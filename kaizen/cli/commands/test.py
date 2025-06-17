"""Test-related CLI commands."""

import click
import logging
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback

from .config import ConfigurationManager
from .test_commands import TestAllCommand
from .formatters import MarkdownTestResultFormatter, RichTestResultFormatter
from .report_writer import TestReportWriter
from .types import (
    TestError,
    ConfigurationError,
    TestExecutionError,
    ReportGenerationError,
    ValidationError,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_BRANCH,
    PRStrategy
)

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

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=DEFAULT_MAX_RETRIES, help=f'Maximum number of retry attempts for auto-fix (default: {DEFAULT_MAX_RETRIES})')
@click.option('--base-branch', default=DEFAULT_BASE_BRANCH, help=f'Base branch for pull request (default: {DEFAULT_BASE_BRANCH})')
@click.option('--pr-strategy', type=click.Choice([s.value for s in PRStrategy]), 
              default=PRStrategy.ALL_PASSING.value, help='Strategy for when to create PRs (default: ALL_PASSING)')
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
