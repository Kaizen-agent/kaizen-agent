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
from typing import Optional, NoReturn, List, Any
import json

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
    TestStatus,
    Language,
    DEFAULT_LANGUAGE
)
from .models import TestResult

# Configure rich traceback
install_rich_traceback(show_locals=True)

class CleanLogger:
    """A logger that provides clean, concise output by default."""
    
    def __init__(self, verbose: bool = False):
        """Initialize the clean logger.
        
        Args:
            verbose: Whether to show detailed debug information
        """
        self.verbose = verbose
        self.console = Console()
        
        # Configure logging based on verbose flag
        if verbose:
            # Full logging for verbose mode
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(message)s",
                datefmt="[%X]",
                handlers=[RichHandler(rich_tracebacks=True)]
            )
            # Set all kaizen loggers to DEBUG level
            logging.getLogger("kaizen").setLevel(logging.DEBUG)
        else:
            # Clean logging for normal mode - show info, warnings and errors
            logging.basicConfig(
                level=logging.INFO,
                format="%(message)s",
                datefmt="[%X]",
                handlers=[RichHandler(rich_tracebacks=True)]
            )
            # Set all kaizen loggers to INFO level to show progress messages
            logging.getLogger("kaizen").setLevel(logging.INFO)
        
        self.logger = logging.getLogger("kaizen.test")
    
    def info(self, message: str) -> None:
        """Log info message (shown in both normal and verbose mode)."""
        self.logger.info(message)
    
    def debug(self, message: str) -> None:
        """Log debug message (only shown in verbose mode)."""
        if self.verbose:
            self.logger.debug(message)
    
    def warning(self, message: str) -> None:
        """Log warning message (always shown)."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message (always shown)."""
        self.logger.error(message)
    
    def print(self, message: str, style: str = None) -> None:
        """Print a message to console (always shown)."""
        self.console.print(message, style=style)
    
    def print_progress(self, message: str) -> None:
        """Print a progress message (always shown, clean format)."""
        self.console.print(f"[blue]→[/blue] {message}")
    
    def print_success(self, message: str) -> None:
        """Print a success message (always shown)."""
        self.console.print(f"[bold green]✓[/bold green] {message}")
    
    def print_error(self, message: str) -> None:
        """Print an error message (always shown)."""
        self.console.print(f"[bold red]✗[/bold red] {message}")

def _handle_error(error: Exception, message: str, logger: CleanLogger = None) -> NoReturn:
    """Handle errors in a consistent way.
    
    Args:
        error: The exception that occurred
        message: Error message to display
        logger: CleanLogger instance (optional)
        
    Raises:
        click.Abort: Always raises to abort the command
    """
    if logger:
        logger.print_error(f"{message}: {str(error)}")
    else:
        # Fallback to standard logging if no logger provided
        logging.error(f"{message}: {str(error)}")
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

