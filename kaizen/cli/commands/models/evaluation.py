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
        llm_provider: LLM provider to use
        model: Model to use for evaluation
        settings: Test settings
    """
    criteria: List[Dict[str, Any]]
    llm_provider: Optional[str] = None
    model: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestEvaluation':
        """Create TestEvaluation from dictionary.
        
        Args:
            data: Dictionary containing evaluation criteria
            
        Returns:
            TestEvaluation instance
        """
        return cls(
            criteria=data.get('criteria', []),
            llm_provider=data.get('llm_provider'),
            model=data.get('model'),
            settings=data.get('settings', {})
        ) 