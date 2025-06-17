"""Test-related CLI commands."""

import click
import yaml
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from rich.console import Console

from ...autofix.test.runner import TestRunner
from ...autofix.test.logger import TestLogger
from ...utils.test_utils import collect_failed_tests

# Constants
DEFAULT_MAX_RETRIES = 1
DEFAULT_BASE_BRANCH = 'main'
STATUS_EMOJI = {
    'passed': '✅',
    'failed': '❌',
    'completed': '✓',
    'unknown': '?'
}

@dataclass
class TestResult:
    """Data class to hold test results."""
    name: str
    file_path: Path
    config_path: Path
    results: Dict[str, Any]
    failed_tests: List[Dict[str, Any]]
    test_attempts: Optional[List[Dict[str, Any]]] = None

class TestConfigValidator:
    """Validates test configuration."""
    
    @staticmethod
    def validate(config: Dict[str, Any], config_path: Path) -> None:
        """Validate test configuration."""
        if not config:
            raise ValueError("Test configuration file is empty")
            
        required_fields = ['name', 'file_path']
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields in configuration: {', '.join(missing_fields)}")
            
        # Resolve and validate file path
        file_path = (config_path.parent / config['file_path']).resolve()
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

class TestResultFormatter:
    """Formats test results for display and file output."""
    
    @staticmethod
    def get_status_emoji(status: str) -> str:
        """Get emoji for status."""
        return STATUS_EMOJI.get(status.lower(), STATUS_EMOJI['unknown'])
    
    @staticmethod
    def format_overall_status(results: Dict[str, Any]) -> tuple[str, str]:
        """Format overall status with emoji."""
        overall_status = results.get('overall_status', 'unknown')
        status = overall_status.get('status', 'unknown') if isinstance(overall_status, dict) else overall_status
        status_emoji = TestResultFormatter.get_status_emoji(status)
        return status, status_emoji
    
    @staticmethod
    def format_test_results_table(results: Dict[str, Any]) -> List[str]:
        """Format test results as a table."""
        table_lines = [
            "| Test Name | Region | Status | Details |",
            "|-----------|--------|--------|---------|"
        ]
        
        for region, result in results.items():
            if region == 'overall_status':
                continue
                
            test_cases = result.get('test_cases', [])
            for test_case in test_cases:
                status = "✅ PASS" if test_case.get('status') == 'passed' else "❌ FAIL"
                details = str(test_case.get('details', ''))
                if len(details) > 50:
                    details = details[:47] + "..."
                table_lines.append(
                    f"| {test_case.get('name', 'Unknown')} | {region} | {status} | {details} |"
                )
        
        return table_lines

