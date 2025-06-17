"""Test configuration models.

This module contains the main TestConfiguration class and related models
for test configuration.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum

from .types import PRStrategy
from .models import TestMetadata, TestEvaluation, TestSettings
from .validation import ConfigurationValidator
from .errors import ConfigurationError, FileNotFoundError

@dataclass(frozen=True)
class TestConfiguration:
    """Configuration for test execution.
    
    This class represents the complete configuration for a test,
    including metadata, evaluation criteria, and execution settings.
    
    Attributes:
        name: Name of the test
        file_path: Path to the test file
        config_path: Path to the configuration file
        agent_type: Type of agent to use
        description: Description of the test
        metadata: Test metadata
        evaluation: Test evaluation criteria
        regions: List of regions to test
        steps: List of test steps
        settings: Test settings
        auto_fix: Whether to automatically fix issues
        create_pr: Whether to create a PR for fixes
        max_retries: Maximum number of retry attempts
        base_branch: Base branch for PR creation
        pr_strategy: Strategy for PR creation
    """
    name: str
    file_path: Path
    config_path: Path
    agent_type: str
    description: Optional[str] = None
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[TestEvaluation] = None
    regions: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    settings: Optional[TestSettings] = None
    auto_fix: bool = False
    create_pr: bool = False
    max_retries: int = 3
    base_branch: str = "main"
    pr_strategy: PRStrategy = PRStrategy.CREATE_NEW

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: Path) -> 'TestConfiguration':
        """Create a TestConfiguration instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration data
            config_path: Path to the configuration file
            
        Returns:
            TestConfiguration instance
            
        Raises:
            ConfigurationError: If configuration is invalid
            FileNotFoundError: If test file does not exist
        """
        validator = ConfigurationValidator(data)
        validator.validate()
        
        file_path = cls._resolve_path(data['file_path'], config_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")
            
        return cls(
            name=data['name'],
            file_path=file_path,
            config_path=config_path,
            agent_type=data.get('agent_type', 'default'),
            description=data.get('description'),
            metadata=TestMetadata.from_dict(data.get('metadata', {})) if 'metadata' in data else None,
            evaluation=TestEvaluation.from_dict(data.get('evaluation', {})) if 'evaluation' in data else None,
            regions=data.get('regions', []),
            steps=data.get('steps', []),
            settings=TestSettings.from_dict(data.get('settings', {})) if 'settings' in data else None,
            auto_fix=data.get('auto_fix', False),
            create_pr=data.get('create_pr', False),
            max_retries=data.get('max_retries', 3),
            base_branch=data.get('base_branch', 'main'),
            pr_strategy=cls._parse_pr_strategy(data.get('pr_strategy', PRStrategy.CREATE_NEW))
        )

    @staticmethod
    def _resolve_path(path: str, config_path: Path) -> Path:
        """Resolve a path relative to the configuration file.
        
        Args:
            path: Path to resolve
            config_path: Path to the configuration file
            
        Returns:
            Resolved Path object
        """
        path_obj = Path(path)
        return path_obj if path_obj.is_absolute() else config_path.parent / path

    @staticmethod
    def _parse_pr_strategy(strategy: Any) -> PRStrategy:
        """Parse PR strategy from input.
        
        Args:
            strategy: Strategy to parse (string or PRStrategy)
            
        Returns:
            PRStrategy enum value
            
        Raises:
            ConfigurationError: If strategy is invalid
        """
        if isinstance(strategy, PRStrategy):
            return strategy
        if isinstance(strategy, str):
            try:
                return PRStrategy[strategy.upper()]
            except KeyError:
                raise ConfigurationError(f"Invalid PR strategy: {strategy}")
        raise ConfigurationError(f"PR strategy must be string or PRStrategy, got {type(strategy)}") 