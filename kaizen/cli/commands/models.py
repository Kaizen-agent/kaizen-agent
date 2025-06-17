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

from typing import Dict, Any, Optional, List, TypeVar, Generic, Union, Type
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from .types import PRStrategy
from .errors import ConfigurationError

T = TypeVar('T')

class ConfigurationValidationError(ConfigurationError):
    """Base class for configuration validation errors."""
    pass

class RequiredFieldError(ConfigurationValidationError):
    """Error raised when a required field is missing."""
    pass

class InvalidValueError(ConfigurationValidationError):
    """Error raised when a field value is invalid."""
    pass

class PathResolutionError(ConfigurationError):
    """Error raised when there is a problem resolving file paths."""
    pass

class ValidationResult:
    """Result of a validation operation.
    
    Attributes:
        is_valid: Whether the validation passed
        errors: List of validation errors
    """
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []

    def add_error(self, error: str) -> None:
        """Add a validation error.
        
        Args:
            error: Error message to add
        """
        self.is_valid = False
        self.errors.append(error)

    def raise_if_invalid(self) -> None:
        """Raise an exception if validation failed.
        
        Raises:
            ConfigurationValidationError: If validation failed
        """
        if not self.is_valid:
            raise ConfigurationValidationError("\n".join(self.errors))

@dataclass
class PathResolver:
    """Utility class for resolving file paths.
    
    This class handles path resolution relative to a base directory,
    with proper error handling and validation.
    
    Attributes:
        base_dir: Base directory for resolving relative paths
    """
    base_dir: Path

    def resolve(self, path: Union[str, Path]) -> Path:
        """Resolve a path relative to the base directory.
        
        Args:
            path: Path to resolve (string or Path object)
            
        Returns:
            Resolved absolute path
            
        Raises:
            PathResolutionError: If path resolution fails
        """
        try:
            path = Path(path)
            if path.is_absolute():
                return path
            return (self.base_dir / path).resolve()
        except Exception as e:
            raise PathResolutionError(f"Failed to resolve path {path}: {str(e)}") from e

    def validate_exists(self, path: Union[str, Path]) -> Path:
        """Resolve and validate that a path exists.
        
        Args:
            path: Path to resolve and validate
            
        Returns:
            Resolved absolute path
            
        Raises:
            PathResolutionError: If path doesn't exist or resolution fails
        """
        resolved_path = self.resolve(path)
        if not resolved_path.exists():
            raise PathResolutionError(
                f"Path does not exist: {path} (resolved to: {resolved_path})"
            )
        return resolved_path

