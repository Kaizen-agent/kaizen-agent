"""Result type for handling operation outcomes.

This module provides a generic Result type for handling operations that can fail.
It follows the Result pattern, providing a type-safe way to handle both successful
and failed operations.
"""

from typing import TypeVar, Generic, Optional, Any, Union, Callable
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Result(Generic[T]):
    """Generic result type for operations that can fail.
    
    This class provides a type-safe way to handle operations that can either
    succeed or fail. It follows the Result pattern, similar to Rust's Result type.
    
    Attributes:
        value: The successful result value, if any
        error: The error that occurred, if any
    
    Example:
        >>> def divide(a: int, b: int) -> Result[float]:
        ...     if b == 0:
        ...         return Result.failure(ValueError("Division by zero"))
        ...     return Result.success(a / b)
        ...
        >>> result = divide(10, 2)
        >>> if result.is_success:
        ...     print(f"Result: {result.value}")
        ... else:
        ...     print(f"Error: {result.error}")
    """
    
    value: Optional[T] = None
    error: Optional[Exception] = None
    
    @property
    def is_success(self) -> bool:
        """Check if the operation was successful.
        
        Returns:
            True if the operation succeeded, False otherwise
        """
        return self.error is None
    
    @property
    def is_failure(self) -> bool:
        """Check if the operation failed.
        
        Returns:
            True if the operation failed, False otherwise
        """
        return not self.is_success
    
    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        """Create a successful result.
        
        Args:
            value: The successful result value
            
        Returns:
            A Result instance representing success
        """
        return cls(value=value)
    
    @classmethod
    def failure(cls, error: Exception) -> 'Result[T]':
        """Create a failed result.
        
        Args:
            error: The error that occurred
            
        Returns:
            A Result instance representing failure
        """
        return cls(error=error)
    
    def map(self, func: Callable[[T], Any]) -> 'Result[Any]':
        """Apply a function to the value if the result is successful.
        
        Args:
            func: Function to apply to the value
            
        Returns:
            A new Result with the transformed value, or the original error
        """
        if self.is_success and self.value is not None:
            try:
                return Result.success(func(self.value))
            except Exception as e:
                return Result.failure(e)
        return Result.failure(self.error) if self.error else Result.failure(ValueError("No value or error"))
    
    def flat_map(self, func: Callable[[T], 'Result[Any]']) -> 'Result[Any]':
        """Apply a function that returns a Result to the value if the result is successful.
        
        Args:
            func: Function that returns a Result to apply to the value
            
        Returns:
            The Result from the function, or the original error
        """
        if self.is_success and self.value is not None:
            try:
                return func(self.value)
            except Exception as e:
                return Result.failure(e)
        return Result.failure(self.error) if self.error else Result.failure(ValueError("No value or error"))
    
    def get_or_else(self, default: T) -> T:
        """Get the value if successful, or return a default value.
        
        Args:
            default: Default value to return if the result is a failure
            
        Returns:
            The successful value or the default value
        """
        return self.value if self.is_success and self.value is not None else default 