def _save_detailed_logs(console: Console, test_result: TestResult, config: Any) -> None:
    """Save detailed test logs in JSON format for later analysis.
    
    Args:
        console: Rich console for output
        test_result: The test result to save
        config: Test configuration
    """
    try:
        # Create logs directory
        logs_dir = Path("test-logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{test_result.name}_{timestamp}_detailed_logs.json"
        log_file_path = logs_dir / log_filename
        
        # Prepare detailed log data
        detailed_logs = {
            "metadata": {
                "test_name": test_result.name,
                "file_path": str(test_result.file_path),
                "config_path": str(test_result.config_path),
                "start_time": test_result.start_time.isoformat(),
                "end_time": test_result.end_time.isoformat(),
                "status": test_result.status,
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "auto_fix": getattr(config, 'auto_fix', False),
                    "create_pr": getattr(config, 'create_pr', False),
                    "max_retries": getattr(config, 'max_retries', 0),
                    "base_branch": getattr(config, 'base_branch', 'main'),
                    "pr_strategy": getattr(config, 'pr_strategy', 'ANY_IMPROVEMENT')
                }
            },
            "test_results": test_result.results,
            "error": test_result.error,
            "steps": test_result.steps
        }
        
        # Add unified test results if available with enhanced test case details
        if test_result.unified_result:
            try:
                unified_data = test_result.unified_result.to_dict()
                
                # Enhance the unified results with more detailed test case information
                enhanced_unified_data = {
                    **unified_data,
                    "test_cases_detailed": []
                }
                
                # Add detailed information for each test case
                for tc in test_result.unified_result.test_cases:
                    detailed_tc = {
                        "name": tc.name,
                        "status": tc.status.value,
                        "region": tc.region,
                        "input": tc.input,
                        "expected_output": tc.expected_output,
                        "actual_output": tc.actual_output,
                        "error_message": tc.error_message,
                        "error_details": tc.error_details,
                        "evaluation": tc.evaluation,
                        "evaluation_score": tc.evaluation_score,
                        "execution_time": tc.execution_time,
                        "timestamp": tc.timestamp.isoformat() if tc.timestamp else None,
                        "metadata": tc.metadata,
                        # Add human-readable summary for quick scanning
                        "summary": {
                            "passed": tc.status.value in ['passed'],
                            "failed": tc.status.value in ['failed', 'error'],
                            "has_error": tc.error_message is not None,
                            "has_evaluation": tc.evaluation is not None,
                            "input_type": type(tc.input).__name__ if tc.input is not None else None,
                            "output_type": type(tc.actual_output).__name__ if tc.actual_output is not None else None,
                            "expected_type": type(tc.expected_output).__name__ if tc.expected_output is not None else None
                        }
                    }
                    enhanced_unified_data["test_cases_detailed"].append(detailed_tc)
                
                # Add summary statistics for quick reference
                enhanced_unified_data["test_summary"] = {
                    "total_test_cases": len(test_result.unified_result.test_cases),
                    "passed_test_cases": len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'passed']),
                    "failed_test_cases": len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'failed']),
                    "error_test_cases": len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'error']),
                    "test_cases_with_evaluations": len([tc for tc in test_result.unified_result.test_cases if tc.evaluation is not None]),
                    "test_cases_with_errors": len([tc for tc in test_result.unified_result.test_cases if tc.error_message is not None]),
                    "regions": list(set(tc.region for tc in test_result.unified_result.test_cases))
                }
                
                detailed_logs["unified_test_results"] = enhanced_unified_data
                
            except Exception as e:
                console.print(f"[yellow]Warning: Could not serialize unified results: {str(e)}[/yellow]")
                detailed_logs["unified_test_results"] = {"error": f"Serialization failed: {str(e)}"}
        
        # Add auto-fix attempts if available
        if test_result.test_attempts:
            detailed_logs["auto_fix_attempts"] = test_result.test_attempts
        
        # Save to JSON file
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(detailed_logs, f, indent=2, ensure_ascii=False, default=str)
        
        console.print(f"\n[bold green]✓ Detailed test logs saved to: {log_file_path}[/bold green]")
        console.print(f"[dim]File size: {log_file_path.stat().st_size / 1024:.1f} KB[/dim]")
        
        # Also save a summary file for quick reference
        summary_filename = f"{test_result.name}_{timestamp}_summary.json"
        summary_file_path = logs_dir / summary_filename
        
        # Enhanced summary with test case details
        summary_data = {
            "test_name": test_result.name,
            "status": test_result.status,
            "timestamp": datetime.now().isoformat(),
            "file_path": str(test_result.file_path),
            "config_path": str(test_result.config_path),
            "start_time": test_result.start_time.isoformat(),
            "end_time": test_result.end_time.isoformat(),
            "error": test_result.error,
            "overall_status": test_result.results.get('overall_status', {}),
            "detailed_logs_file": log_filename,
            "has_unified_results": test_result.unified_result is not None,
            "has_auto_fix_attempts": test_result.test_attempts is not None,
            "auto_fix_attempts_count": len(test_result.test_attempts) if test_result.test_attempts else 0
        }
        
        # Add test case summary if unified results are available
        if test_result.unified_result:
            summary_data["test_cases_summary"] = {
                "total": len(test_result.unified_result.test_cases),
                "passed": len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'passed']),
                "failed": len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'failed']),
                "error": len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'error']),
                "regions": list(set(tc.region for tc in test_result.unified_result.test_cases))
            }
            
            # Add quick reference for failed/error test cases
            failed_tests = []
            for tc in test_result.unified_result.test_cases:
                if tc.status.value in ['failed', 'error']:
                    failed_tests.append({
                        "name": tc.name,
                        "region": tc.region,
                        "status": tc.status.value,
                        "input": tc.input,
                        "expected_output": tc.expected_output,
                        "actual_output": tc.actual_output,
                        "error_message": tc.error_message,
                        "evaluation_score": tc.evaluation_score
                    })
            summary_data["failed_test_cases"] = failed_tests
        
        with open(summary_file_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False, default=str)
        
        console.print(f"[dim]Summary file saved to: {summary_file_path}[/dim]")
        
        # Show what was saved with enhanced information
        if test_result.unified_result:
            total_tests = len(test_result.unified_result.test_cases)
            passed_tests = len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'passed'])
            failed_tests = len([tc for tc in test_result.unified_result.test_cases if tc.status.value in ['failed', 'error']])
            
            console.print(f"[dim]✓ Unified test results included ({total_tests} test cases)[/dim]")
            console.print(f"[dim]  - Passed: {passed_tests}, Failed/Error: {failed_tests}[/dim]")
            console.print(f"[dim]  - Regions: {', '.join(set(tc.region for tc in test_result.unified_result.test_cases))}[/dim]")
            
            # Show failed test cases for quick reference
            if failed_tests > 0:
                console.print(f"[dim]  - Failed tests: {', '.join(tc.name for tc in test_result.unified_result.test_cases if tc.status.value in ['failed', 'error'])}[/dim]")
        
        if test_result.test_attempts:
            console.print(f"[dim]✓ Auto-fix attempts included ({len(test_result.test_attempts)} attempts)[/dim]")
        
        # Provide guidance on how to analyze the logs
        console.print(f"\n[bold]How to analyze the logs:[/bold]")
        console.print(f"[dim]1. Open {log_filename} for complete test details[/dim]")
        console.print(f"[dim]2. Check 'test_cases_detailed' section for individual test inputs/outputs[/dim]")
        console.print(f"[dim]3. Use 'test_summary' for quick statistics[/dim]")
        console.print(f"[dim]4. Review {summary_filename} for failed test cases overview[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Warning: Failed to save detailed logs: {str(e)}[/bold red]")
        # Note: Removed the self.verbose check since this function doesn't have access to self

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=DEFAULT_MAX_RETRIES, help=f'Maximum number of retry attempts for auto-fix (default: {DEFAULT_MAX_RETRIES})')
@click.option('--base-branch', default=DEFAULT_BASE_BRANCH, help=f'Base branch for pull request (default: {DEFAULT_BASE_BRANCH})')
@click.option('--pr-strategy', type=click.Choice([s.value for s in PRStrategy]), 
              default=PRStrategy.ANY_IMPROVEMENT.value, help='Strategy for when to create PRs (default: ANY_IMPROVEMENT)')
