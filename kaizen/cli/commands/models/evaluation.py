"""Evaluation model for test configuration.

This module contains the TestEvaluation class used for storing evaluation
criteria and settings for tests.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

class EvaluationSource(Enum):
    """Source types for evaluation targets."""
    RETURN = "return"
    VARIABLE = "variable"
    PATTERN = "pattern"  # Future: for wildcard matching

@dataclass
class EvaluationTarget:
    """Individual evaluation target configuration.
    
    Attributes:
        name: Name of the target (variable name or "return")
        source: Source type (return, variable, or pattern)
        criteria: Evaluation criteria for this target
        description: Optional description of what this target should contain
        weight: Optional weight for this target in overall evaluation
    """
    name: str
    source: EvaluationSource
    criteria: str
    description: Optional[str] = None
    weight: Optional[float] = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of the evaluation target
        """
        return {
            'name': self.name,
            'source': self.source.value,
            'criteria': self.criteria,
            'description': self.description,
            'weight': self.weight
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationTarget':
        """Create EvaluationTarget from dictionary.
        
        Args:
            data: Dictionary containing target configuration
            
        Returns:
            EvaluationTarget instance
        """
        source_str = data.get('source', 'return')
        try:
            source = EvaluationSource(source_str)
        except ValueError:
            source = EvaluationSource.RETURN  # Default to return
            
        return cls(
            name=data['name'],
            source=source,
            criteria=data['criteria'],
            description=data.get('description'),
            weight=data.get('weight', 1.0)
        )

@dataclass
class TestEvaluation:
    """Evaluation criteria for test.
    
    Attributes:
        criteria: List of evaluation criteria (legacy format)
        evaluation_targets: List of evaluation targets (new format)
        llm_provider: LLM provider to use
        model: Model to use for evaluation
        settings: Test settings
    """
    criteria: List[Dict[str, Any]]
    evaluation_targets: List[EvaluationTarget]
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
        # Parse evaluation targets if present
        evaluation_targets = []
        if 'evaluation_targets' in data:
            for target_data in data['evaluation_targets']:
                evaluation_targets.append(EvaluationTarget.from_dict(target_data))
        
        # Handle legacy criteria format
        criteria = data.get('criteria', [])
        if isinstance(criteria, list):
            # Legacy format: list of criteria strings/dicts
            pass
        else:
            # Single criteria - convert to list
            criteria = [criteria] if criteria else []
        
        return cls(
            criteria=criteria,
            evaluation_targets=evaluation_targets,
            llm_provider=data.get('llm_provider'),
            model=data.get('model'),
            settings=data.get('settings', {})
        ) 