class TestReportGenerator:
    """Generates test reports."""
    
    def __init__(self, result: TestResult):
        self.result = result
        self.console = Console()
    
    def generate_report(self) -> Path:
        """Generate and save test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = Path("test-results") / f"{self.result.name}_{timestamp}_report.txt"
        result_file.parent.mkdir(exist_ok=True)
        
        with open(result_file, 'w') as f:
            self._write_report_header(f)
            self._write_configuration_details(f)
            self._write_overall_status(f)
            self._write_detailed_results(f)
            self._write_failed_tests(f)
            if self.result.test_attempts:
                self._write_autofix_attempts(f)
        
        return result_file
    
    def _write_report_header(self, f) -> None:
        f.write("Test Results Report\n")
        f.write("=" * 50 + "\n\n")
    
    def _write_configuration_details(self, f) -> None:
        f.write("Test Configuration:\n")
        f.write(f"- Name: {self.result.name}\n")
        f.write(f"- File: {self.result.file_path}\n")
        f.write(f"- Config: {self.result.config_path}\n\n")
    
    def _write_overall_status(self, f) -> None:
        status, status_emoji = TestResultFormatter.format_overall_status(self.result.results)
        f.write(f"Overall Status: {status_emoji} {status.upper()}\n\n")
    
    def _write_detailed_results(self, f) -> None:
        f.write("Detailed Test Results:\n")
        f.write("=" * 50 + "\n\n")
        
        for region, result in self.result.results.items():
            if region == 'overall_status':
                continue
                
            f.write(f"Region: {region}\n")
            f.write("-" * 30 + "\n")
            
            test_cases = result.get('test_cases', [])
            for test_case in test_cases:
                self._write_test_case(f, test_case)
    
    def _write_test_case(self, f, test_case: Dict[str, Any]) -> None:
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
            f.write(f"Test: {test['test_name']} ({test['region']})\n")
            f.write(f"Error: {test['error_message']}\n")
            if test['output']:
                f.write(f"Output:\n{test['output']}\n")
            f.write("-" * 30 + "\n")
    
    def _write_autofix_attempts(self, f) -> None:
        f.write("\nAuto-fix Attempts:\n")
        f.write("=" * 50 + "\n\n")
        for attempt in self.result.test_attempts:
            self._write_attempt_details(f, attempt)
    
    def _write_attempt_details(self, f, attempt: Dict[str, Any]) -> None:
        f.write(f"Attempt {attempt['attempt']}:\n")
        f.write("-" * 30 + "\n")
        
        fixed_tests = self._get_fixed_tests(attempt)
        if fixed_tests:
            f.write("Fixed Tests:\n")
            for fixed in fixed_tests:
                f.write(f"- {fixed['test_name']} ({fixed['region']})\n")
        else:
            f.write("No tests were fixed in this attempt\n")
        
        status, _ = TestResultFormatter.format_overall_status(attempt['results'])
        f.write(f"\nOverall Status: {status.upper()}\n")
        
        overall_status = attempt['results'].get('overall_status', {})
        if isinstance(overall_status, dict) and 'error' in overall_status:
            f.write(f"Error: {overall_status['error']}\n")
        
        f.write("\n")
    
    def _get_fixed_tests(self, attempt: Dict[str, Any]) -> List[Dict[str, Any]]:
        fixed_tests = []
        for region, result in attempt['results'].items():
            if region == 'overall_status':
                continue
            test_cases = result.get('test_cases', [])
            for test_case in test_cases:
                if test_case.get('status') == 'passed':
                    fixed_tests.append({
                        'region': region,
                        'test_name': test_case.get('name')
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
        # Load and validate configuration
        config_path = Path(config)
        console.print(f"[blue]Loading test configuration from: {config_path}[/blue]")
        
        with open(config_path, 'r') as f:
            test_config = yaml.safe_load(f)
        
        TestConfigValidator.validate(test_config, config_path)
        
        # Debug print the loaded configuration
        console.print("[blue]Loaded test configuration:[/blue]")
        console.print(json.dumps(test_config, indent=2))
        
        # Add config file path to test configuration
        test_config['config_file'] = str(config_path)
        
        # Create test runner and run tests
        runner = TestRunner(test_config)
        logger = TestLogger(test_config.get('name', 'Unnamed Test'))
        
        console.print(f"Running test: {test_config.get('name', 'Unnamed Test')}")
        console.print("=" * 50)
        
        # Resolve and validate file path
        file_path = (config_path.parent / test_config['file_path']).resolve()
        console.print(f"[blue]Debug: Resolved file path: {file_path}[/blue]")
        
        if not file_path.exists():
            console.print(f"[red]Error: File not found: {file_path}[/red]")
            sys.exit(1)
        
        # Run tests and collect results
        results = runner.run_tests(file_path)
        failed_tests = collect_failed_tests(results)
        
        # Handle failed tests if auto-fix is enabled
        test_attempts = None
        if failed_tests and auto_fix:
            console.print(f"\nAttempting to fix failing tests (max retries: {max_retries})...")
            from ...autofix.main import AutoFix
            test_attempts = AutoFix(config_path).fix_code(
                str(file_path),
                failed_tests,
                max_retries=max_retries,
                create_pr=create_pr,
                base_branch=base_branch
            )
            if create_pr:
                console.print("Pull request created with fixes")
        
        # Create test result object
        test_result = TestResult(
            name=test_config.get('name', 'Unnamed Test'),
            file_path=file_path,
            config_path=config_path,
            results=results,
            failed_tests=failed_tests,
            test_attempts=test_attempts
        )
        
        # Generate and display report
        report_generator = TestReportGenerator(test_result)
        result_file = report_generator.generate_report()
        
        # Display results summary
        console.print("\nTest Results Summary")
        console.print("=" * 50)
        
        # Print configuration details
        console.print(f"\nTest Configuration:")
        console.print(f"- Name: {test_result.name}")
        console.print(f"- File: {test_result.file_path}")
        console.print(f"- Config: {test_result.config_path}")
        
        # Print overall status
        status, status_emoji = TestResultFormatter.format_overall_status(results)
        console.print(f"\nOverall Status: {status_emoji} {status.upper()}")
        
        # Print test results table
        console.print("\nTest Results Table:")
        for line in TestResultFormatter.format_test_results_table(results):
            console.print(line)
        
        console.print(f"\nDetailed report saved to: {result_file}")
        
    except Exception as e:
        console.print(f"[red]Error running tests: {str(e)}[/red]")
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
            click.echo(f"Output saved to: {output}")
        else:
            click.echo("\nExecution Result:")
            click.echo("=" * 50)
            click.echo(result)
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@click.command()
@click.argument('test_file', type=click.Path(exists=True))
def run_test(test_file: str):
    """Run a test file and display results."""
    try:
        with open(test_file, 'r') as f:
            test_config = yaml.safe_load(f)
        
        # Create test runner
        runner = TestRunner()
        logger = TestLogger(test_config.get('name', 'Unnamed Test'))
        
        click.echo(f"Running test: {test_config.get('name', 'Unnamed Test')}")
        click.echo("=" * 50)
        
        # Run tests (use run_test, not run_tests)
        passed = runner.run_test(test_file)
        
        if passed:
            click.echo("\nAll steps passed! See test-results/ for details.")
        else:
            click.echo("\nSome steps failed. See test-results/ for details.")
        
    except Exception as e:
        click.echo(f"Error running test: {str(e)}")
        raise click.Abort() 