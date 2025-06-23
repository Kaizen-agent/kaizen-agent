"""Test log analyzer utility.

This module provides utilities to analyze and display test logs saved by the CLI.
It helps users quickly scan through test results and understand what outputs
were generated for each test case.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

class TestLogAnalyzer:
    """Analyzer for test logs saved by the CLI."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the analyzer.
        
        Args:
            console: Rich console for output (creates new one if not provided)
        """
        self.console = console or Console()
    
    def analyze_log_file(self, log_file_path: Path, show_details: bool = False) -> None:
        """Analyze a test log file and display results.
        
        Args:
            log_file_path: Path to the log file to analyze
            show_details: Whether to show detailed test case information
        """
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            self.console.print(f"\n[bold blue]Test Log Analysis: {log_file_path.name}[/bold blue]")
            self.console.print("=" * 80)
            
            # Display metadata
            self._display_metadata(log_data.get('metadata', {}))
            
            # Display unified test results if available
            if 'unified_test_results' in log_data:
                self._display_unified_results(log_data['unified_test_results'], show_details)
            else:
                self.console.print("[yellow]No unified test results found in log file[/yellow]")
            
            # Display auto-fix attempts if available
            if 'auto_fix_attempts' in log_data:
                self._display_auto_fix_attempts(log_data['auto_fix_attempts'])
            
        except FileNotFoundError:
            self.console.print(f"[bold red]Error: Log file not found: {log_file_path}[/bold red]")
        except json.JSONDecodeError as e:
            self.console.print(f"[bold red]Error: Invalid JSON in log file: {e}[/bold red]")
        except Exception as e:
            self.console.print(f"[bold red]Error analyzing log file: {e}[/bold red]")
    
    def _display_metadata(self, metadata: Dict[str, Any]) -> None:
        """Display test metadata.
        
        Args:
            metadata: Test metadata dictionary
        """
        self.console.print("\n[bold]Test Metadata:[/bold]")
        
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="bold")
        table.add_column("Value")
        
        table.add_row("Test Name", metadata.get('test_name', 'Unknown'))
        table.add_row("File Path", metadata.get('file_path', 'Unknown'))
        table.add_row("Config Path", metadata.get('config_path', 'Unknown'))
        table.add_row("Status", metadata.get('status', 'Unknown'))
        table.add_row("Start Time", metadata.get('start_time', 'Unknown'))
        table.add_row("End Time", metadata.get('end_time', 'Unknown'))
        
        # Display config options
        config = metadata.get('config', {})
        if config:
            table.add_row("Auto Fix", str(config.get('auto_fix', False)))
            table.add_row("Create PR", str(config.get('create_pr', False)))
            table.add_row("Max Retries", str(config.get('max_retries', 0)))
            table.add_row("Base Branch", config.get('base_branch', 'main'))
            table.add_row("PR Strategy", config.get('pr_strategy', 'ANY_IMPROVEMENT'))
        
        self.console.print(table)
    
    def _display_unified_results(self, unified_data: Dict[str, Any], show_details: bool) -> None:
        """Display unified test results.
        
        Args:
            unified_data: Unified test results data
            show_details: Whether to show detailed test case information
        """
        self.console.print("\n[bold]Test Results Summary:[/bold]")
        
        # Display overall summary
        summary = unified_data.get('test_summary', {})
        if summary:
            table = Table(show_header=False, box=None)
            table.add_column("Metric", style="bold")
            table.add_column("Value")
            
            table.add_row("Total Test Cases", str(summary.get('total_test_cases', 0)))
            table.add_row("Passed", f"[green]{summary.get('passed_test_cases', 0)}[/green]")
            table.add_row("Failed", f"[red]{summary.get('failed_test_cases', 0)}[/red]")
            table.add_row("Error", f"[red]{summary.get('error_test_cases', 0)}[/red]")
            table.add_row("With Evaluations", str(summary.get('test_cases_with_evaluations', 0)))
            table.add_row("With Errors", str(summary.get('test_cases_with_errors', 0)))
            
            self.console.print(table)
            
            # Display regions
            regions = summary.get('regions', [])
            if regions:
                self.console.print(f"\n[bold]Test Regions:[/bold] {', '.join(regions)}")
        
        # Display test cases
        test_cases = unified_data.get('test_cases_detailed', [])
        if test_cases:
            self.console.print(f"\n[bold]Test Cases ({len(test_cases)}):[/bold]")
            
            if show_details:
                self._display_detailed_test_cases(test_cases)
            else:
                self._display_test_cases_summary(test_cases)
        else:
            self.console.print("[yellow]No detailed test cases found[/yellow]")
    
    def _display_test_cases_summary(self, test_cases: List[Dict[str, Any]]) -> None:
        """Display a summary table of test cases.
        
        Args:
            test_cases: List of test case dictionaries
        """
        table = Table(title="Test Cases Summary")
        table.add_column("Name", style="bold")
        table.add_column("Region")
        table.add_column("Status")
        table.add_column("Input Type")
        table.add_column("Output Type")
        table.add_column("Evaluation Score")
        table.add_column("Error")
        
        for tc in test_cases:
            status = tc.get('status', 'unknown')
            status_style = "green" if status == 'passed' else "red"
            
            input_type = tc.get('summary', {}).get('input_type', 'N/A')
            output_type = tc.get('summary', {}).get('output_type', 'N/A')
            eval_score = tc.get('evaluation_score', 'N/A')
            error = tc.get('error_message', '')[:30] + "..." if tc.get('error_message') else ''
            
            table.add_row(
                tc.get('name', 'Unknown'),
                tc.get('region', 'Unknown'),
                f"[{status_style}]{status}[/{status_style}]",
                input_type,
                output_type,
                str(eval_score),
                error
            )
        
        self.console.print(table)
    
    def _display_detailed_test_cases(self, test_cases: List[Dict[str, Any]]) -> None:
        """Display detailed information for each test case.
        
        Args:
            test_cases: List of test case dictionaries
        """
        for i, tc in enumerate(test_cases, 1):
            status = tc.get('status', 'unknown')
            status_color = "green" if status == 'passed' else "red"
            
            # Create panel for each test case
            title = f"Test Case {i}: {tc.get('name', 'Unknown')} [{status_color}]{status}[/{status_color}]"
            
            content = []
            content.append(f"[bold]Region:[/bold] {tc.get('region', 'Unknown')}")
            
            # Input
            input_data = tc.get('input')
            if input_data is not None:
                content.append(f"\n[bold]Input:[/bold]")
                content.append(self._format_data(input_data))
            
            # Expected Output
            expected_output = tc.get('expected_output')
            if expected_output is not None:
                content.append(f"\n[bold]Expected Output:[/bold]")
                content.append(self._format_data(expected_output))
            
            # Actual Output
            actual_output = tc.get('actual_output')
            if actual_output is not None:
                content.append(f"\n[bold]Actual Output:[/bold]")
                content.append(self._format_data(actual_output))
            
            # Evaluation
            evaluation = tc.get('evaluation')
            if evaluation is not None:
                content.append(f"\n[bold]Evaluation:[/bold]")
                content.append(self._format_data(evaluation))
            
            # Error
            error_message = tc.get('error_message')
            if error_message:
                content.append(f"\n[bold red]Error:[/bold red] {error_message}")
            
            error_details = tc.get('error_details')
            if error_details:
                content.append(f"\n[bold red]Error Details:[/bold red] {error_details}")
            
            # Metadata
            metadata = tc.get('metadata', {})
            if metadata:
                content.append(f"\n[bold]Metadata:[/bold]")
                content.append(self._format_data(metadata))
            
            panel = Panel(
                "\n".join(content),
                title=title,
                border_style=status_color
            )
            self.console.print(panel)
    
    def _format_data(self, data: Any) -> str:
        """Format data for display.
        
        Args:
            data: Data to format
            
        Returns:
            Formatted string representation
        """
        if isinstance(data, str):
            # Try to format as code if it looks like code
            if any(keyword in data.lower() for keyword in ['def ', 'class ', 'import ', 'from ', 'return ', 'if ', 'for ', 'while ']):
                return f"```python\n{data}\n```"
            else:
                return f'"{data}"'
        elif isinstance(data, (dict, list)):
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return str(data)
    
    def _display_auto_fix_attempts(self, attempts: List[Dict[str, Any]]) -> None:
        """Display auto-fix attempts.
        
        Args:
            attempts: List of auto-fix attempt dictionaries
        """
        self.console.print(f"\n[bold]Auto-Fix Attempts ({len(attempts)}):[/bold]")
        
        for i, attempt in enumerate(attempts, 1):
            status = attempt.get('status', 'unknown')
            status_color = "green" if status == 'passed' else "red"
            
            self.console.print(f"\n[bold]Attempt {i}:[/bold] [{status_color}]{status}[/{status_color}]")
            
            test_cases = attempt.get('test_cases', [])
            if test_cases:
                table = Table(show_header=True)
                table.add_column("Name")
                table.add_column("Status")
                table.add_column("Input")
                table.add_column("Expected")
                table.add_column("Actual")
                table.add_column("Error")
                
                for tc in test_cases:
                    tc_status = tc.get('status', 'unknown')
                    tc_status_style = "green" if tc_status == 'passed' else "red"
                    
                    table.add_row(
                        tc.get('name', 'Unknown'),
                        f"[{tc_status_style}]{tc_status}[/{tc_status_style}]",
                        str(tc.get('input', ''))[:30] + "..." if len(str(tc.get('input', ''))) > 30 else str(tc.get('input', '')),
                        str(tc.get('expected_output', ''))[:30] + "..." if len(str(tc.get('expected_output', ''))) > 30 else str(tc.get('expected_output', '')),
                        str(tc.get('actual_output', ''))[:30] + "..." if len(str(tc.get('actual_output', ''))) > 30 else str(tc.get('actual_output', '')),
                        tc.get('reason', '')[:30] + "..." if tc.get('reason') and len(tc.get('reason', '')) > 30 else tc.get('reason', '')
                    )
                
                self.console.print(table)

def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python log_analyzer.py <log_file_path> [--details]")
        print("\nOptions:")
        print("  --details    Show detailed test case information")
        print("\nExample:")
        print("  python log_analyzer.py test-logs/my_test_20241201_120000_detailed_logs.json --details")
        sys.exit(1)
    
    log_file_path = Path(sys.argv[1])
    show_details = "--details" in sys.argv
    
    analyzer = TestLogAnalyzer()
    analyzer.analyze_log_file(log_file_path, show_details)

if __name__ == "__main__":
    main() 