"""Error types for test commands.

This module defines custom exceptions used throughout the test command system.
Each error type is designed to handle specific failure cases and provide
meaningful error messages.
"""

from typing import Optional, Any

class TestError(Exception):
    """Base class for all test-related errors.
    
    This class serves as the foundation for all test-related exceptions,
    providing a common interface for error handling.
    
    Attributes:
        message: A descriptive error message
        details: Optional additional error details
    """
    
    def __init__(self, message: str, details: Optional[Any] = None):
        """Initialize a new TestError.
        
        Args:
            message: A descriptive error message
            details: Optional additional error details
        """
        self.message = message
        self.details = details
        super().__init__(self.message)

class ConfigurationError(TestError):
    """Error raised when there is a problem with test configuration.
    
    This error is raised when:
    - Configuration file is invalid or missing
    - Required configuration parameters are missing
    - Configuration values are invalid
    
    Example:
        >>> raise ConfigurationError("Missing required field 'name' in config")
    """
    pass

class TestExecutionError(TestError):
    """Error raised when test execution fails.
    
    This error is raised when:
    - Test runner fails to execute tests
    - Test execution times out
    - Test environment is not properly set up
    
    Example:
        >>> raise TestExecutionError("Failed to execute test suite", {"test_id": "test_001"})
    """
    pass

class ReportGenerationError(TestError):
    """Error raised when report generation fails.
    
    This error is raised when:
    - Report writer fails to create report
    - Report formatting fails
    - Report file cannot be written
    
    Example:
        >>> raise ReportGenerationError("Failed to write report to file", {"file_path": "report.txt"})
    """
    pass

class ValidationError(TestError):
    """Error raised when validation fails.
    
    This error is raised when:
    - Test results fail validation
    - Test configuration fails validation
    - Test environment fails validation
    
    Example:
        >>> raise ValidationError("Test results validation failed", {"failed_checks": ["check1", "check2"]})
    """
    pass

class AutoFixError(TestError):
    """Error raised when auto-fix process fails.
    
    This error is raised when:
    - Auto-fix process fails to fix tests
    - Fix attempts exceed maximum retries
    - Fix process encounters unexpected errors
    
    Example:
        >>> raise AutoFixError("Auto-fix failed after 3 attempts", {"attempts": 3, "failed_tests": ["test1", "test2"]})
    """
    pass 