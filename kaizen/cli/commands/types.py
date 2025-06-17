"""Enums and constants for test commands.

This module defines enums and constants used throughout the test command system.
These values are used for configuration and control flow in the test execution process.
"""

from enum import Enum
from typing import List

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
        """
        try:
            return cls(value.upper())
        except ValueError:
            valid_values = [s.value for s in cls]
            raise ValueError(
                f"Invalid PR strategy: {value}. "
                f"Must be one of {valid_values}"
            )

# Default values for test configuration
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BASE_BRANCH: str = 'main' 