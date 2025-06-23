"""CLI command for analyzing test logs.

This module provides a CLI command to analyze and display test logs saved by the test command.
It helps users quickly scan through test results and understand what outputs were generated.
"""

import click
from pathlib import Path
from typing import Optional

from rich.console import Console
from .utils.log_analyzer import TestLogAnalyzer

@click.command()
@click.argument('log_file', type=click.Path(exists=True, path_type=Path))
@click.option('--details', '-d', is_flag=True, help='Show detailed test case information including inputs, outputs, and evaluations')
@click.option('--summary-only', '-s', is_flag=True, help='Show only summary information (no test case details)')
def analyze_logs(log_file: Path, details: bool, summary_only: bool) -> None:
    """Analyze test logs saved by the test command.
    
    This command helps you quickly scan through test results and understand what outputs
    were generated for each test case. It displays inputs, outputs, evaluations, and
    error messages in a readable format.
    
    Args:
        log_file: Path to the test log file to analyze
        details: Whether to show detailed test case information
        summary_only: Whether to show only summary information
        
    Examples:
        # Analyze a log file with summary only
        kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json
        
        # Analyze with detailed test case information
        kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json --details
        
        # Show only summary
        kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json --summary-only
    """
    console = Console()
    
    try:
        # Validate log file
        if not log_file.exists():
            console.print(f"[bold red]Error: Log file not found: {log_file}[/bold red]")
            return
        
        if not log_file.suffix == '.json':
            console.print(f"[bold red]Error: Log file must be a JSON file: {log_file}[/bold red]")
            return
        
        # Analyze the log file
        analyzer = TestLogAnalyzer(console)
        
        # Determine what level of detail to show
        show_details = details and not summary_only
        
        analyzer.analyze_log_file(log_file, show_details)
        
        # Provide helpful information about the log file
        console.print(f"\n[bold]Log File Information:[/bold]")
        console.print(f"[dim]File: {log_file}[/dim]")
        console.print(f"[dim]Size: {log_file.stat().st_size / 1024:.1f} KB[/dim]")
        console.print(f"[dim]Modified: {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        
        # Show usage tips
        console.print(f"\n[bold]Usage Tips:[/bold]")
        console.print(f"[dim]• Use --details to see full inputs, outputs, and evaluations[/dim]")
        console.print(f"[dim]• Use --summary-only for quick overview[/dim]")
        console.print(f"[dim]• Check the summary file for failed test cases overview[/dim]")
        console.print(f"[dim]• Open the JSON file directly for complete data[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error analyzing log file: {e}[/bold red]")
        raise click.Abort()

# Add missing import
from datetime import datetime 