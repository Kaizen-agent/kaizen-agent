"""Enums and constants for test commands.

This module defines enums and constants used throughout the test command system.
These values are used for configuration and control flow in the test execution process.

The module provides:
- PRStrategy: Enum for pull request creation strategies
- TestStatus: Enum for test execution statuses
- STATUS_EMOJI: Mapping of status values to emoji representations
- Default configuration values

Example:
    >>> from kaizen.cli.commands.types import PRStrategy, TestStatus
    >>> strategy = PRStrategy.ALL_PASSING
    >>> status = TestStatus.PASSED
    >>> print(f"Strategy: {strategy.value}, Status: {status.value}")
    Strategy: ALL_PASSING, Status: passed
"""

from enum import Enum
from typing import Dict, List, Final

class PRStrategy(str, Enum):
    """Strategy for when to create pull requests.
    
    This enum defines the different strategies for when to create pull requests
    during the auto-fix process.
    
    Attributes:
        ALL_PASSING: Only create PR if all tests pass
        ANY_IMPROVEMENT: Create PR if any tests improve
        NONE: Never create PR
    
    Example:
        >>> strategy = PRStrategy.from_str("ALL_PASSING")
        >>> print(strategy.value)  # "ALL_PASSING"
    """
    
    ALL_PASSING = 'ALL_PASSING'  # Only create PR if all tests pass
    ANY_IMPROVEMENT = 'ANY_IMPROVEMENT'  # Create PR if any tests improve
    NONE = 'NONE'  # Never create PR

    @classmethod
    def from_str(cls, value: str) -> 'PRStrategy':
        """Convert string to PRStrategy enum.
        
        Args:
            value: String value to convert (case-insensitive)
            
        Returns:
            PRStrategy enum value
            
        Raises:
            ValueError: If value is not a valid PR strategy
            
        Example:
            >>> strategy = PRStrategy.from_str("all_passing")
            >>> print(strategy)  # PRStrategy.ALL_PASSING
        """
        try:
            return cls(value.upper())
        except ValueError:
            valid_values = [s.value for s in cls]
            raise ValueError(
                f"Invalid PR strategy: {value}. "
                f"Must be one of {valid_values}"
            )

class TestStatus(str, Enum):
    """Enum for test status values.
    
    This enum defines the possible status values for test results.
    
    Attributes:
        PENDING: Test is waiting to be executed
        RUNNING: Test is currently running
        PASSED: Test has passed successfully
        FAILED: Test has failed
        ERROR: Test encountered an error
        COMPLETED: Test execution is complete
        UNKNOWN: Test status is unknown
        
    Example:
        >>> status = TestStatus.PASSED
        >>> print(f"Test status: {status.value}")  # Test status: passed
    """
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    ERROR = 'error'
    COMPLETED = 'completed'
    UNKNOWN = 'unknown'

# Emoji mapping for test statuses
STATUS_EMOJI: Final[Dict[str, str]] = {
    TestStatus.PENDING.value: '⏳',
    TestStatus.RUNNING.value: '🔄',
    TestStatus.PASSED.value: '✅',
    TestStatus.FAILED.value: '❌',
    TestStatus.ERROR.value: '⚠️',
    TestStatus.COMPLETED.value: '🏁',
    TestStatus.UNKNOWN.value: '❓'
}

# Default values for test configuration
DEFAULT_MAX_RETRIES: Final[int] = 2
DEFAULT_BASE_BRANCH: Final[str] = 'main' 