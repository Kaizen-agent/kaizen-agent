"""Sample input types for testing multiple input functionality.

This module provides example classes that can be used as object inputs
in the new multiple input format.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class ChemistFeedback:
    """Sample class representing chemist feedback.
    
    This class demonstrates how object inputs can be used to pass
    structured feedback data to agents.
    """
    text: str
    tags: List[str]
    confidence: Optional[float] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Validate the feedback data."""
        if not self.text.strip():
            raise ValueError("Feedback text cannot be empty")
        if not self.tags:
            raise ValueError("At least one tag must be provided")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'text': self.text,
            'tags': self.tags,
            'confidence': self.confidence,
            'source': self.source
        }

@dataclass
class ExperimentContext:
    """Sample class representing experimental context.
    
    This class demonstrates how object inputs can be used to pass
    experimental parameters and conditions.
    """
    temperature: float
    pressure: Optional[float] = None
    solvent: Optional[str] = None
    catalyst: Optional[str] = None
    duration: Optional[float] = None
    
    def __post_init__(self):
        """Validate the experimental parameters."""
        if self.temperature < -273.15:  # Absolute zero
            raise ValueError("Temperature cannot be below absolute zero")
        if self.pressure is not None and self.pressure < 0:
            raise ValueError("Pressure cannot be negative")
        if self.duration is not None and self.duration < 0:
            raise ValueError("Duration cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'temperature': self.temperature,
            'pressure': self.pressure,
            'solvent': self.solvent,
            'catalyst': self.catalyst,
            'duration': self.duration
        }

@dataclass
class CompoundData:
    """Sample class representing compound data.
    
    This class demonstrates how object inputs can be used to pass
    molecular and chemical information.
    """
    name: str
    molecular_weight: float
    molecular_formula: Optional[str] = None
    cas_number: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate the compound data."""
        if not self.name.strip():
            raise ValueError("Compound name cannot be empty")
        if self.molecular_weight <= 0:
            raise ValueError("Molecular weight must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'molecular_weight': self.molecular_weight,
            'molecular_formula': self.molecular_formula,
            'cas_number': self.cas_number,
            'properties': self.properties or {}
        }

@dataclass
class UserQuery:
    """Sample class representing a user query.
    
    This class demonstrates how object inputs can be used to pass
    structured user queries with metadata.
    """
    text: str
    intent: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    priority: Optional[str] = "normal"
    
    def __post_init__(self):
        """Validate the query data."""
        if not self.text.strip():
            raise ValueError("Query text cannot be empty")
        if self.priority not in ["low", "normal", "high", "urgent"]:
            raise ValueError("Priority must be one of: low, normal, high, urgent")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'text': self.text,
            'intent': self.intent,
            'context': self.context or {},
            'priority': self.priority
        } 