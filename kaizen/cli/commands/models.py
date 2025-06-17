"""Data models for test commands.

This module defines the data models used by test commands, including
test metadata, evaluation criteria, and test steps.

Example:
    >>> metadata = TestMetadata(
    ...     version="1.0.0",
    ...     dependencies=["pytest>=7.0.0"],
    ...     environment_variables=["API_KEY"]
    ... )
    >>> evaluation = TestEvaluation(
    ...     criteria=[{"name": "accuracy", "threshold": 0.9}],
    ...     llm_provider="openai",
    ...     model="gpt-4"
    ... )
"""

from typing import Dict, Any, Optional, List, TypeVar, Generic, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from .types import PRStrategy

T = TypeVar('T')

class PRStrategy(str, Enum):
    """Strategy for when to create pull requests.
    
    Attributes:
        ALL_PASSING: Create PR only when all tests pass
        ANY_PASSING: Create PR when any test passes
        ALWAYS: Always create PR regardless of test results
    """
    ALL_PASSING = "ALL_PASSING"
    ANY_PASSING = "ANY_PASSING"
    ALWAYS = "ALWAYS"

@dataclass
class TestMetadata:
    """Metadata for a test configuration.
    
    This class represents the metadata associated with a test configuration,
    including version information, dependencies, and environment variables.
    
    Attributes:
        version: Version of the test configuration
        dependencies: List of required dependencies with version constraints
        environment_variables: List of required environment variables
        author: Author of the test configuration
        created_at: Creation timestamp
        updated_at: Last update timestamp
        description: Description of the test configuration
        
    Example:
        >>> metadata = TestMetadata(
        ...     version="1.0.0",
        ...     dependencies=["pytest>=7.0.0", "requests>=2.0.0"],
        ...     environment_variables=["API_KEY", "SECRET_KEY"]
        ... )
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
class TestSettings:
    """Settings for test execution.
    
    This class represents the execution settings for a test,
    including timeout and retry configurations.
    
    Attributes:
        timeout: Timeout in seconds for test execution
        retries: Number of retry attempts for failed tests
        
    Example:
        >>> settings = TestSettings(timeout=30, retries=3)
    """
    timeout: Optional[int] = None
    retries: Optional[int] = None

@dataclass
class TestEvaluation:
    """Evaluation criteria for test results.
    
    This class represents the evaluation criteria and settings
    for assessing test results, including LLM configuration.
    
    Attributes:
        criteria: List of evaluation criteria with weights and descriptions
        llm_provider: LLM provider to use for evaluation (e.g., 'openai', 'gemini')
        model: Model to use for evaluation (e.g., 'gpt-4', 'gemini-pro')
        thresholds: Thresholds for evaluation criteria
        settings: Test execution settings
        
    Example:
        >>> evaluation = TestEvaluation(
        ...     criteria=[
        ...         {"name": "accuracy", "weight": 0.7},
        ...         {"name": "completeness", "weight": 0.3}
        ...     ],
        ...     llm_provider="openai",
        ...     model="gpt-4"
        ... )
    """
    criteria: List[Dict[str, Any]]
    llm_provider: str
    model: str
    thresholds: Dict[str, Any] = field(default_factory=dict)
    settings: TestSettings = field(default_factory=TestSettings)

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
            llm_provider=data.get('llm_provider', ''),
            model=data.get('model', ''),
            thresholds=data.get('thresholds', {}),
            settings=TestSettings.from_dict(data)
        )

@dataclass
class TestStep:
    """A single test step.
    
    This class represents a single step in a test sequence,
    including input data and execution details.
    
    Attributes:
        step_index: Index of the step in the sequence
        name: Name of the step
        description: Description of the step's purpose
        input: Input data for the step, including file path, region, and method
        
    Example:
        >>> step = TestStep(
        ...     step_index=1,
        ...     name="Basic Email Improvement",
        ...     description="Test basic email improvement functionality",
        ...     input={
        ...         "file_path": "email_agent.py",
        ...         "region": "email_agent",
        ...         "method": "improve_email",
        ...         "input": "Please improve this email..."
        ...     }
        ... )
    """
    step_index: int
    name: str
    description: Optional[str] = None
    input: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class TestConfiguration:
    """Configuration for test execution.
    
    This class represents the complete configuration for test execution,
    including test metadata, execution settings, and auto-fix options.
    
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
        auto_fix: Whether to enable auto-fix functionality
        create_pr: Whether to create pull requests for fixes
        max_retries: Maximum number of retry attempts for auto-fix (min: 1, max: 10)
        base_branch: Base branch for pull requests (e.g., 'main', 'master')
        pr_strategy: Strategy for when to create PRs (ALL_PASSING, ANY_PASSING, ALWAYS)
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
    settings: TestSettings = field(default_factory=TestSettings)
    auto_fix: bool = False
    create_pr: bool = False
    max_retries: int = 3
    base_branch: str = 'main'
    pr_strategy: PRStrategy = PRStrategy.ALL_PASSING

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate configuration values.
        
        Raises:
            ValueError: If any configuration value is invalid
        """
        self._validate_retries()
        self._validate_branch()
        self._validate_paths()

    def _validate_retries(self) -> None:
        """Validate max_retries value.
        
        Raises:
            ValueError: If max_retries is invalid
        """
        if not 1 <= self.max_retries <= 10:
            raise ValueError(f"max_retries must be between 1 and 10, got {self.max_retries}")

    def _validate_branch(self) -> None:
        """Validate base_branch value.
        
        Raises:
            ValueError: If base_branch is invalid
        """
        if not self.base_branch or not isinstance(self.base_branch, str):
            raise ValueError("base_branch must be a non-empty string")

    def _validate_paths(self) -> None:
        """Validate file paths.
        
        Raises:
            ValueError: If any file path is invalid
        """
        if not self.file_path.exists():
            raise ValueError(f"Test file not found: {self.file_path}")
        if not self.config_path.exists():
            raise ValueError(f"Configuration file not found: {self.config_path}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: Path) -> 'TestConfiguration':
        """Create TestConfiguration from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            config_path: Path to the configuration file
            
        Returns:
            TestConfiguration instance
            
        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate and convert pr_strategy
        pr_strategy = cls._parse_pr_strategy(data.get('pr_strategy', 'ALL_PASSING'))

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
            settings=TestSettings.from_dict(data),
            auto_fix=data.get('auto_fix', False),
            create_pr=data.get('create_pr', False),
            max_retries=data.get('max_retries', 3),
            base_branch=data.get('base_branch', 'main'),
            pr_strategy=pr_strategy
        )

    @staticmethod
    def _parse_pr_strategy(value: Union[str, PRStrategy]) -> PRStrategy:
        """Parse PR strategy value.
        
        Args:
            value: PR strategy value (string or enum)
            
        Returns:
            PRStrategy enum value
            
        Raises:
            ValueError: If value is invalid
        """
        if isinstance(value, PRStrategy):
            return value
        if not isinstance(value, str):
            raise ValueError(f"PR strategy must be a string or PRStrategy enum, got {type(value)}")
        try:
            return PRStrategy.from_str(value)
        except ValueError as e:
            raise ValueError(f"Invalid PR strategy: {value}") from e

