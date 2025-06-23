"""Test result model."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TypeVar, Generic, Any

from .configuration import TestConfiguration

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

@dataclass(frozen=True)
class TestResult:
    """Test execution result.
    
    Attributes:
        name: Test name
        file_path: Test file location
        config_path: Config file location
        start_time: Test start time
        end_time: Test end time
        status: Overall test status
        results: Detailed test results
        error: Error message if failed
        steps: Test step results
        unified_result: Unified test execution result (for detailed logging)
        test_attempts: Auto-fix attempts (for detailed logging)
    """
    # Required fields
    name: str
    file_path: Path
    config_path: Path
    start_time: datetime
    end_time: datetime
    status: str
    results: Dict[str, any]
    
    # Optional fields
    error: Optional[str] = None
    steps: List[Dict[str, any]] = field(default_factory=list)
    unified_result: Optional[Any] = None  # TestExecutionResult
    test_attempts: Optional[List[Dict[str, any]]] = None
    
    @classmethod
    def from_config(cls, config: TestConfiguration) -> 'TestResult':
        """Create a test result from configuration.
        
        Args:
            config: Test configuration
            
        Returns:
            New test result instance
        """
        now = datetime.now()
        return cls(
            name=config.name,
            file_path=config.file_path,
            config_path=config.config_path,
            start_time=now,
            end_time=now,
            status='pending',
            results={}
        ) 