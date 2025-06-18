"""Test step model for configuration.

This module defines the TestStep model used to represent individual test steps
in the test configuration.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestStep':
        """Create a TestStep instance from a dictionary.
        
        Args:
            data: Dictionary containing step data
            
        Returns:
            TestStep instance
        """
        return cls(
            name=data.get('name', ''),
            command=data.get('input', {}).get('method', ''),
            expected_output=data.get('expected_output', ''),
            description=data.get('description'),
            timeout=data.get('timeout'),
            retries=data.get('retries'),
            environment=data.get('environment'),
            dependencies=data.get('dependencies')
        ) 