@click.option('--language', type=click.Choice([l.value for l in Language]), 
              default=DEFAULT_LANGUAGE.value, help=f'Programming language for test execution (default: {DEFAULT_LANGUAGE.value})')
@click.option('--test-github-access', is_flag=True, help='Test GitHub access and permissions before running tests')
@click.option('--save-logs', is_flag=True, help='Save detailed test logs in JSON format for later analysis')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed debug information and verbose logging')
@click.option('--clear-ts-cache', is_flag=True, help='Clear TypeScript compilation cache before running tests')
@click.option('--show-cache-stats', is_flag=True, help='Show TypeScript cache statistics')
@click.option('--debug-ts', is_flag=True, help='Enable detailed TypeScript execution debugging')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation prompts (useful for non-interactive use)')
def test_all(
    config: str,
    auto_fix: bool,
    create_pr: bool,
    max_retries: int,
    base_branch: str,
    pr_strategy: str,
    language: str,
    test_github_access: bool,
    save_logs: bool,
    verbose: bool,
    clear_ts_cache: bool,
    show_cache_stats: bool,
    debug_ts: bool,
    no_confirm: bool
) -> None:
    """Run all tests specified in the configuration file.
    
    This command executes tests based on the provided configuration file. It supports
    automatic fixing of failing tests, creating pull requests with fixes, and saving
    detailed test logs for later analysis.
    
    By default, this command provides clean, concise output showing only essential
    information. Use --verbose to see detailed debug information and step-by-step
    execution logs.
    
    The command includes several confirmation steps to ensure user awareness:
    1. Before auto-fix: Confirms that code files will be modified
    2. Before PR creation: Confirms that a pull request will be created
    3. After test failure: Confirms auto-fix should proceed (if enabled)
    4. After auto-fix: Confirms PR creation should proceed (if both enabled)
    
    Use --no-confirm to skip all confirmation prompts (useful for CI/CD pipelines).
    
    Args:
        config: Path to the test configuration file
        auto_fix: Whether to automatically fix failing tests
        create_pr: Whether to create a pull request with fixes
        max_retries: Maximum number of retry attempts for auto-fix
        base_branch: Base branch for pull request
        pr_strategy: Strategy for when to create PRs
        language: Programming language for test execution
        test_github_access: Whether to test GitHub access and permissions before running tests
        save_logs: Whether to save detailed test logs in JSON format for later analysis
        verbose: Whether to show detailed debug information and verbose logging
        clear_ts_cache: Whether to clear TypeScript compilation cache before running tests
        show_cache_stats: Whether to show TypeScript cache statistics
        debug_ts: Whether to enable detailed TypeScript execution debugging
        no_confirm: Whether to skip confirmation prompts (useful for non-interactive use)
        
    When --save-logs is enabled, the following files are created in the test-logs/ directory:
    - {test_name}_{timestamp}_detailed_logs.json: Complete test results including inputs, outputs, 
      evaluations, and auto-fix attempts
    - {test_name}_{timestamp}_summary.json: Quick reference summary with key metrics
    
    The detailed logs include:
    - Test metadata and configuration
    - Individual test case results with inputs and outputs
    - LLM evaluation results and scores
    - Auto-fix attempts and their outcomes
    - Error details and stack traces
    - Execution timing information
        
    Example:
        >>> test_all(
        ...     config="test_config.yaml",
        ...     auto_fix=True,
        ...     create_pr=True,
        ...     max_retries=2,
        ...     base_branch="main",
        ...     pr_strategy="ANY_IMPROVEMENT",
        ...     language="python",
        ...     test_github_access=True,
        ...     save_logs=True,
        ...     verbose=False
        ... )
    """
    # Initialize clean logger
    logger = CleanLogger(verbose=verbose)
    
    # Enable detailed TypeScript debugging if requested
    if debug_ts:
        logger.print_progress("Enabling detailed TypeScript debugging...")
        # Set TypeScript logger to DEBUG level
        ts_logger = logging.getLogger("kaizen.autofix.test.code_region")
        ts_logger.setLevel(logging.DEBUG)
        # Also enable debug for the main test logger
        logging.getLogger("kaizen").setLevel(logging.DEBUG)
        logger.print_success("TypeScript debugging enabled")
    
    try:
        # Load configuration
        logger.print_progress("Loading test configuration...")
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
            _handle_error(config_result.error, "Configuration error", logger)
        
        config = config_result.value
        logger.print_success(f"Configuration loaded: {config.name}")
        logger.info(f"Language: {config.language.value}")
        
        # Handle TypeScript cache management
        if clear_ts_cache or show_cache_stats:
            from kaizen.autofix.test.code_region import CodeRegionExecutor
            temp_executor = CodeRegionExecutor(Path.cwd())
            
            if clear_ts_cache:
                logger.print_progress("Clearing TypeScript compilation cache...")
                temp_executor.clear_cache()
                logger.print_success("TypeScript cache cleared")
            
            if show_cache_stats:
                stats = temp_executor.get_cache_stats()
                logger.print("\n[bold]TypeScript Cache Statistics:[/bold]")
                logger.print(f"  • Execution cache entries: {stats['execution_cache_size']}")
                logger.print(f"  • Compiled modules: {stats['compiled_modules_size']}")
                logger.print(f"  • Cache directory: {stats['ts_cache_directory']}")
                logger.print("")
        
        # Confirm auto-fix operation if enabled
        if auto_fix:
            logger.print("\n[bold yellow]⚠ Auto-fix Warning[/bold yellow]")
            logger.print("Auto-fix will attempt to modify your code files to fix failing tests.")
            logger.print("This may change your existing code and could potentially introduce new issues.")
            logger.print(f"Maximum retry attempts: {max_retries}")
            logger.print("\n[bold]Files that may be modified:[/bold]")
            
            # Show files that will be tested/modified
            if hasattr(config, 'files_to_fix') and config.files_to_fix:
                for file_path in config.files_to_fix:
                    logger.print(f"  • {file_path}")
            else:
                logger.print("  • Files specified in test configuration")
            
            if no_confirm:
                logger.print_success("Auto-fix confirmed (--no-confirm flag used)")
            elif not click.confirm("\n[bold]Do you want to proceed with auto-fix?[/bold]"):
                logger.print("[dim]Auto-fix cancelled by user[/dim]")
                auto_fix = False
                # Update config to disable auto-fix
                config.auto_fix = False
            else:
                logger.print_success("Auto-fix confirmed - proceeding with automatic fixes")
        
        # Confirm PR creation if enabled
        if create_pr:
            logger.print("\n[bold yellow]⚠ Pull Request Creation Warning[/bold yellow]")
            logger.print("This will create a pull request on GitHub with the fixes applied.")
            logger.print(f"Base branch: {base_branch}")
            logger.print(f"PR strategy: {pr_strategy}")
            logger.print("\n[bold]What will happen:[/bold]")
            logger.print("  • A new branch will be created with your fixes")
            logger.print("  • A pull request will be opened against the base branch")
            logger.print("  • You'll need to review and merge the PR manually")
            
            if no_confirm:
                logger.print_success("PR creation confirmed (--no-confirm flag used)")
            elif not click.confirm("\n[bold]Do you want to proceed with PR creation?[/bold]"):
                logger.print("[dim]PR creation cancelled by user[/dim]")
                create_pr = False
                # Update config to disable PR creation
                config.create_pr = False
            else:
                logger.print_success("PR creation confirmed - will create pull request after fixes")
        
        # Load environment variables before testing GitHub access
        if test_github_access or create_pr:
            from ..utils.env_setup import load_environment_variables
            logger.print_progress("Loading environment variables...")
            loaded_files = load_environment_variables()
            if loaded_files:
                logger.info(f"Loaded environment from: {', '.join(loaded_files.keys())}")
            else:
                logger.info("No .env files found, using system environment variables")
        
        # Test GitHub access if requested
        if test_github_access or create_pr:
            logger.print_progress("Testing GitHub access...")
            
            # Check if GITHUB_TOKEN is available
            import os
            github_token = os.environ.get('GITHUB_TOKEN')
            if not github_token:
                logger.print_error("GITHUB_TOKEN not found in environment variables")
                logger.print("\n[bold]Possible solutions:[/bold]")
                logger.print("1. Create a .env file in your project root with:")
                logger.print("   GITHUB_TOKEN=your_github_token_here")
                logger.print("2. Set the environment variable directly:")
                logger.print("   export GITHUB_TOKEN=your_github_token_here")
                logger.print("3. Check if your .env file is in the correct location")
                logger.print("4. Restart your terminal after creating/modifying .env files")
                logger.print("\n[bold]For more help, run:[/bold]")
                logger.print("   kaizen setup check-env --features github")
                if create_pr:
                    logger.print("\n[bold yellow]Warning: PR creation will fail without GITHUB_TOKEN[/bold yellow]")
                    if not no_confirm and not click.confirm("Continue with test execution?"):
                        return
                else:
                    return
            
            # Show token status (without exposing the actual token)
            token_preview = github_token[:8] + "..." if len(github_token) > 8 else "***"
            logger.info(f"GitHub token found: {token_preview}")
            
            try:
                from kaizen.autofix.pr.manager import PRManager
                pr_manager = PRManager(config.__dict__)
                access_result = pr_manager.test_github_access()
                
                if access_result['overall_status'] == 'full_access':
                    logger.print_success("GitHub access test passed")
                elif access_result['overall_status'] == 'limited_branch_access_private':
                    logger.print("[bold yellow]⚠ GitHub access test: Partial access (Private Repository)[/bold yellow]")
                    logger.print("Branch-level access is limited, but PR creation may still work.")
                else:
                    logger.print_error(f"GitHub access test failed: {access_result['overall_status']}")
                    
                    # Display detailed results only in verbose mode
                    if verbose:
                        logger.print("\n[bold]Access Test Results:[/bold]")
                        
                        # Repository access
                        repo = access_result['repository']
                        if repo.get('accessible'):
                            logger.print(f"  [green]✓ Repository: {repo.get('full_name', 'Unknown')} (Private: {repo.get('private', False)})[/green]")
                        else:
                            logger.print(f"  [red]✗ Repository: {repo.get('error', 'Unknown error')}[/red]")
                        
                        # Branch access
                        current_branch = access_result['current_branch']
                        if current_branch.get('accessible'):
                            logger.print(f"  [green]✓ Current branch: {current_branch.get('branch_name', 'Unknown')}[/green]")
                        else:
                            logger.print(f"  [red]✗ Current branch: {current_branch.get('error', 'Unknown error')}[/red]")
                        
                        base_branch = access_result['base_branch']
                        if base_branch.get('accessible'):
                            logger.print(f"  [green]✓ Base branch: {base_branch.get('branch_name', 'Unknown')}[/green]")
                        else:
                            logger.print(f"  [red]✗ Base branch: {base_branch.get('error', 'Unknown error')}[/red]")
                        
                        # PR permissions
                        pr_perms = access_result['pr_permissions']
                        if pr_perms.get('can_read'):
                            logger.print("  [green]✓ PR permissions: Read access confirmed[/green]")
                        else:
                            logger.print(f"  [red]✗ PR permissions: {pr_perms.get('error', 'Unknown error')}[/red]")
                        
                        # Display recommendations
                        logger.print("\n[bold]Recommendations:[/bold]")
                        for rec in access_result.get('recommendations', []):
                            logger.print(f"  • {rec}")
                    
                    if create_pr:
                        if access_result['overall_status'] == 'limited_branch_access_private':
                            logger.print("\n[bold yellow]Note: Limited branch access detected for private repository. PR creation will be attempted but may fail.[/bold yellow]")
                            if not no_confirm and not click.confirm("Continue with test execution?"):
                                return
                        else:
                            logger.print("\n[bold yellow]Warning: PR creation may fail due to access issues.[/bold yellow]")
                            if not no_confirm and not click.confirm("Continue with test execution?"):
                                return
                            
            except Exception as e:
                logger.print_error(f"GitHub access test failed: {str(e)}")
                if create_pr:
                    logger.print("[bold yellow]Warning: PR creation may fail due to access issues.[/bold yellow]")
                    if not no_confirm and not click.confirm("Continue with test execution?"):
                        return
        
        # Execute tests
        logger.print_progress("Running tests...")
        command = TestAllCommand(config, logger.logger if verbose else logger, verbose=verbose)
        test_result = command.execute()
        
        if not test_result.is_success:
            _handle_error(test_result.error, "Test execution error", logger)
        
        # Display results
        test_result_value = test_result.value
        overall_status = test_result_value.results.get('overall_status', {})
        if isinstance(overall_status, dict):
            status = overall_status.get('status', 'unknown')
        else:
            status = overall_status
        
        if status == 'passed':
            logger.print_success(f"All tests passed! ({test_result_value.name})")
        else:
            logger.print_error(f"Tests failed! ({test_result_value.name})")
            if not verbose:
                logger.print("[dim]Run with --verbose to see detailed test results[/dim]")
            
            # If auto-fix is enabled and tests failed, ask for confirmation before proceeding
            if auto_fix and config.auto_fix:
                logger.print("\n[bold yellow]⚠ Auto-fix Confirmation[/bold yellow]")
                logger.print("Tests have failed. Auto-fix will now attempt to fix the failing tests.")
                logger.print("This will modify your code files and may introduce changes.")
                
                # Show a brief summary of what failed (if available)
                if test_result_value.unified_result:
                    failed_tests = [tc for tc in test_result_value.unified_result.test_cases if tc.status.value in ['failed', 'error']]
                    if failed_tests:
                        logger.print(f"\n[bold]Failed test cases ({len(failed_tests)}):[/bold]")
                        for tc in failed_tests[:3]:  # Show first 3 failed tests
                            logger.print(f"  • {tc.name} ({tc.region})")
                        if len(failed_tests) > 3:
                            logger.print(f"  • ... and {len(failed_tests) - 3} more")
                
                if no_confirm:
                    logger.print_success("Auto-fix confirmed (--no-confirm flag used)")
                elif not click.confirm("\n[bold]Do you want to proceed with auto-fix?[/bold]"):
                    logger.print("[dim]Auto-fix cancelled by user after seeing test results[/dim]")
                    # Update config to disable auto-fix
                    config.auto_fix = False
                else:
                    logger.print_success("Proceeding with auto-fix to resolve failing tests")
        
        # Save detailed logs if requested
        if save_logs:
            _save_detailed_logs(logger.console, test_result_value, config)
        
        # Show detailed results in verbose mode
        if verbose:
            # Use Rich formatter for console output
            rich_formatter = RichTestResultFormatter(logger.console)
            
            # Display test summary
            _display_test_summary(logger.console, test_result_value, rich_formatter)
        
        # If auto-fix was performed and PR creation is enabled, ask for confirmation before creating PR
        if (auto_fix and config.auto_fix and create_pr and config.create_pr and 
            test_result_value.test_attempts and len(test_result_value.test_attempts) > 0):
            
            logger.print("\n[bold yellow]⚠ Pull Request Creation Confirmation[/bold yellow]")
            logger.print("Auto-fix has been completed. A pull request will now be created with the fixes.")
            logger.print(f"Base branch: {base_branch}")
            logger.print(f"PR strategy: {pr_strategy}")
            
            # Show auto-fix summary
            if test_result_value.test_attempts:
                logger.print(f"\n[bold]Auto-fix summary:[/bold]")
                logger.print(f"  • Attempts made: {len(test_result_value.test_attempts)}")
                
                # Count successful fixes
                successful_fixes = sum(1 for attempt in test_result_value.test_attempts 
                                     if attempt.get('status') == 'success')
                logger.print(f"  • Successful fixes: {successful_fixes}")
                
                # Show what was fixed
                if test_result_value.unified_result:
                    fixed_tests = [tc for tc in test_result_value.unified_result.test_cases 
                                 if tc.status.value == 'passed']
                    if fixed_tests:
                        logger.print(f"  • Tests now passing: {len(fixed_tests)}")
            
            if no_confirm:
                logger.print_success("PR creation confirmed (--no-confirm flag used)")
            elif not click.confirm("\n[bold]Do you want to create a pull request with these fixes?[/bold]"):
                logger.print("[dim]PR creation cancelled by user after auto-fix[/dim]")
                # Update config to disable PR creation
                config.create_pr = False
            else:
                logger.print_success("Proceeding with pull request creation")
        
    except Exception as e:
        _handle_error(e, "Unexpected error", logger)
