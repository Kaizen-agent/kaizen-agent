"""Metadata model for test configuration.

This module contains the TestMetadata class used for storing metadata
about test configurations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class TestMetadata:
    """Test configuration metadata.
    
    Attributes:
        version: Version number
        dependencies: Required dependencies
        environment_variables: Required environment variables
        author: Author name
        created_at: Creation timestamp
        updated_at: Last update timestamp
        description: Test description
    """
    version: str
    dependencies: List[str] = field(default_factory=list)
    environment_variables: List[str] = field(default_factory=list)
    author: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestMetadata':
        """Create TestMetadata from dictionary.
        
        Args:
            data: Dictionary containing metadata
            
        Returns:
            TestMetadata instance
        """
        return cls(
            version=data.get('version'),
            dependencies=data.get('dependencies', []),
            environment_variables=data.get('environment_variables', []),
            author=data.get('author'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            description=data.get('description')
        ) 