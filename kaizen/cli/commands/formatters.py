"""Test result formatters for Kaizen CLI.

This module provides formatters for converting test results into different output formats.
It includes both Markdown and Rich console formatters, each implementing a common
interface defined by the TestResultFormatter protocol.

The formatters handle:
- Status formatting with emojis
- Table generation for test results
- Consistent output formatting across different mediums
"""

# Standard library imports
from typing import Any, Dict, List, Protocol, Union

# Third-party imports
from rich.console import Console
from rich.table import Table

# Local application imports
from kaizen.cli.commands.types import STATUS_EMOJI

class TestResultFormatter(Protocol):
    """Protocol for test result formatters.
    
    This protocol defines the interface that all test result formatters must implement.
    Formatters are responsible for converting test results into different output formats.
    
    Attributes:
        None - This is a protocol class defining an interface
    """
    
    def format_status(self, status: str) -> str:
        """Format test status with emoji.
        
        Args:
            status: The status string to format (e.g., 'passed', 'failed')
            
        Returns:
            A formatted status string with emoji
            
        Example:
            >>> formatter = MarkdownTestResultFormatter()
            >>> formatter.format_status('passed')
            '✅ PASSED'
        """
        ...
    
    def format_table(self, results: Dict[str, Any]) -> Union[List[str], Table]:
        """Format test results as a table.
        
        Args:
            results: Dictionary containing test results with the following structure:
                {
                    'region_name': {
                        'status': str,
                        'test_cases': List[Dict[str, Any]]
                    }
                }
            
        Returns:
            Either a list of strings (for markdown) or a Rich Table object
            
        Example:
            >>> formatter = MarkdownTestResultFormatter()
            >>> results = {'test1': {'status': 'passed', 'test_cases': []}}
            >>> formatter.format_table(results)
            ['| Region | Status | Details |', '|--------|--------|---------|', '| test1 | ✅ PASSED |  |']
        """
        ...

class MarkdownTestResultFormatter(TestResultFormatter):
    """Formats test results in Markdown format.
    
    This formatter is used for writing test results to files in a human-readable
    Markdown format. It provides methods for formatting both individual status
    indicators and complete result tables.
    
    The formatter generates markdown tables with the following columns:
    - Region: The name of the test region
    - Status: The test status with emoji
    - Details: Additional test case information
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
    
    The formatter creates Rich tables with the following columns:
    - Region: The name of the test region (dimmed style)
    - Status: The test status with emoji
    - Details: Additional test case information
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