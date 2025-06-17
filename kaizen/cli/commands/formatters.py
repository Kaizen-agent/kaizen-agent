"""Test result formatters for Kaizen CLI."""

from typing import Dict, Any, List, Union
from rich.console import Console
from rich.table import Table
from .types import TestResultFormatter, STATUS_EMOJI

class MarkdownTestResultFormatter(TestResultFormatter):
    """Formats test results in Markdown format.
    
    This formatter is used for writing test results to files in a human-readable
    Markdown format. It provides methods for formatting both individual status
    indicators and complete result tables.
    """
    
    def format_status(self, status: str) -> str:
        """Format test status with emoji.
        
        Args:
            status: The status string to format (e.g., 'passed', 'failed')
            
        Returns:
            A formatted status string with emoji
        """
        return f"{STATUS_EMOJI.get(status, STATUS_EMOJI['unknown'])} {status.upper()}"
    
    def format_table(self, results: Dict[str, Any]) -> List[str]:
        """Format test results as a markdown table.
        
        Args:
            results: Dictionary containing test results
            
        Returns:
            List of strings representing the markdown table
        """
        lines = []
        
        # Add header
        lines.append("| Region | Status | Details |")
        lines.append("|--------|--------|---------|")
        
        # Add rows
        for region, result in results.items():
            if region in ('overall_status', '_status'):
                continue
                
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                test_cases = result.get('test_cases', [])
                details = []
                
                for test_case in test_cases:
                    if isinstance(test_case, dict):
                        test_name = test_case.get('name', 'Unknown')
                        test_status = test_case.get('status', 'unknown')
                        details.append(f"{test_name}: {test_status}")
                
                lines.append(f"| {region} | {self.format_status(status)} | {', '.join(details)} |")
        
        return lines

class RichTestResultFormatter(TestResultFormatter):
    """Formats test results using Rich library.
    
    This formatter is used for displaying test results in the console using
    Rich's table formatting capabilities. It provides methods for formatting
    both individual status indicators and complete result tables.
    """
    
    def __init__(self, console: Console):
        """Initialize the formatter with a Rich console.
        
        Args:
            console: Rich console instance for output
        """
        self.console = console
    
    def format_status(self, status: str) -> str:
        """Format test status with emoji.
        
        Args:
            status: The status string to format (e.g., 'passed', 'failed')
            
        Returns:
            A formatted status string with emoji
        """
        return f"{STATUS_EMOJI.get(status, STATUS_EMOJI['unknown'])} {status.upper()}"
    
    def format_table(self, results: Dict[str, Any]) -> Table:
        """Format test results as a Rich table.
        
        Args:
            results: Dictionary containing test results
            
        Returns:
            A Rich Table object containing the formatted results
        """
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Region", style="dim")
        table.add_column("Status")
        table.add_column("Details")
        
        for region, result in results.items():
            if region in ('overall_status', '_status'):
                continue
                
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                test_cases = result.get('test_cases', [])
                details = []
                
                for test_case in test_cases:
                    if isinstance(test_case, dict):
                        test_name = test_case.get('name', 'Unknown')
                        test_status = test_case.get('status', 'unknown')
                        details.append(f"{test_name}: {test_status}")
                
                table.add_row(
                    region,
                    self.format_status(status),
                    "\n".join(details)
                )
        
        return table 