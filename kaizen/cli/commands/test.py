"""Test-related CLI commands."""

import click
import yaml
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Protocol, runtime_checkable
from dataclasses import dataclass
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.traceback import install as install_rich_traceback

from ...autofix.test.runner import TestRunner
from ...autofix.test.logger import TestLogger
from ...utils.test_utils import collect_failed_tests

# Configure rich traceback
install_rich_traceback(show_locals=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("kaizen.test")

# Constants
DEFAULT_MAX_RETRIES = 1
DEFAULT_BASE_BRANCH = 'main'
STATUS_EMOJI = {
    'passed': '✅',
    'failed': '❌',
    'completed': '✓',
    'unknown': '?'
}

class TestError(Exception):
    """Base exception for test-related errors."""
    pass

class ConfigurationError(TestError):
    """Exception for configuration-related errors."""
    pass

class TestExecutionError(TestError):
    """Exception for test execution errors."""
    pass

class ReportGenerationError(TestError):
    """Exception for report generation errors."""
    pass

@runtime_checkable
class StatusFormatter(Protocol):
    """Protocol for formatting test status."""
    def format_status(self, status: str) -> str: ...

@runtime_checkable
class TableFormatter(Protocol):
    """Protocol for formatting test results as tables."""
    def format_table(self, results: Dict[str, Any]) -> Union[List[str], Table]: ...

@runtime_checkable
class TestResultFormatter(StatusFormatter, TableFormatter, Protocol):
    """Protocol for test result formatting."""
    pass

@dataclass
class TestMetadata:
    """Metadata for test configuration."""
    version: str
    dependencies: List[str]
    environment_variables: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestMetadata':
        """Create TestMetadata from dictionary."""
        return cls(
            version=data['version'],
            dependencies=data['dependencies'],
            environment_variables=data['environment_variables']
        )

@dataclass
class EvaluationCriteria:
    """Evaluation criteria for tests."""
    llm_provider: str
    model: str
    criteria: List[Dict[str, Any]]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationCriteria':
        """Create EvaluationCriteria from dictionary."""
        return cls(
            llm_provider=data['llm_provider'],
            model=data['model'],
            criteria=data['criteria']
        )

@dataclass
class TestConfiguration:
    """Configuration for test execution."""
    name: str
    file_path: Path
    config_path: Path
    agent_type: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[EvaluationCriteria] = None
    regions: Optional[List[Dict[str, Any]]] = None
    steps: Optional[List[Dict[str, Any]]] = None
    auto_fix: bool = False
    create_pr: bool = False
    max_retries: int = DEFAULT_MAX_RETRIES
    base_branch: str = DEFAULT_BASE_BRANCH

    @classmethod
    def from_file(cls, config_path: Path, auto_fix: bool = False, 
                 create_pr: bool = False, max_retries: int = DEFAULT_MAX_RETRIES,
                 base_branch: str = DEFAULT_BASE_BRANCH) -> 'TestConfiguration':
        """Create configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                raise ConfigurationError("Test configuration file is empty")
            
            cls._validate_required_fields(config_data)
            cls._validate_test_structure(config_data)
            
            file_path = cls._resolve_file_path(config_path, config_data['file_path'])
            metadata = cls._parse_metadata(config_data)
            evaluation = cls._parse_evaluation(config_data)
            
            return cls(
                name=config_data['name'],
                file_path=file_path,
                config_path=config_path,
                agent_type=config_data.get('agent_type'),
                description=config_data.get('description'),
                metadata=metadata,
                evaluation=evaluation,
                regions=config_data.get('regions'),
                steps=config_data.get('steps'),
                auto_fix=auto_fix,
                create_pr=create_pr,
                max_retries=max_retries,
                base_branch=base_branch
            )
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML configuration: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {str(e)}")

    @staticmethod
    def _validate_required_fields(config_data: Dict[str, Any]) -> None:
        """Validate required fields in configuration."""
        required_fields = ['name', 'file_path']
        missing_fields = [field for field in required_fields if field not in config_data]
        if missing_fields:
            raise ConfigurationError(f"Missing required fields in configuration: {', '.join(missing_fields)}")

    @staticmethod
    def _validate_test_structure(config_data: Dict[str, Any]) -> None:
        """Validate test structure in configuration."""
        if 'regions' not in config_data and 'steps' not in config_data:
            raise ConfigurationError("Test configuration must contain either 'regions' or 'steps'")

    @staticmethod
    def _resolve_file_path(config_path: Path, file_path: str) -> Path:
        """Resolve file path relative to config file."""
        resolved_path = (config_path.parent / file_path).resolve()
        if not resolved_path.exists():
            raise ConfigurationError(f"File not found: {resolved_path}")
        return resolved_path

    @staticmethod
    def _parse_metadata(config_data: Dict[str, Any]) -> Optional[TestMetadata]:
        """Parse metadata from configuration."""
        if 'metadata' not in config_data:
            return None
        return TestMetadata.from_dict(config_data['metadata'])

    @staticmethod
    def _parse_evaluation(config_data: Dict[str, Any]) -> Optional[EvaluationCriteria]:
        """Parse evaluation criteria from configuration."""
        if 'evaluation' not in config_data:
            return None
        return EvaluationCriteria.from_dict(config_data['evaluation'])

@dataclass
class TestResult:
    """Data class to hold test results."""
    name: str
    file_path: Path
    config_path: Path
    results: Dict[str, Any]
    failed_tests: List[Dict[str, Any]]
    test_attempts: Optional[List[Dict[str, Any]]] = None

class MarkdownTestResultFormatter:
    """Formats test results in Markdown format."""
    
    @staticmethod
    def format_status(status: str) -> str:
        """Format status with emoji."""
        return f"{STATUS_EMOJI.get(status.lower(), STATUS_EMOJI['unknown'])} {status.upper()}"
    
    def format_table(self, results: Dict[str, Any]) -> List[str]:
        """Format test results as a table."""
        table_lines = [
            "| Test Name | Region | Status | Details |",
            "|-----------|--------|--------|---------|"
        ]
        
        for region, result in results.items():
            if region == 'overall_status':
                continue
                
            test_cases = result.get('test_cases', []) if isinstance(result, dict) else []
            for test_case in test_cases:
                if not isinstance(test_case, dict):
                    continue
                    
                status = "✅ PASS" if test_case.get('status') == 'passed' else "❌ FAIL"
                details = str(test_case.get('details', ''))
                if len(details) > 50:
                    details = details[:47] + "..."
                table_lines.append(
                    f"| {test_case.get('name', 'Unknown')} | {region} | {status} | {details} |"
                )
        
        return table_lines

class RichTestResultFormatter:
    """Formats test results using Rich library."""
    
    def __init__(self, console: Console):
        self.console = console
    
    def format_status(self, status: str) -> str:
        """Format status with emoji."""
        return f"{STATUS_EMOJI.get(status.lower(), STATUS_EMOJI['unknown'])} {status.upper()}"
    
    def format_table(self, results: Dict[str, Any]) -> Table:
        """Format test results as a Rich table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test Name")
        table.add_column("Region")
        table.add_column("Status")
        table.add_column("Details")
        
        for region, result in results.items():
            if region == 'overall_status':
                continue
                
            test_cases = result.get('test_cases', []) if isinstance(result, dict) else []
            for test_case in test_cases:
                if not isinstance(test_case, dict):
                    continue
                    
                status = "✅ PASS" if test_case.get('status') == 'passed' else "❌ FAIL"
                details = str(test_case.get('details', ''))
                if len(details) > 50:
                    details = details[:47] + "..."
                table.add_row(
                    test_case.get('name', 'Unknown'),
                    region,
                    status,
                    details
                )
        
        return table

class TestReportWriter:
    """Handles writing test reports to files."""
    
    def __init__(self, result: TestResult, formatter: TestResultFormatter, logger: logging.Logger):
        self.result = result
        self.formatter = formatter
        self.logger = logger
    
    def write_report(self, file_path: Path) -> None:
        """Write test report to file."""
        try:
            self.logger.info(f"Writing test report to {file_path}")
            with open(file_path, 'w') as f:
                self._write_report_header(f)
                self._write_configuration_details(f)
                self._write_overall_status(f)
                self._write_detailed_results(f)
                self._write_failed_tests(f)
                if self.result.test_attempts:
                    self._write_autofix_attempts(f)
            self.logger.info("Test report written successfully")
        except Exception as e:
            self.logger.error(f"Failed to write report: {str(e)}")
            raise ReportGenerationError(f"Failed to write report: {str(e)}")
    
    def _write_report_header(self, f) -> None:
        f.write("Test Results Report\n")
        f.write("=" * 50 + "\n\n")
    
    def _write_configuration_details(self, f) -> None:
        f.write("Test Configuration:\n")
        f.write(f"- Name: {self.result.name}\n")
        f.write(f"- File: {self.result.file_path}\n")
        f.write(f"- Config: {self.result.config_path}\n\n")
    
    def _write_overall_status(self, f) -> None:
        try:
            overall_status = self.result.results.get('overall_status', 'unknown')
            status = overall_status.get('status', 'unknown') if isinstance(overall_status, dict) else overall_status
            formatted_status = self.formatter.format_status(status)
            f.write(f"Overall Status: {formatted_status}\n\n")
        except Exception as e:
            self.logger.warning(f"Error formatting overall status: {str(e)}")
            f.write("Overall Status: ❓ UNKNOWN\n\n")
    
    def _write_detailed_results(self, f) -> None:
        f.write("Detailed Test Results:\n")
        f.write("=" * 50 + "\n\n")
        
        for region, result in self.result.results.items():
            if region == 'overall_status':
                continue
                
            f.write(f"Region: {region}\n")
            f.write("-" * 30 + "\n")
            
            test_cases = result.get('test_cases', []) if isinstance(result, dict) else []
            for test_case in test_cases:
                self._write_test_case(f, test_case)
    
    def _write_test_case(self, f, test_case: Dict[str, Any]) -> None:
        if not isinstance(test_case, dict):
            self.logger.warning(f"Invalid test case format: {test_case}")
            f.write(f"Invalid test case format: {test_case}\n")
            return

        f.write(f"\nTest: {test_case.get('name', 'Unknown')}\n")
        f.write(f"Status: {test_case.get('status', 'unknown')}\n")
        if test_case.get('details'):
            f.write(f"Details: {test_case.get('details')}\n")
        if test_case.get('output'):
            f.write(f"Output:\n{test_case.get('output')}\n")
        if test_case.get('evaluation'):
            f.write(f"Evaluation:\n{json.dumps(test_case.get('evaluation'), indent=2)}\n")
        f.write("-" * 30 + "\n")
    
    def _write_failed_tests(self, f) -> None:
        if not self.result.failed_tests:
            return
            
        f.write("\nFailed Tests Analysis:\n")
        f.write("=" * 50 + "\n\n")
        for test in self.result.failed_tests:
            if not isinstance(test, dict):
                self.logger.warning(f"Invalid failed test format: {test}")
                f.write(f"Invalid failed test format: {test}\n")
                continue

            f.write(f"Test: {test.get('test_name', 'Unknown')} ({test.get('region', 'Unknown')})\n")
            f.write(f"Error: {test.get('error_message', 'Unknown error')}\n")
            if test.get('output'):
                f.write(f"Output:\n{test.get('output')}\n")
            f.write("-" * 30 + "\n")
    
    def _write_autofix_attempts(self, f) -> None:
        f.write("\nAuto-fix Attempts:\n")
        f.write("=" * 50 + "\n\n")
        for attempt in self.result.test_attempts:
            if not isinstance(attempt, dict):
                self.logger.warning(f"Invalid attempt format: {attempt}")
                f.write(f"Invalid attempt format: {attempt}\n")
                continue
            self._write_attempt_details(f, attempt)
    
    def _write_attempt_details(self, f, attempt: Dict[str, Any]) -> None:
        f.write(f"Attempt {attempt.get('attempt', 'Unknown')}:\n")
        f.write("-" * 30 + "\n")
        
        fixed_tests = self._get_fixed_tests(attempt)
        if fixed_tests:
            f.write("Fixed Tests:\n")
            for fixed in fixed_tests:
                f.write(f"- {fixed.get('test_name', 'Unknown')} ({fixed.get('region', 'Unknown')})\n")
        else:
            f.write("No tests were fixed in this attempt\n")
        
        try:
            results = attempt.get('results', {})
            overall_status = results.get('overall_status', 'unknown')
            status = overall_status.get('status', 'unknown') if isinstance(overall_status, dict) else overall_status
            formatted_status = self.formatter.format_status(status)
            f.write(f"\nOverall Status: {formatted_status}\n")
        except Exception as e:
            self.logger.warning(f"Error formatting attempt status: {str(e)}")
            f.write("\nOverall Status: UNKNOWN\n")
        
        if isinstance(overall_status, dict) and 'error' in overall_status:
            f.write(f"Error: {overall_status['error']}\n")
        
        f.write("\n")
    
    def _get_fixed_tests(self, attempt: Dict[str, Any]) -> List[Dict[str, Any]]:
        fixed_tests = []
        results = attempt.get('results', {})
        
        for region, result in results.items():
            if region == 'overall_status':
                continue
            if not isinstance(result, dict):
                continue
                
            test_cases = result.get('test_cases', [])
            for test_case in test_cases:
                if isinstance(test_case, dict) and test_case.get('status') == 'passed':
                    fixed_tests.append({
                        'region': region,
                        'test_name': test_case.get('name', 'Unknown')
                    })
        return fixed_tests

class TestExecutor:
    """Handles test execution and result processing."""
    
    def __init__(self, config: TestConfiguration, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def execute(self) -> TestResult:
        """Execute tests and return results."""
        try:
            self.logger.info(f"Running test: {self.config.name}")
            if self.config.description:
                self.logger.info(f"Description: {self.config.description}")
            
            runner = TestRunner(self._create_runner_config())
            results = runner.run_tests(self.config.file_path)
            failed_tests = collect_failed_tests(results)
            
            test_attempts = self._handle_auto_fix(failed_tests) if self.config.auto_fix else None
            
            return TestResult(
                name=self.config.name,
                file_path=self.config.file_path,
                config_path=self.config.config_path,
                results=results,
                failed_tests=failed_tests,
                test_attempts=test_attempts
            )
            
        except Exception as e:
            self.logger.error(f"Error executing tests: {str(e)}")
            raise TestExecutionError(f"Failed to execute tests: {str(e)}")
    
    def _create_runner_config(self) -> Dict[str, Any]:
        """Create configuration for test runner."""
        config = {
            'name': self.config.name,
            'file_path': str(self.config.file_path),
            'config_file': str(self.config.config_path),
            'agent_type': self.config.agent_type,
            'description': self.config.description,
            'metadata': self.config.metadata.__dict__ if self.config.metadata else None,
            'evaluation': self.config.evaluation.__dict__ if self.config.evaluation else None
        }
        
        if self.config.regions:
            config['regions'] = self.config.regions
        if self.config.steps:
            config['steps'] = self.config.steps
            
        return config
    
    def _handle_auto_fix(self, failed_tests: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Handle auto-fix for failed tests."""
        if not failed_tests:
            return None
            
        self.logger.info(f"Attempting to fix {len(failed_tests)} failing tests (max retries: {self.config.max_retries})")
        from ...autofix.main import AutoFix
        return AutoFix(self.config.config_path).fix_code(
            str(self.config.file_path),
            failed_tests,
            max_retries=self.config.max_retries,
            create_pr=self.config.create_pr,
            base_branch=self.config.base_branch
        )

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=DEFAULT_MAX_RETRIES, help=f'Maximum number of retry attempts for auto-fix (default: {DEFAULT_MAX_RETRIES})')
@click.option('--base-branch', default=DEFAULT_BASE_BRANCH, help=f'Base branch for pull request (default: {DEFAULT_BASE_BRANCH})')
def test_all(config: str, auto_fix: bool, create_pr: bool, max_retries: int, base_branch: str):
    """Run all tests specified in the configuration file."""
    console = Console()
    
    try:
        test_config = TestConfiguration.from_file(
            Path(config),
            auto_fix=auto_fix,
            create_pr=create_pr,
            max_retries=max_retries,
            base_branch=base_branch
        )
        
        executor = TestExecutor(test_config, logger)
        test_result = executor.execute()
        
        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = Path("test-results") / f"{test_result.name}_{timestamp}_report.txt"
        result_file.parent.mkdir(exist_ok=True)
        
        # Use Markdown formatter for file output
        markdown_formatter = MarkdownTestResultFormatter()
        report_writer = TestReportWriter(test_result, markdown_formatter, logger)
        report_writer.write_report(result_file)
        
        # Use Rich formatter for console output
        rich_formatter = RichTestResultFormatter(console)
        
        console.print("\nTest Results Summary")
        console.print("=" * 50)
        
        console.print(f"\nTest Configuration:")
        console.print(f"- Name: {test_result.name}")
        console.print(f"- File: {test_result.file_path}")
        console.print(f"- Config: {test_result.config_path}")
        
        status = rich_formatter.format_status(test_result.results.get('overall_status', 'unknown'))
        console.print(f"\nOverall Status: {status}")
        
        console.print("\nTest Results Table:")
        console.print(rich_formatter.format_table(test_result.results))
        
        console.print(f"\nDetailed report saved to: {result_file}")
        
    except ConfigurationError as e:
        logger.error(f"Configuration error: {str(e)}")
        raise click.Abort()
    except TestExecutionError as e:
        logger.error(f"Test execution error: {str(e)}")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise click.Abort()

@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.argument('input_text', required=False)
@click.option('--output', '-o', type=click.Path(), help='Path to save output to')
def run_block(file_path: str, input_text: str = None, output: str = None):
    """Execute a code block between kaizen markers in a Python file."""
    try:
        from ...core.runner import run_test_block
        result = run_test_block(file_path, input_text)
        
        if output:
            with open(output, 'w') as f:
                f.write(result)
            logger.info(f"Output saved to: {output}")
        else:
            logger.info("\nExecution Result:")
            logger.info("=" * 50)
            logger.info(result)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise click.Abort()

@click.command()
@click.argument('test_file', type=click.Path(exists=True))
def run_test(test_file: str):
    """Run a test file and display results."""
    try:
        test_config = TestConfiguration.from_file(Path(test_file))
        executor = TestExecutor(test_config, logger)
        test_result = executor.execute()
        
        if not test_result.failed_tests:
            logger.info("\nAll steps passed! See test-results/ for details.")
        else:
            logger.info("\nSome steps failed. See test-results/ for details.")
        
    except Exception as e:
        logger.error(f"Error running test: {str(e)}")
        raise click.Abort() 