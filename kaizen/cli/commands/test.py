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



@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=DEFAULT_MAX_RETRIES, help=f'Maximum number of retry attempts for auto-fix (default: {DEFAULT_MAX_RETRIES})')
@click.option('--base-branch', default=DEFAULT_BASE_BRANCH, help=f'Base branch for pull request (default: {DEFAULT_BASE_BRANCH})')
@click.option('--pr-strategy', type=click.Choice([s.value for s in PRStrategy]), 
              default=PRStrategy.ANY_IMPROVEMENT.value, help='Strategy for when to create PRs (default: ANY_IMPROVEMENT)')
@click.option('--test-github-access', is_flag=True, help='Test GitHub access and permissions before running tests')
def test_all(
    config: str,
    auto_fix: bool,
    create_pr: bool,
    max_retries: int,
    base_branch: str,
    pr_strategy: str,
    test_github_access: bool
) -> None:
    """Run all tests specified in the configuration file.
    
    Args:
        config: Path to the test configuration file
        auto_fix: Whether to automatically fix failing tests
        create_pr: Whether to create a pull request with fixes
        max_retries: Maximum number of retry attempts for auto-fix
        base_branch: Base branch for pull request
        pr_strategy: Strategy for when to create PRs
        test_github_access: Whether to test GitHub access and permissions before running tests
        
    Example:
        >>> test_all(
        ...     config="test_config.yaml",
        ...     auto_fix=True,
        ...     create_pr=True,
        ...     max_retries=2,
        ...     base_branch="main",
        ...     pr_strategy="ANY_IMPROVEMENT",
        ...     test_github_access=True
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
        
        # Load environment variables before testing GitHub access
        if test_github_access or create_pr:
            from ..utils.env_setup import load_environment_variables
            console.print("[dim]Loading environment variables...[/dim]")
            loaded_files = load_environment_variables()
            if loaded_files:
                console.print(f"[dim]Loaded environment from: {', '.join(loaded_files.keys())}[/dim]")
            else:
                console.print("[dim]No .env files found, using system environment variables[/dim]")
        
        # Test GitHub access if requested
        if test_github_access or create_pr:
            console.print("\n[bold blue]Testing GitHub Access...[/bold blue]")
            
            # Check if GITHUB_TOKEN is available
            import os
            github_token = os.environ.get('GITHUB_TOKEN')
            if not github_token:
                console.print("\n[bold red]GITHUB_TOKEN not found in environment variables[/bold red]")
                console.print("\n[bold]Possible solutions:[/bold]")
                console.print("1. Create a .env file in your project root with:")
                console.print("   GITHUB_TOKEN=your_github_token_here")
                console.print("2. Set the environment variable directly:")
                console.print("   export GITHUB_TOKEN=your_github_token_here")
                console.print("3. Check if your .env file is in the correct location")
                console.print("4. Restart your terminal after creating/modifying .env files")
                console.print("\n[bold]For more help, run:[/bold]")
                console.print("   kaizen setup check-env --features github")
                if create_pr:
                    console.print("\n[bold yellow]Warning: PR creation will fail without GITHUB_TOKEN[/bold yellow]")
                    if not click.confirm("Continue with test execution?"):
                        return
                else:
                    return
            
            # Show token status (without exposing the actual token)
            token_preview = github_token[:8] + "..." if len(github_token) > 8 else "***"
            console.print(f"[dim]GitHub token found: {token_preview}[/dim]")
            
            try:
                from kaizen.autofix.pr.manager import PRManager
                pr_manager = PRManager(config.__dict__)
                access_result = pr_manager.test_github_access()
                
                if access_result['overall_status'] == 'full_access':
                    console.print("[bold green]✓ GitHub access test passed[/bold green]")
                elif access_result['overall_status'] == 'limited_branch_access_private':
                    console.print("[bold yellow]⚠ GitHub access test: Partial access (Private Repository)[/bold yellow]")
                    console.print("Branch-level access is limited, but PR creation may still work.")
                else:
                    console.print(f"[bold red]✗ GitHub access test failed: {access_result['overall_status']}[/bold red]")
                    
                    # Display detailed results
                    console.print("\n[bold]Access Test Results:[/bold]")
                    
                    # Repository access
                    repo = access_result['repository']
                    if repo.get('accessible'):
                        console.print(f"  [green]✓ Repository: {repo.get('full_name', 'Unknown')} (Private: {repo.get('private', False)})[/green]")
                    else:
                        console.print(f"  [red]✗ Repository: {repo.get('error', 'Unknown error')}[/red]")
                    
                    # Branch access
                    current_branch = access_result['current_branch']
                    if current_branch.get('accessible'):
                        console.print(f"  [green]✓ Current branch: {current_branch.get('branch_name', 'Unknown')}[/green]")
                    else:
                        console.print(f"  [red]✗ Current branch: {current_branch.get('error', 'Unknown error')}[/red]")
                    
                    base_branch = access_result['base_branch']
                    if base_branch.get('accessible'):
                        console.print(f"  [green]✓ Base branch: {base_branch.get('branch_name', 'Unknown')}[/green]")
                    else:
                        console.print(f"  [red]✗ Base branch: {base_branch.get('error', 'Unknown error')}[/red]")
                    
                    # PR permissions
                    pr_perms = access_result['pr_permissions']
                    if pr_perms.get('can_read'):
                        console.print("  [green]✓ PR permissions: Read access confirmed[/green]")
                    else:
                        console.print(f"  [red]✗ PR permissions: {pr_perms.get('error', 'Unknown error')}[/red]")
                    
                    # Display recommendations
                    console.print("\n[bold]Recommendations:[/bold]")
                    for rec in access_result.get('recommendations', []):
                        console.print(f"  • {rec}")
                    
                    if create_pr:
                        if access_result['overall_status'] == 'limited_branch_access_private':
                            console.print("\n[bold yellow]Note: Limited branch access detected for private repository. PR creation will be attempted but may fail.[/bold yellow]")
                            if not click.confirm("Continue with test execution?"):
                                return
                        else:
                            console.print("\n[bold yellow]Warning: PR creation may fail due to access issues.[/bold yellow]")
                            if not click.confirm("Continue with test execution?"):
                                return
                            
            except Exception as e:
                console.print(f"[bold red]GitHub access test failed: {str(e)}[/bold red]")
                if create_pr:
                    console.print("[bold yellow]Warning: PR creation may fail due to access issues.[/bold yellow]")
                    if not click.confirm("Continue with test execution?"):
                        return
        
        # Execute tests
        command = TestAllCommand(config, logger)
        test_result = command.execute()
        
        
        # # Generate report
        # result_file = _generate_report_path(test_result.value)
        
        # # Use Markdown formatter for file output
        # markdown_formatter = MarkdownTestResultFormatter()
        # report_writer = TestReportWriter(test_result.value, markdown_formatter, logger)
        # report_result = report_writer.write_report(result_file)
        
        # if not report_result.is_success:
        #     _handle_error(report_result.error, "Report generation error")
        
        # # Use Rich formatter for console output
        # rich_formatter = RichTestResultFormatter(console)
        
        # # Display test summary
        # _display_test_summary(console, test_result.value, rich_formatter)
        
        # console.print(f"\nDetailed report saved to: {result_file}")
        
    except Exception as e:
        _handle_error(e, "Unexpected error")
