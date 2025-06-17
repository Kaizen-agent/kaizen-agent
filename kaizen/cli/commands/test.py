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
from abc import ABC, abstractmethod

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback
from rich.table import Table

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
from .types import (
    TestError,
    ConfigurationError,
    TestExecutionError,
    ReportGenerationError,
    ValidationError,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_BRANCH,
    TestResultFormatter,
    STATUS_EMOJI
)
from .report_writer import TestReportWriter

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
        """
        Handle auto-fix for failed tests.
        
        Args:
            failed_tests: List of failed tests to fix
            
        Returns:
            Optional[List[Dict[str, Any]]]: List of fix attempts if any were made
        """
        if not failed_tests:
            return None
            
        self.logger.info(f"Attempting to fix {len(failed_tests)} failing tests (max retries: {self.config.max_retries})")
        from ...autofix.main import AutoFix, FixStatus
        
        try:
            # Create AutoFix instance and run fixes
            fixer = AutoFix(self.config.config_path)
            fix_results = fixer.fix_code(
                str(self.config.file_path),
                failed_tests,
                max_retries=self.config.max_retries,
                create_pr=self.config.create_pr,
                base_branch=self.config.base_branch
            )
            
            # Process and return attempts
            attempts = fix_results.get('attempts', [])
            if not attempts:
                self.logger.warning("No fix attempts were made")
                return None
                
            # Log results of each attempt
            for attempt in attempts:
                status = attempt.get('status', 'unknown')
                attempt_num = attempt.get('attempt_number', 'unknown')
                self.logger.info(f"Attempt {attempt_num}: {status}")
                
                if status == FixStatus.SUCCESS.name:
                    self.logger.info("Successfully fixed all failing tests!")
                    if self.config.create_pr:
                        pr_data = fix_results.get('pr')
                        if pr_data:
                            self.logger.info(f"Created pull request: {pr_data.get('url', 'Unknown URL')}")
                elif status == FixStatus.FAILED.name:
                    self.logger.warning("Failed to fix all tests after all attempts")
                elif status == FixStatus.ERROR.name:
                    error = attempt.get('error', 'Unknown error')
                    self.logger.error(f"Error during fix attempt: {error}")
            
            return attempts
            
        except Exception as e:
            self.logger.error(f"Error during auto-fix process: {str(e)}")
            return None

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=DEFAULT_MAX_RETRIES, help=f'Maximum number of retry attempts for auto-fix (default: {DEFAULT_MAX_RETRIES})')
@click.option('--base-branch', default=DEFAULT_BASE_BRANCH, help=f'Base branch for pull request (default: {DEFAULT_BASE_BRANCH})')
@click.option('--pr-strategy', type=click.Choice(['ALL_PASSING', 'ANY_IMPROVEMENT', 'NONE']), 
              default='ALL_PASSING', help='Strategy for when to create PRs (default: ALL_PASSING)')
def test_all(config: str, auto_fix: bool, create_pr: bool, max_retries: int, base_branch: str, pr_strategy: str):
    """Run all tests specified in the configuration file."""
    console = Console()
    
    try:
        # Load configuration
        config_result = ConfigurationManager.load_configuration(
            Path(config),
            auto_fix=auto_fix,
            create_pr=create_pr,
            max_retries=max_retries,
            base_branch=base_branch,
            pr_strategy=pr_strategy
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
