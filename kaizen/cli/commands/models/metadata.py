"""Metadata model for test configuration.

This module contains the TestMetadata class used for storing metadata
about test configurations.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class TestMetadata:
    """Metadata for test configuration.
    
    Attributes:
        author: Author of the test
        created_at: Creation timestamp
        updated_at: Last update timestamp
        tags: List of tags
        version: Version number
    """
    author: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestMetadata':
        """Create TestMetadata from dictionary.
        
        Args:
            data: Dictionary containing metadata
            
        Returns:
            TestMetadata instance
        """
        return cls(
            author=data.get('author'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            tags=data.get('tags'),
            version=data.get('version')
        ) 