"""Data models for Kaizen CLI test commands."""

from typing import Dict, Any, Optional, List, TypeVar, Generic
from dataclasses import dataclass
from pathlib import Path
from .types import PRStrategy

T = TypeVar('T')

@dataclass
class TestMetadata:
    """Metadata for test configuration.
    
    Attributes:
        version: Version of the test configuration
        dependencies: List of dependencies required for the test
        environment_variables: List of environment variables needed
    """
    version: str
    dependencies: List[str]
    environment_variables: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestMetadata':
        """Create TestMetadata from dictionary.
        
        Args:
            data: Dictionary containing metadata information
            
        Returns:
            TestMetadata instance
        """
        return cls(
            version=data['version'],
            dependencies=data['dependencies'],
            environment_variables=data['environment_variables']
        )

@dataclass
class TestEvaluation:
    """Evaluation criteria for test results.
    
    Attributes:
        criteria: List of evaluation criteria
        thresholds: Dictionary of threshold values
        required_score: Minimum required score
    """
    criteria: List[str]
    thresholds: Dict[str, float]
    required_score: float

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
            thresholds=data.get('thresholds', {}),
            required_score=data.get('required_score', 0.0)
        )

@dataclass
class TestSettings:
    """Settings for test execution.
    
    Attributes:
        auto_fix: Whether to automatically fix failing tests
        create_pr: Whether to create a pull request with fixes
        max_retries: Maximum number of retry attempts
        base_branch: Base branch for pull request
        pr_strategy: Strategy for when to create PRs
    """
    auto_fix: bool = False
    create_pr: bool = False
    max_retries: int = 1
    base_branch: str = 'main'
    pr_strategy: PRStrategy = PRStrategy.ALL_PASSING

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestSettings':
        """Create TestSettings from dictionary.
        
        Args:
            data: Dictionary containing test settings
            
        Returns:
            TestSettings instance
        """
        return cls(
            auto_fix=data.get('auto_fix', False),
            create_pr=data.get('create_pr', False),
            max_retries=data.get('max_retries', 1),
            base_branch=data.get('base_branch', 'main'),
            pr_strategy=PRStrategy.from_str(data.get('pr_strategy', 'ALL_PASSING'))
        )

@dataclass
class TestConfiguration:
    """Configuration for test execution.
    
    Attributes:
        name: Name of the test configuration
        file_path: Path to the test file
        config_path: Path to the configuration file
        agent_type: Type of agent to use (optional)
        description: Description of the test (optional)
        metadata: Test metadata (optional)
        evaluation: Evaluation criteria (optional)
        regions: List of test regions (optional)
        steps: List of test steps (optional)
        settings: Test execution settings
    """
    name: str
    file_path: Path
    config_path: Path
    agent_type: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[TestEvaluation] = None
    regions: Optional[List[Dict[str, Any]]] = None
    steps: Optional[List[Dict[str, Any]]] = None
    settings: TestSettings = TestSettings()

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: Path) -> 'TestConfiguration':
        """Create TestConfiguration from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            config_path: Path to the configuration file
            
        Returns:
            TestConfiguration instance
        """
        return cls(
            name=data['name'],
            file_path=Path(data['file_path']),
            config_path=config_path,
            agent_type=data.get('agent_type'),
            description=data.get('description'),
            metadata=TestMetadata.from_dict(data.get('metadata', {})) if 'metadata' in data else None,
            evaluation=TestEvaluation.from_dict(data.get('evaluation', {})) if 'evaluation' in data else None,
            regions=data.get('regions'),
            steps=data.get('steps'),
            settings=TestSettings.from_dict(data)
        )

@dataclass
class TestResult:
    """Data class to hold test results.
    
    Attributes:
        name: Name of the test
        file_path: Path to the test file
        config_path: Path to the configuration file
        results: Dictionary containing test results
        failed_tests: List of failed tests
        test_attempts: List of test attempts (optional)
    """
    name: str
    file_path: Path
    config_path: Path
    results: Dict[str, Any]
    failed_tests: List[Dict[str, Any]]
    test_attempts: Optional[List[Dict[str, Any]]] = None

class Result(Generic[T]):
    """Generic result class for operations.
    
    This class provides a type-safe way to handle operation results that may
    either succeed with a value or fail with an error.
    
    Attributes:
        _value: The result value if successful
        _error: The error if the operation failed
    """
    
    def __init__(self, value: Optional[T] = None, error: Optional[Exception] = None):
        """Initialize a Result instance.
        
        Args:
            value: The result value (if successful)
            error: The error (if failed)
        """
        self._value = value
        self._error = error
    
    @property
    def is_success(self) -> bool:
        """Check if the operation was successful.
        
        Returns:
            True if the operation succeeded, False otherwise
        """
        return self._error is None
    
    @property
    def value(self) -> T:
        """Get the result value.
        
        Returns:
            The result value
            
        Raises:
            ValueError: If the operation failed
        """
        if not self.is_success:
            raise ValueError("Cannot get value from failed result")
        return self._value
    
    @property
    def error(self) -> Exception:
        """Get the error if the operation failed.
        
        Returns:
            The error
            
        Raises:
            ValueError: If the operation succeeded
        """
        if self.is_success:
            raise ValueError("Cannot get error from successful result")
        return self._error
    
    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        """Create a successful result.
        
        Args:
            value: The result value
            
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