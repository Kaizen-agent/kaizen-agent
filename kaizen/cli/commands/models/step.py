"""Test step model for configuration.

This module defines the TestStep model used to represent individual test steps
in the test configuration.
"""

from dataclasses import dataclass
from typing import Optional, Dict

@dataclass(frozen=True)
class TestStep:
    """A single test step in the configuration.
    
    Attributes:
        name: Step identifier
        command: Command to execute
        expected_output: Expected result
        description: Step description
        timeout: Timeout in seconds
        retries: Number of retry attempts
        environment: Step-specific environment variables
        dependencies: Required step dependencies
    """
    name: str
    command: str
    expected_output: str
    description: Optional[str] = None
    timeout: Optional[int] = None
    retries: Optional[int] = None
    environment: Optional[Dict[str, str]] = None
    dependencies: Optional[list[str]] = None 