"""Operation result model."""

from dataclasses import dataclass
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

@dataclass(frozen=True)
class Result(Generic[T]):
    """Operation result with success/failure status.
    
    Attributes:
        is_success: Whether operation succeeded
        value: Result value if successful
        error: Error message if failed
    """
    is_success: bool
    value: Optional[T] = None
    error: Optional[str] = None
    
    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        """Create a successful result.
        
        Args:
            value: Result value
            
        Returns:
            New success result
        """
        return cls(is_success=True, value=value)
    
    @classmethod
    def failure(cls, error: str) -> 'Result[T]':
        """Create a failed result.
        
        Args:
            error: Error message
            
        Returns:
            New failure result
        """
        return cls(is_success=False, error=error) 