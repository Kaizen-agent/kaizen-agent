"""Shared types and constants for Kaizen CLI test commands."""

from typing import Dict, Any, List, Union, Protocol, runtime_checkable
from rich.table import Table
from enum import Enum, auto

# Constants
STATUS_EMOJI = {
    'passed': '✅',
    'failed': '❌',
    'completed': '✓',
    'unknown': '?'
}

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

"""Common types and errors for CLI commands."""

class TestError(Exception):
    """Base exception for test-related errors."""
    pass

class ConfigurationError(TestError):
    """Exception for configuration-related errors."""
    pass

class TestExecutionError(TestError):
    """Exception for test execution errors."""
    pass

class ReportGenerationError(TestError):
    """Exception for report generation errors."""
    pass

class ValidationError(TestError):
    """Exception for validation errors."""
    pass

# Constants
DEFAULT_MAX_RETRIES = 1
DEFAULT_BASE_BRANCH = 'main'

class PRStrategy(Enum):
    """Strategy for when to create pull requests."""
    ALL_PASSING = "ALL_PASSING"
    ANY_IMPROVEMENT = "ANY_IMPROVEMENT"
    NONE = "NONE"

    @classmethod
    def from_str(cls, value: str) -> 'PRStrategy':
        """Convert string to PRStrategy enum.
        
        Args:
            value: String value to convert
            
        Returns:
            PRStrategy enum value
            
        Raises:
            ValueError: If value is not a valid PR strategy
        """
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid PR strategy: {value}. Must be one of {[s.value for s in cls]}") 