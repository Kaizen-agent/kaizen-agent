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
from typing import Optional, NoReturn, List, Any, Dict
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
from .memory import ExecutionMemory
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
from kaizen.cli.commands.models.test_execution_result import TestCaseResult, TestStatus, TestExecutionResult

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
    try:
        overall_status = test_result.results.get('overall_status', 'unknown')
        status = overall_status.get('status', 'unknown') if isinstance(overall_status, dict) else overall_status
        formatted_status = rich_formatter.format_status(status)
        console.print(f"\nOverall Status: {formatted_status}")
    except Exception as e:
        console.print(f"\nOverall Status: ❓ UNKNOWN (Error: {str(e)})")
    
    # Display test results table
    try:
        console.print("\nTest Results Table:")
        console.print(rich_formatter.format_table(test_result.results))
    except Exception as e:
        console.print(f"\n[bold red]Error displaying test results table: {str(e)}[/bold red]")
        console.print("[dim]Test results table could not be displayed due to formatting error[/dim]")

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
                    "test_cases_with_errors": len([tc for tc in test_result.unified_result.test_cases if tc.error_message is not None])
                }
                
                detailed_logs["unified_test_results"] = enhanced_unified_data
                
            except Exception as e:
                console.print(f"[yellow]Warning: Could not serialize unified results: {str(e)}[/yellow]")
                detailed_logs["unified_test_results"] = {"error": f"Serialization failed: {str(e)}"}
        
        # Add auto-fix attempts if available
        if test_result.test_attempts is not None:
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
                "error": len([tc for tc in test_result.unified_result.test_cases if tc.status.value == 'error'])
            }
            
            # Add quick reference for failed/error test cases
            failed_tests = []
            for tc in test_result.unified_result.test_cases:
                if tc.status.value in ['failed', 'error']:
                    failed_tests.append({
                        "name": tc.name,
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

def _save_summary_report(console: Console, test_result: TestResult, config: Any) -> None:
    """Save test summary report in Markdown format for later analysis.
    
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
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_filename = f"test_report_{timestamp}.md"
        report_file_path = logs_dir / report_filename
        
        # Import required modules
        from kaizen.autofix.pr.manager import PRManager
        from kaizen.cli.commands.models import TestExecutionHistory
        
        # Create PR manager instance with create_pr=False to avoid GitHub token requirement
        pr_config = config.__dict__.copy()
        pr_config['create_pr'] = False  # Disable PR creation to avoid GitHub token requirement
        
        # Create PR manager instance
        pr_manager = PRManager(pr_config)
        
        # Create test execution history from the test result
        test_history = TestExecutionHistory()
        
        # Add baseline result if available
        if test_result.baseline_result:
            test_history.add_baseline_result(test_result.baseline_result)
            console.print(f"[dim]✓ Baseline results included ({len(test_result.baseline_result.test_cases)} test cases)[/dim]")
        
        # Convert all memory-based attempts (dicts) to TestExecutionResult objects if needed
        if test_result.test_attempts is not None and len(test_result.test_attempts) > 0:
            console.print(f"[dim]DEBUG: Found {len(test_result.test_attempts)} test attempts[/dim]")
            attempts_processed = 0
            for i, attempt_data in enumerate(test_result.test_attempts):
                console.print(f"[dim]DEBUG: Processing attempt {i+1}, type: {type(attempt_data)}[/dim]")
                try:
                    if isinstance(attempt_data, dict):
                        # Handle memory system attempts (which have test_execution_result: None)
                        test_cases = []
                        test_results = attempt_data.get('test_results', {})
                        # Debug print the structure of test_results
                        console.print(f"[dim]DEBUG: test_results structure for attempt {attempt_data.get('attempt_number', 'unknown')}: {repr(test_results)[:300]}[/dim]")
                        # Try to extract test cases from legacy format
                        if 'tests' in test_results and isinstance(test_results['tests'], dict):
                            console.print(f"[dim]DEBUG: Found 'tests' key in test_results[/dim]")
                            for tc_data in test_results['tests'].get('test_cases', []):
                                status_val = tc_data.get('status', 'unknown')
                                if status_val == 'success':
                                    status_val = 'passed'
                                elif status_val == 'fail':
                                    status_val = 'failed'
                                elif status_val == 'error':
                                    status_val = 'error'
                                elif status_val == 'passed':
                                    status_val = 'passed'
                                elif status_val == 'failed':
                                    status_val = 'failed'
                                else:
                                    status_val = 'unknown'
                                try:
                                    status_enum = TestStatus(status_val)
                                except Exception:
                                    status_enum = TestStatus.UNKNOWN
                                test_case = TestCaseResult(
                                    name=tc_data.get('name', f"test_case_{len(test_cases)}"),
                                    status=status_enum,
                                    input=tc_data.get('input'),
                                    expected_output=tc_data.get('expected_output'),
                                    actual_output=tc_data.get('actual_output') if 'actual_output' in tc_data else tc_data.get('output'),
                                    error_message=tc_data.get('error'),
                                    evaluation=tc_data.get('evaluation')
                                )
                                test_cases.append(test_case)
                        # Fallback: handle direct 'test_cases' key (legacy format)
                        elif 'test_cases' in test_results and isinstance(test_results['test_cases'], list):
                            console.print(f"[dim]DEBUG: Found 'test_cases' key in test_results[/dim]")
                            for tc_data in test_results['test_cases']:
                                status_val = tc_data.get('status', 'unknown')
                                if status_val == 'success':
                                    status_val = 'passed'
                                elif status_val == 'fail':
                                    status_val = 'failed'
                                elif status_val == 'error':
                                    status_val = 'error'
                                elif status_val == 'passed':
                                    status_val = 'passed'
                                elif status_val == 'failed':
                                    status_val = 'failed'
                                else:
                                    status_val = 'unknown'
                                try:
                                    status_enum = TestStatus(status_val)
                                except Exception:
                                    status_enum = TestStatus.UNKNOWN
                                test_case = TestCaseResult(
                                    name=tc_data.get('name', f"test_case_{len(test_cases)}"),
                                    status=status_enum,
                                    input=tc_data.get('input'),
                                    expected_output=tc_data.get('expected_output'),
                                    actual_output=tc_data.get('actual_output') if 'actual_output' in tc_data else tc_data.get('output'),
                                    error_message=tc_data.get('error'),
                                    evaluation=tc_data.get('evaluation')
                                )
                                test_cases.append(test_case)
                        else:
                            console.print(f"[dim]DEBUG: No 'tests' or 'test_cases' found in test_results. Keys: {list(test_results.keys())}[/dim]")
                        # If no test_cases, create a dummy failed case to avoid empty attempts
                        if not test_cases:
                            console.print(f"[dim]DEBUG: No test cases extracted, creating dummy case[/dim]")
                            test_cases = [TestCaseResult(
                                name='unknown',
                                status=TestStatus.FAILED,
                                input=None,
                                expected_output=None,
                                actual_output=None,
                                error_message='No test case data',
                                evaluation=None
                            )]
                        # Map status values to valid TestStatus enum values
                        status_str = attempt_data.get('status', 'unknown')
                        if status_str == 'success':
                            status_str = 'passed'
                        elif status_str == 'failed':
                            status_str = 'failed'
                        elif status_str == 'error':
                            status_str = 'error'
                        else:
                            status_str = 'unknown'
                        try:
                            status_enum = TestStatus(status_str)
                        except Exception:
                            status_enum = TestStatus.UNKNOWN
                        execution_result = TestExecutionResult(
                            name=f"attempt_{attempt_data.get('attempt_number', attempts_processed + 1)}",
                            file_path=test_result.file_path,
                            config_path=test_result.config_path,
                            test_cases=test_cases,
                            status=status_enum
                        )
                        test_history.add_fix_attempt_result(execution_result)
                        attempts_processed += 1
                        console.print(f"[dim]DEBUG: Successfully converted attempt {attempt_data.get('attempt_number', 'unknown')} with {len(test_cases)} test cases[/dim]")
                    elif hasattr(attempt_data, 'test_results_after'):
                        # Handle FixAttempt objects from memory system
                        console.print(f"[dim]DEBUG: Processing FixAttempt object[/dim]")
                        test_cases = []
                        test_results = attempt_data.test_results_after
                        # Debug print the structure of test_results
                        console.print(f"[dim]DEBUG: test_results structure for FixAttempt: {repr(test_results)[:300]}[/dim]")
                        # Try to extract test cases from legacy format
                        if 'tests' in test_results and isinstance(test_results['tests'], dict):
                            console.print(f"[dim]DEBUG: Found 'tests' key in test_results[/dim]")
                            for tc_data in test_results['tests'].get('test_cases', []):
                                status_val = tc_data.get('status', 'unknown')
                                if status_val == 'success':
                                    status_val = 'passed'
                                elif status_val == 'fail':
                                    status_val = 'failed'
                                elif status_val == 'error':
                                    status_val = 'error'
                                elif status_val == 'passed':
                                    status_val = 'passed'
                                elif status_val == 'failed':
                                    status_val = 'failed'
                                else:
                                    status_val = 'unknown'
                                try:
                                    status_enum = TestStatus(status_val)
                                except Exception:
                                    status_enum = TestStatus.UNKNOWN
                                test_case = TestCaseResult(
                                    name=tc_data.get('name', f"test_case_{len(test_cases)}"),
                                    status=status_enum,
                                    input=tc_data.get('input'),
                                    expected_output=tc_data.get('expected_output'),
                                    actual_output=tc_data.get('actual_output') if 'actual_output' in tc_data else tc_data.get('output'),
                                    error_message=tc_data.get('error'),
                                    evaluation=tc_data.get('evaluation')
                                )
                                test_cases.append(test_case)
                        # Fallback: handle direct 'test_cases' key (legacy format)
                        elif 'test_cases' in test_results and isinstance(test_results['test_cases'], list):
                            console.print(f"[dim]DEBUG: Found 'test_cases' key in test_results[/dim]")
                            for tc_data in test_results['test_cases']:
                                status_val = tc_data.get('status', 'unknown')
                                if status_val == 'success':
                                    status_val = 'passed'
                                elif status_val == 'fail':
                                    status_val = 'failed'
                                elif status_val == 'error':
                                    status_val = 'error'
                                elif status_val == 'passed':
                                    status_val = 'passed'
                                elif status_val == 'failed':
                                    status_val = 'failed'
                                else:
                                    status_val = 'unknown'
                                try:
                                    status_enum = TestStatus(status_val)
                                except Exception:
                                    status_enum = TestStatus.UNKNOWN
                                test_case = TestCaseResult(
                                    name=tc_data.get('name', f"test_case_{len(test_cases)}"),
                                    status=status_enum,
                                    input=tc_data.get('input'),
                                    expected_output=tc_data.get('expected_output'),
                                    actual_output=tc_data.get('actual_output') if 'actual_output' in tc_data else tc_data.get('output'),
                                    error_message=tc_data.get('error'),
                                    evaluation=tc_data.get('evaluation')
                                )
                                test_cases.append(test_case)
                        else:
                            console.print(f"[dim]DEBUG: No 'tests' or 'test_cases' found in test_results. Keys: {list(test_results.keys())}[/dim]")
                        # If no test_cases, create a dummy failed case to avoid empty attempts
                        if not test_cases:
                            console.print(f"[dim]DEBUG: No test cases extracted, creating dummy case[/dim]")
                            test_cases = [TestCaseResult(
                                name='unknown',
                                status=TestStatus.FAILED,
                                input=None,
                                expected_output=None,
                                actual_output=None,
                                error_message='No test case data',
                                evaluation=None
                            )]
                        # Map status values to valid TestStatus enum values
                        status_str = 'passed' if attempt_data.success else 'failed'
                        try:
                            status_enum = TestStatus(status_str)
                        except Exception:
                            status_enum = TestStatus.UNKNOWN
                        execution_result = TestExecutionResult(
                            name=f"attempt_{attempt_data.attempt_number}",
                            file_path=test_result.file_path,
                            config_path=test_result.config_path,
                            test_cases=test_cases,
                            status=status_enum
                        )
                        test_history.add_fix_attempt_result(execution_result)
                        attempts_processed += 1
                        console.print(f"[dim]DEBUG: Successfully converted FixAttempt {attempt_data.attempt_number} with {len(test_cases)} test cases[/dim]")
                    elif hasattr(attempt_data, 'test_cases'):
                        # Already a TestExecutionResult
                        test_history.add_fix_attempt_result(attempt_data)
                        attempts_processed += 1
                        console.print(f"[dim]DEBUG: Added existing TestExecutionResult[/dim]")
                except Exception as e:
                    console.print(f"[dim]Warning: Could not convert attempt {getattr(attempt_data, 'attempt_number', 'unknown')} to TestExecutionResult: {str(e)}[/dim]")
                    continue

            if attempts_processed > 0:
                console.print(f"[dim]✓ Test attempts included ({attempts_processed} attempts)[/dim]")
            else:
                console.print(f"[dim]✓ Test attempts found but not in TestExecutionResult format ({len(test_result.test_attempts)} attempts)[/dim]")
        # If no test attempts, use unified_result as the only result
        elif test_result.unified_result:
            test_history.add_fix_attempt_result(test_result.unified_result)
            console.print(f"[dim]✓ Test results included ({len(test_result.unified_result.test_cases)} test cases)[/dim]")
        # If no test history available, skip report generation
        if not test_history.get_all_results():
            console.print(f"[dim]No valid test results found, skipping summary report generation[/dim]")
            return
        
        # Use the existing AutoFix logic to create test results for PR
        # This reuses the same transformation logic used for PR creation
        from kaizen.autofix.main import AutoFix
        
        # Create a minimal AutoFix instance just for the transformation method
        # We don't need the full AutoFix functionality, just the data transformation
        class MinimalAutoFix:
            def _create_test_results_for_pr_from_history(self, test_history: TestExecutionHistory) -> Dict:
                """Create test results for PR using test history."""
                # Create agent info
                agent_info = {
                    'name': 'Kaizen AutoFix Agent',
                    'version': '1.0.0',
                    'description': 'Automated code fixing agent using LLM-based analysis'
                }
                
                # Get all results from test history
                all_results = test_history.get_all_results()
                
                # Convert each result to the expected Attempt format
                attempts = []
                for i, result in enumerate(all_results):
                    # Convert test cases to the expected TestCase format
                    test_cases = []
                    for tc in result.test_cases:
                        # Safely serialize evaluation data
                        safe_evaluation = self._safe_serialize_evaluation(tc.evaluation)
                        
                        test_case = {
                            'name': tc.name,
                            'status': tc.status.value,
                            'input': tc.input,
                            'expected_output': tc.expected_output,
                            'actual_output': tc.actual_output,
                            'evaluation': safe_evaluation,
                            'reason': tc.error_message
                        }
                        test_cases.append(test_case)
                    
                    # Create attempt
                    attempt = {
                        'status': result.status.value,
                        'test_cases': test_cases
                    }
                    attempts.append(attempt)
                
                # Create TestResults structure
                test_results_for_pr = {
                    'agent_info': agent_info,
                    'attempts': attempts,
                    'additional_summary': f"Test: {test_result.name}, File: {test_result.file_path}"
                }
                
                return test_results_for_pr
            
            def _safe_serialize_evaluation(self, evaluation):
                """Safely serialize evaluation data to prevent JSON serialization issues."""
                if evaluation is None:
                    return None
                
                try:
                    # Try to serialize as JSON first
                    import json
                    return json.dumps(evaluation, default=str)
                except (TypeError, ValueError) as e:
                    try:
                        # Fallback to string representation
                        return str(evaluation)
                    except Exception as e2:
                        return "Evaluation data unavailable"
        
        # Use the minimal AutoFix instance to transform the data
        minimal_autofix = MinimalAutoFix()
        test_results_for_pr = minimal_autofix._create_test_results_for_pr_from_history(test_history)
        
        # Generate the summary report using the same logic as PR descriptions
        summary_report = pr_manager.generate_summary_report(
            changes={},  # No code changes to show in summary report
            test_results=test_results_for_pr
        )
        
        # Write the summary report to file
        with open(report_file_path, 'w', encoding='utf-8') as f:
            f.write(summary_report)
        
        # Show success message
        console.print(f"[green]✓ Summary report saved: {report_filename}[/green]")
        console.print(f"[dim]  Location: {report_file_path}[/dim]")
        console.print(f"[dim]  Size: {report_file_path.stat().st_size / 1024:.1f} KB[/dim]")
        
        # Show what was included
        all_results = test_history.get_all_results()
        if all_results:
            console.print(f"[dim]✓ Test results included ({len(all_results)} attempts)[/dim]")
            total_test_cases = sum(len(result.test_cases) for result in all_results)
            console.print(f"[dim]  - Total test cases: {total_test_cases}[/dim]")
            
            # Show breakdown of attempts
            if test_result.baseline_result:
                console.print(f"[dim]  - Baseline: {len(test_result.baseline_result.test_cases)} test cases[/dim]")
            if test_result.test_attempts:
                console.print(f"[dim]  - Auto-fix attempts: {len(test_result.test_attempts)} attempts[/dim]")
        
        # Provide guidance on how to use the report
        console.print(f"\n[bold]Summary Report Information:[/bold]")
        console.print(f"[dim]• Contains the same detailed test summary used in PR descriptions[/dim]")
        console.print(f"[dim]• Includes baseline results and all auto-fix attempts[/dim]")
        console.print(f"[dim]• Shows test results table and detailed analysis[/dim]")
        console.print(f"[dim]• Can be viewed in any Markdown viewer or text editor[/dim]")
        
        return report_file_path
        
    except Exception as e:
        console.print(f"[bold red]Warning: Failed to save summary report: {str(e)}[/bold red]")
        # Add more detailed error information for debugging
        import traceback
        console.print(f"[dim]Error details: {traceback.format_exc()}[/dim]")
        return None

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
@click.option('--save-logs', is_flag=True, help='Save detailed test logs in JSON format and summary report in Markdown format for later analysis')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed debug information and verbose logging')
@click.option('--clear-ts-cache', is_flag=True, help='Clear TypeScript compilation cache before running tests')
@click.option('--show-cache-stats', is_flag=True, help='Show TypeScript cache statistics')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation prompts (useful for non-interactive use)')
@click.option('--better-ai', is_flag=True, help='Use enhanced AI model for improved code fixing and analysis')
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
    no_confirm: bool,
    better_ai: bool
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
        no_confirm: Whether to skip confirmation prompts (useful for non-interactive use)
        better_ai: Whether to use enhanced AI model for improved code fixing and analysis
        
    When --save-logs is enabled, the following files are created in the test-logs/ directory:
    - {test_name}_{timestamp}_detailed_logs.json: Complete test results including inputs, outputs, 
      evaluations, and auto-fix attempts
    - {test_name}_{timestamp}_summary.json: Quick reference summary with key metrics
    - test_report_{timestamp}.md: Detailed test summary report in Markdown format (same as PR descriptions)
    
    The detailed logs include:
    - Test metadata and configuration
    - Individual test case results with inputs and outputs
    - LLM evaluation results and scores
    - Auto-fix attempts and their outcomes
    - Error details and stack traces
    - Execution timing information
    
    The summary report (.md file) includes:
    - Comprehensive test summary (same format as PR descriptions)
    - Test results table showing all attempts
    - Detailed analysis of improvements and regressions
    - Agent information and execution details
        
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
        ...     verbose=False,
        ...     better_ai=True
        ... )
    """
    # Initialize clean logger
    logger = CleanLogger(verbose=verbose)
    
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
            pr_strategy=pr_strategy,
            better_ai=better_ai
        )
        
        if not config_result.is_success:
            _handle_error(config_result.error, "Configuration error", logger)
        
        config = config_result.value
        logger.print_success(f"Configuration loaded: {config.name}")
        logger.info(f"Language: {config.language.value}")
        
        # Log better AI status if enabled
        if config.better_ai:
            logger.print_success("Enhanced AI model enabled for improved code fixing and analysis")
        
        # Handle TypeScript cache management
        if clear_ts_cache or show_cache_stats:
            from .utils.ts_cache_manager import TypeScriptCacheManager
            ts_cache_manager = TypeScriptCacheManager(logger.console)
            ts_cache_manager.handle_cache_operations(clear_ts_cache, show_cache_stats)
        
        # Handle user confirmations
        from .utils.confirmation_manager import ConfirmationManager
        confirmation_manager = ConfirmationManager(logger.console)
        
        # Confirm auto-fix operation if enabled
        if auto_fix:
            if not confirmation_manager.confirm_auto_fix(config, max_retries, no_confirm):
                auto_fix = False
                config.auto_fix = False
        
        # Confirm PR creation if enabled
        if create_pr:
            if not confirmation_manager.confirm_pr_creation(base_branch, pr_strategy, no_confirm):
                create_pr = False
                config.create_pr = False
        
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
            
            # Check GitHub token availability
            if not confirmation_manager.check_github_token(create_pr, no_confirm):
                return
            
            # Test GitHub access
            if not confirmation_manager.test_github_access(config, create_pr, no_confirm, verbose):
                return
        
        # Initialize memory system for execution tracking
        from datetime import datetime
        execution_id = f"kaizen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        memory = ExecutionMemory()
        memory.start_execution(execution_id, config, config_manager)
        
        # Save original code before any modifications
        if hasattr(config, 'files_to_fix') and config.files_to_fix:
            from .utils.code_extractor import extract_relevant_functions
            for file_path in config.files_to_fix:
                try:
                    with open(file_path, 'r') as f:
                        original_content = f.read()
                    
                    # Create agent config from the test configuration
                    agent_config = None
                    if hasattr(config, 'agent') and config.agent:
                        agent_config = {
                            'agent': {
                                'module': config.agent.module,
                                'class': config.agent.class_name,
                                'method': config.agent.method,
                                'fallback_to_function': config.agent.fallback_to_function
                            }
                        }
                    
                    # Extract relevant functions using the enhanced code extractor
                    relevant_sections = extract_relevant_functions(original_content, file_path, agent_config)
                    memory.save_original_relevant_code(file_path, relevant_sections)
                    logger.info(f"Saved original code sections for {file_path}: {list(relevant_sections.keys())}")
                except Exception as e:
                    logger.warning(f"Could not save original code for {file_path}: {str(e)}")
        
        # Execute tests with memory tracking
        logger.print_progress("Running tests...")
        command = TestAllCommand(config, logger.logger if verbose else logger, verbose=verbose, memory=memory, config_manager=config_manager)
        test_result = command.execute()
        
        if not test_result.is_success:
            _handle_error(test_result.error, "Test execution error", logger)
        
        # Display results
        test_result_value = test_result.value
        try:
            overall_status = test_result_value.results.get('overall_status', {})
            if isinstance(overall_status, dict):
                status = overall_status.get('status', 'unknown')
            else:
                status = overall_status
        except Exception as e:
            logger.print_error(f"Error determining test status: {str(e)}")
            status = 'unknown'
        
        if status == 'passed':
            logger.print_success(f"All tests passed! ({test_result_value.name})")
        else:
            logger.print_error(f"Tests failed! ({test_result_value.name})")
            if not verbose:
                logger.print("[dim]Run with --verbose to see detailed test results[/dim]")
            
            # If auto-fix is enabled and tests failed, ask for confirmation before proceeding
            if auto_fix and config.auto_fix:
                if not confirmation_manager.confirm_auto_fix_after_failure(test_result_value, no_confirm):
                    config.auto_fix = False
        
        # Save detailed logs if requested
        if save_logs:
            _save_detailed_logs(logger.console, test_result_value, config)
            # Also save summary report in Markdown format
            _save_summary_report(logger.console, test_result_value, config)
        
        # Show detailed results in verbose mode
        if verbose:
            # Use Rich formatter for console output
            rich_formatter = RichTestResultFormatter(logger.console)
            
            # Display test summary
            _display_test_summary(logger.console, test_result_value, rich_formatter)
        
        # If auto-fix was performed and PR creation is enabled, ask for confirmation before creating PR
        if (auto_fix and config.auto_fix and create_pr and config.create_pr and 
            test_result_value.test_attempts and len(test_result_value.test_attempts) > 0):
            
            if not confirmation_manager.confirm_pr_creation_after_auto_fix(test_result_value, base_branch, pr_strategy, no_confirm):
                config.create_pr = False
        
    except Exception as e:
        _handle_error(e, "Unexpected error", logger)


