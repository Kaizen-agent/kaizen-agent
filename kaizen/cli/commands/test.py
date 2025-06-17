"""Test-related CLI commands."""

import click
import yaml
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback
from abc import ABC, abstractmethod

from ...autofix.test.runner import TestRunner
from ...autofix.test.logger import TestLogger
from ...utils.test_utils import collect_failed_tests
from .formatters import MarkdownTestResultFormatter, RichTestResultFormatter
from .models import (
    TestMetadata,
    EvaluationCriteria,
    TestConfiguration,
    TestResult,
    Result
)
from .config import ConfigurationManager
from .types import TestResultFormatter, STATUS_EMOJI

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

class ValidationError(TestError):
    """Exception for validation errors."""
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

class TestCommand(ABC):
    """Abstract base class for test commands."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    @abstractmethod
    def execute(self) -> Result[TestResult]:
        """Execute the test command."""
        pass

class TestAllCommand(TestCommand):
    """Command to run all tests."""
    
    def __init__(self, config: TestConfiguration, logger: logging.Logger):
        super().__init__(logger)
        self.config = config
    
    def execute(self) -> Result[TestResult]:
        """Execute all tests."""
        try:
            self.logger.info(f"Running test: {self.config.name}")
            if self.config.description:
                self.logger.info(f"Description: {self.config.description}")
            
            # Create and validate runner configuration
            runner_config = self._create_runner_config()
            self.logger.info("Starting test execution...")
            
            # Execute tests
            runner = TestRunner(runner_config)
            results = runner.run_tests(self.config.file_path)
            
            if not results:
                return Result.failure(TestExecutionError("No test results returned from runner"))
            
            self.logger.info("Test execution completed")
            failed_tests = collect_failed_tests(results)
            
            # Handle auto-fix if enabled
            test_attempts = None
            if self.config.auto_fix and failed_tests:
                self.logger.info(f"Found {len(failed_tests)} failed tests")
                test_attempts = self._handle_auto_fix(failed_tests)
            
            result = TestResult(
                name=self.config.name,
                file_path=self.config.file_path,
                config_path=self.config.config_path,
                results=results,
                failed_tests=failed_tests,
                test_attempts=test_attempts
            )
            
            validation_result = result.validate()
            if not validation_result.is_success:
                return Result.failure(validation_result.error)
            
            return Result.success(result)
            
        except Exception as e:
            self.logger.error(f"Error executing tests: {str(e)}")
            return Result.failure(TestExecutionError(f"Failed to execute tests: {str(e)}"))
    
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

class TestReportWriter:
    """Handles writing test reports to files."""
    
    def __init__(self, result: TestResult, formatter: TestResultFormatter, logger: logging.Logger):
        self.result = result
        self.formatter = formatter
        self.logger = logger
    
    def write_report(self, file_path: Path) -> Result[None]:
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
            return Result.success(None)
        except Exception as e:
            self.logger.error(f"Failed to write report: {str(e)}")
            return Result.failure(ReportGenerationError(f"Failed to write report: {str(e)}"))
    
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
        # Load configuration
        config_result = ConfigurationManager.load_configuration(
            Path(config),
            auto_fix=auto_fix,
            create_pr=create_pr,
            max_retries=max_retries,
            base_branch=base_branch
        )
        
        if not config_result.is_success:
            logger.error(f"Configuration error: {str(config_result.error)}")
            raise click.Abort()
        
        # Execute tests
        command = TestAllCommand(config_result.value, logger)
        test_result = command.execute()
        
        if not test_result.is_success:
            logger.error(f"Test execution error: {str(test_result.error)}")
            raise click.Abort()
        
        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = Path("test-results") / f"{test_result.value.name}_{timestamp}_report.txt"
        result_file.parent.mkdir(exist_ok=True)
        
        # Use Markdown formatter for file output
        markdown_formatter = MarkdownTestResultFormatter()
        report_writer = TestReportWriter(test_result.value, markdown_formatter, logger)
        report_result = report_writer.write_report(result_file)
        
        if not report_result.is_success:
            logger.error(f"Report generation error: {str(report_result.error)}")
            raise click.Abort()
        
        # Use Rich formatter for console output
        rich_formatter = RichTestResultFormatter(console)
        
        console.print("\nTest Results Summary")
        console.print("=" * 50)
        
        console.print(f"\nTest Configuration:")
        console.print(f"- Name: {test_result.value.name}")
        console.print(f"- File: {test_result.value.file_path}")
        console.print(f"- Config: {test_result.value.config_path}")
        
        # Format and display overall status
        overall_status = test_result.value.results.get('overall_status', 'unknown')
        status = rich_formatter.format_status(overall_status)
        console.print(f"\nOverall Status: {status}")
        
        # Display test results table
        console.print("\nTest Results Table:")
        console.print(rich_formatter.format_table(test_result.value.results))
        
        console.print(f"\nDetailed report saved to: {result_file}")
        
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
        config_result = ConfigurationManager.load_configuration(Path(test_file))
        if not config_result.is_success:
            logger.error(f"Configuration error: {str(config_result.error)}")
            raise click.Abort()
            
        command = TestAllCommand(config_result.value, logger)
        test_result = command.execute()
        
        if not test_result.is_success:
            logger.error(f"Test execution error: {str(test_result.error)}")
            raise click.Abort()
        
        if not test_result.value.failed_tests:
            logger.info("\nAll steps passed! See test-results/ for details.")
        else:
            logger.info("\nSome steps failed. See test-results/ for details.")
        
    except Exception as e:
        logger.error(f"Error running test: {str(e)}")
        raise click.Abort() 