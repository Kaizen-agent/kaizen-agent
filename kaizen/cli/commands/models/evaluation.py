"""Evaluation model for test configuration.

This module contains the TestEvaluation class used for storing evaluation
criteria and settings for tests.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class TestEvaluation:
    """Evaluation criteria for test.
    
    Attributes:
        criteria: List of evaluation criteria
        threshold: Minimum passing score
        timeout: Maximum execution time
    """
    criteria: Optional[List[str]] = None
    threshold: Optional[float] = None
    timeout: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestEvaluation':
        """Create TestEvaluation from dictionary.
        
        Args:
            data: Dictionary containing evaluation criteria
            
        Returns:
            TestEvaluation instance
        """
        return cls(
            criteria=data.get('criteria'),
            threshold=data.get('threshold'),
            timeout=data.get('timeout')
        ) 