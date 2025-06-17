"""Shared types and constants for Kaizen CLI test commands."""

from typing import Dict, Any, List, Union, Protocol, runtime_checkable
from rich.table import Table

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