class ConfigurationValidator:
    """Validator for test configuration.
    
    This class handles validation of configuration values before
    creating a TestConfiguration instance.
    
    Attributes:
        data: Configuration data to validate
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.result = ValidationResult()

    def validate(self) -> None:
        """Validate all configuration values.
        
        Raises:
            ConfigurationValidationError: If any validation fails
        """
        self._validate_required_fields()
        self._validate_max_retries()
        self._validate_base_branch()
        self._validate_optional_fields()
        self.result.raise_if_invalid()

    def _validate_required_fields(self) -> None:
        """Validate that all required fields are present."""
        required_fields = ['name', 'file_path']
        for field in required_fields:
            if field not in self.data:
                self.result.add_error(f"Configuration must include '{field}' field")

    def _validate_max_retries(self) -> None:
        """Validate max_retries value."""
        max_retries = self.data.get('max_retries', 3)
        if not 1 <= max_retries <= 10:
            self.result.add_error(f"max_retries must be between 1 and 10, got {max_retries}")

    def _validate_base_branch(self) -> None:
        """Validate base_branch value."""
        base_branch = self.data.get('base_branch', 'main')
        if not base_branch or not isinstance(base_branch, str):
            self.result.add_error("base_branch must be a non-empty string")

    def _validate_optional_fields(self) -> None:
        """Validate optional fields if present."""
        if 'metadata' in self.data and not isinstance(self.data['metadata'], dict):
            self.result.add_error("metadata must be a dictionary")
        if 'evaluation' in self.data and not isinstance(self.data['evaluation'], dict):
            self.result.add_error("evaluation must be a dictionary")
        if 'regions' in self.data and not isinstance(self.data['regions'], list):
            self.result.add_error("regions must be a list")
        if 'steps' in self.data and not isinstance(self.data['steps'], list):
            self.result.add_error("steps must be a list")

class PRStrategyParser:
    """Parser for PR strategy values.
    
    This class handles parsing and validation of PR strategy values.
    """
    @staticmethod
    def parse(value: Union[str, PRStrategy]) -> PRStrategy:
        """Parse PR strategy value.
        
        Args:
            value: PR strategy value (string or enum)
            
        Returns:
            PRStrategy enum value
            
        Raises:
            InvalidValueError: If value is invalid
        """
        if isinstance(value, PRStrategy):
            return value
        if not isinstance(value, str):
            raise InvalidValueError(f"PR strategy must be a string or PRStrategy enum, got {type(value)}")
        try:
            return PRStrategy.from_str(value)
        except ValueError as e:
            raise InvalidValueError(f"Invalid PR strategy: {value}") from e

class ConfigurationBuilder:
    """Builder for TestConfiguration instances.
    
    This class handles the creation of TestConfiguration instances
    with proper validation and error handling.
    
    Attributes:
        data: Configuration data
        config_path: Path to the configuration file
    """
    def __init__(self, data: Dict[str, Any], config_path: Path):
        self.data = data
        self.config_path = config_path
        self.validator = ConfigurationValidator(data)
        self.path_resolver = PathResolver(config_path.parent)

    def build(self) -> 'TestConfiguration':
        """Build a TestConfiguration instance.
        
        Returns:
            TestConfiguration instance
            
        Raises:
            ConfigurationValidationError: If configuration validation fails
            PathResolutionError: If file path resolution fails
        """
        # Validate configuration
        self.validator.validate()
        
        # Parse PR strategy
        pr_strategy = PRStrategyParser.parse(self.data.get('pr_strategy', 'ALL_PASSING'))

        # Resolve file path
        try:
            file_path = self.path_resolver.resolve(self.data['file_path'])
        except PathResolutionError as e:
            raise ConfigurationValidationError(f"Invalid file path in configuration: {str(e)}") from e

        # Prepare all fields
        metadata = self._build_metadata()
        evaluation = self._build_evaluation()
        settings = self._build_settings()

        # Create instance
        return TestConfiguration(
            name=self.data['name'],
            file_path=file_path,
            config_path=self.config_path,
            agent_type=self.data.get('agent_type'),
            description=self.data.get('description'),
            metadata=metadata,
            evaluation=evaluation,
            regions=self.data.get('regions'),
            steps=self.data.get('steps'),
            settings=settings,
            auto_fix=self.data.get('auto_fix', False),
            create_pr=self.data.get('create_pr', False),
            max_retries=self.data.get('max_retries', 3),
            base_branch=self.data.get('base_branch', 'main'),
            pr_strategy=pr_strategy
        )

    def _build_metadata(self) -> Optional[TestMetadata]:
        """Build TestMetadata instance if present."""
        if 'metadata' in self.data:
            return TestMetadata.from_dict(self.data['metadata'])
        return None

    def _build_evaluation(self) -> Optional[TestEvaluation]:
        """Build TestEvaluation instance if present."""
        if 'evaluation' in self.data:
            return TestEvaluation.from_dict(self.data['evaluation'])
        return None

    def _build_settings(self) -> TestSettings:
        """Build TestSettings instance."""
        return TestSettings.from_dict(self.data)

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
        evaluation: Test evaluation criteria (optional)
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: Path) -> 'TestConfiguration':
        """Create TestConfiguration from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            config_path: Path to the configuration file
            
        Returns:
            TestConfiguration instance
            
        Raises:
            ConfigurationValidationError: If configuration validation fails
            PathResolutionError: If file path resolution fails
        """
        builder = ConfigurationBuilder(data, config_path)
        return builder.build()

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