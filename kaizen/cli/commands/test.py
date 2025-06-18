"""Test-related CLI commands.

This module provides CLI commands for running tests and managing test execution.
It includes functionality for:
- Running tests with configuration
- Auto-fixing failing tests
- Creating pull requests with fixes
- Generating test reports

Example:
    >>> from kaizen.cli.commands.test import test_all
    >>> test_all(
    ...     config="test_config.yaml",
    ...     auto_fix=True,
    ...     create_pr=True,
    ...     max_retries=2
    ... )
"""

# Standard library imports
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, NoReturn, List

# Third-party imports
import click
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

# Local application imports
from .config import ConfigurationManager
from .test_commands import TestAllCommand
from .formatters import MarkdownTestResultFormatter, RichTestResultFormatter
from .report_writer import TestReportWriter
from .errors import (
    TestError,
    ConfigurationError,
    TestExecutionError,
    ReportGenerationError,
    ValidationError,
    AutoFixError
)
from .types import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_BRANCH,
    PRStrategy,
    TestStatus
)
from .models import TestResult

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

def _handle_error(error: Exception, message: str) -> NoReturn:
    """Handle errors in a consistent way.
    
    Args:
        error: The exception that occurred
        message: Error message to display
        
    Raises:
        click.Abort: Always raises to abort the command
    """
    logger.error(f"{message}: {str(error)}")
    raise click.Abort()

def _generate_report_path(test_result: TestResult) -> Path:
    """Generate a path for the test report.
    
    Args:
        test_result: The test result to generate a report for
        
    Returns:
        Path object for the report file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = Path("test-results") / f"{test_result.name}_{timestamp}_report.txt"
    result_file.parent.mkdir(exist_ok=True)
    return result_file

def _display_test_summary(console: Console, test_result: TestResult, rich_formatter: RichTestResultFormatter) -> None:
    """Display a summary of the test results.
    
    Args:
        console: Rich console for output
        test_result: The test result to display
        rich_formatter: Formatter for rich output
    """
    console.print("\nTest Results Summary")
    console.print("=" * 50)
    
    console.print(f"\nTest Configuration:")
    console.print(f"- Name: {test_result.name}")
    console.print(f"- File: {test_result.file_path}")
    console.print(f"- Config: {test_result.config_path}")
    
    # Format and display overall status
    overall_status = test_result.results.get('overall_status', 'unknown')
    status = rich_formatter.format_status(overall_status)
    console.print(f"\nOverall Status: {status}")
    
    # Display test results table
    console.print("\nTest Results Table:")
    console.print(rich_formatter.format_table(test_result.results))

def _install_dependencies(dependencies: List[str], logger: logging.Logger) -> Result[None]:
    """Install required dependencies.
    
    Args:
        dependencies: List of dependencies to install
        logger: Logger instance
        
    Returns:
        Result indicating success or failure
    """
    if not dependencies:
        return Result.success(None)
        
    try:
        import subprocess
        import sys
        
        logger.info("Installing dependencies...")
        for dep in dependencies:
            logger.info(f"Installing {dep}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", dep],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return Result.failure(
                    TestError(
                        f"Failed to install dependency {dep}: {result.stderr}",
                        {"dependency": dep, "error": result.stderr}
                    )
                )
                
        logger.info("All dependencies installed successfully")
        return Result.success(None)
        
    except Exception as e:
        return Result.failure(
            TestError(
                f"Error installing dependencies: {str(e)}",
                {"error": str(e)}
            )
        )

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=DEFAULT_MAX_RETRIES, help=f'Maximum number of retry attempts for auto-fix (default: {DEFAULT_MAX_RETRIES})')
@click.option('--base-branch', default=DEFAULT_BASE_BRANCH, help=f'Base branch for pull request (default: {DEFAULT_BASE_BRANCH})')
@click.option('--pr-strategy', type=click.Choice([s.value for s in PRStrategy]), 
              default=PRStrategy.ANY_IMPROVEMENT.value, help='Strategy for when to create PRs (default: ANY_IMPROVEMENT)')
def test_all(
    config: str,
    auto_fix: bool,
    create_pr: bool,
    max_retries: int,
    base_branch: str,
    pr_strategy: str
) -> None:
    """Run all tests specified in the configuration file.
    
    Args:
        config: Path to the test configuration file
        auto_fix: Whether to automatically fix failing tests
        create_pr: Whether to create a pull request with fixes
        max_retries: Maximum number of retry attempts for auto-fix
        base_branch: Base branch for pull request
        pr_strategy: Strategy for when to create PRs
        
    Example:
        >>> test_all(
        ...     config="test_config.yaml",
        ...     auto_fix=True,
        ...     create_pr=True,
        ...     max_retries=2,
        ...     base_branch="main",
        ...     pr_strategy="ANY_IMPROVEMENT"
        ... )
    """
    console = Console()
    
    try:
        # Load configuration
        config_manager = ConfigurationManager()
        config_result = config_manager.load_configuration(
            Path(config),
            auto_fix=auto_fix,
            create_pr=create_pr,
            max_retries=max_retries,
            base_branch=base_branch,
            pr_strategy=pr_strategy
        )
        
        if not config_result.is_success:
            _handle_error(config_result.error, "Configuration error")
        
        config = config_result.value
        
        # Execute tests
        command = TestAllCommand(config, logger)
        test_result = command.execute()
        
        if not test_result.is_success:
            _handle_error(test_result.error, "Test execution error")
        
        # Generate report
        result_file = _generate_report_path(test_result.value)
        
        # Use Markdown formatter for file output
        markdown_formatter = MarkdownTestResultFormatter()
        report_writer = TestReportWriter(test_result.value, markdown_formatter, logger)
        report_result = report_writer.write_report(result_file)
        
        if not report_result.is_success:
            _handle_error(report_result.error, "Report generation error")
        
        # Use Rich formatter for console output
        rich_formatter = RichTestResultFormatter(console)
        
        # Display test summary
        _display_test_summary(console, test_result.value, rich_formatter)
        
        console.print(f"\nDetailed report saved to: {result_file}")
        
    except Exception as e:
        _handle_error(e, "Unexpected error")
