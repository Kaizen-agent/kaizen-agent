"""Settings model for test configuration.

This module contains the TestSettings class used for storing test
execution settings.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TestSettings:
    """Settings for test execution.
    
    Attributes:
        timeout: Maximum execution time
        retry_count: Number of retry attempts
        parallel: Whether to run tests in parallel
    """
    timeout: Optional[int] = None
    retry_count: Optional[int] = None
    parallel: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestSettings':
        """Create TestSettings from dictionary.
        
        Args:
            data: Dictionary containing settings
            
        Returns:
            TestSettings instance
        """
        return cls(
            timeout=data.get('timeout'),
            retry_count=data.get('retry_count'),
            parallel=data.get('parallel', False)
        ) 