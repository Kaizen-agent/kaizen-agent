"""Test step model for configuration.

This module defines the TestStep model used to represent individual test steps
in the test configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class TestStep:
    """A single test step configuration.
    
    Attributes:
        name: Step name
        command: Command to execute
        input: Input configuration for the agent
        expected_output: Expected output configuration
        description: Step description
        timeout: Step timeout in seconds
        retries: Number of retry attempts
        environment: Environment variables
        dependencies: List of dependencies
        assertions: List of assertions to run
    """
    name: str
    command: str
    input: str
    expected_output: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    timeout: Optional[int] = None
    retries: Optional[int] = None
    environment: Optional[Dict[str, str]] = None
    dependencies: Optional[List[str]] = None
    assertions: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestStep':
        """Create a TestStep instance from a dictionary.
        
        Args:
            data: Dictionary containing step configuration
            
        Returns:
            TestStep instance
        """
        return cls(
            name=data.get('name', ''),
            command=data.get('input', {}).get('method', ''),
            input=data.get('input', {}).get('input', {}),
            expected_output=data.get('expected_output'),
            description=data.get('description'),
            timeout=data.get('timeout'),
            retries=data.get('retries'),
            environment=data.get('environment'),
            dependencies=data.get('dependencies'),
            assertions=data.get('assertions')
        ) 