@dataclass
class TestResult:
    """Result of a test execution.
    
    This class represents the results of a test execution,
    including test metadata and execution results.
    
    Attributes:
        name: Name of the test
        file_path: Path to the test file
        config_path: Path to the test configuration
        results: Test results including status and metrics
        
    Example:
        >>> result = TestResult(
        ...     name="Email Agent Test",
        ...     file_path="email_agent.py",
        ...     config_path="test_config.yaml",
        ...     results={"status": "passed", "score": 0.95}
        ... )
    """
    name: str
    file_path: Union[str, Path]
    config_path: Union[str, Path]
    results: Dict[str, Any] = field(default_factory=dict)

class Result(Generic[T]):
    """Generic result container for operations that may fail.
    
    This class provides a type-safe way to handle operations that may
    fail, with proper error handling and type checking.
    
    Attributes:
        value: The successful result value
        error: The error that occurred
        
    Example:
        >>> result = Result.success("test passed")
        >>> if result.is_success:
        ...     print(result.value)
        ... else:
        ...     print(f"Error: {result.error}")
    """
    def __init__(self, value: Optional[T] = None, error: Optional[Exception] = None):
        self.value = value
        self.error = error

    @property
    def is_success(self) -> bool:
        """Check if the operation was successful.
        
        Returns:
            True if the operation was successful, False otherwise
        """
        return self.error is None

    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        """Create a successful result.
        
        Args:
            value: The successful result value
            
        Returns:
            Result instance with the success value
        """
        return cls(value=value)

    @classmethod
    def failure(cls, error: Exception) -> 'Result[T]':
        """Create a failed result.
        
        Args:
            error: The error that occurred
            
        Returns:
            Result instance with the error
        """
        return cls(error=error) 