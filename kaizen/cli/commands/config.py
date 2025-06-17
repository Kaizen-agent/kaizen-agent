"""Configuration management for test commands.

This module provides a high-level interface for managing test configurations,
combining loading, validation, and configuration object creation.
"""

from pathlib import Path
from typing import Dict, Any, Optional

from .errors import ConfigurationError
from .types import PRStrategy
from .result import Result
from .models import TestConfiguration
from .config_loader import ConfigurationLoader
from .config_validator import ConfigurationValidator

class ConfigurationManager:
    """Manages test configuration loading and validation.
    
    This class provides a high-level interface for managing test configurations,
    combining loading, validation, and configuration object creation.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.validator = ConfigurationValidator()
        self.loader = ConfigurationLoader(self.validator)
    
    def load_configuration(
        self,
        config_path: Path,
        auto_fix: bool = False,
        create_pr: bool = False,
        max_retries: int = 3,
        base_branch: str = 'main',
        pr_strategy: str = 'ALL_PASSING'
    ) -> Result[TestConfiguration]:
        """Load and validate test configuration.
        
        Args:
            config_path: Path to the configuration file
            auto_fix: Whether to enable auto-fix
            create_pr: Whether to create pull requests
            max_retries: Maximum number of retry attempts
            base_branch: Base branch for pull requests
            pr_strategy: Strategy for when to create PRs
            
        Returns:
            Result containing the validated configuration or an error
        """
        try:
            # Load configuration from file
            load_result = self.loader.load_from_file(config_path)
            if not load_result.is_success:
                return load_result
            
            config_data = load_result.value
            
            # Create configuration object
            config = TestConfiguration(
                name=config_data['name'],
                file_path=Path(config_data['file_path']),
                config_path=config_path,
                auto_fix=auto_fix,
                create_pr=create_pr,
                max_retries=max_retries,
                base_branch=base_branch,
                pr_strategy=PRStrategy.from_str(pr_strategy)
            )
            
            # Add optional fields if present
            if 'description' in config_data:
                config.description = config_data['description']
            if 'agent_type' in config_data:
                config.agent_type = config_data['agent_type']
            if 'regions' in config_data:
                config.regions = config_data['regions']
            if 'steps' in config_data:
                config.steps = config_data['steps']
            if 'metadata' in config_data:
                config.metadata = config_data['metadata']
            if 'evaluation' in config_data:
                config.evaluation = config_data['evaluation']
            
            return Result.success(config)
            
        except Exception as e:
            return Result.failure(
                ConfigurationError(
                    f"Unexpected error loading configuration: {str(e)}",
                    {"error": str(e)}
                )
            )
    
    @staticmethod
    def _validate_configuration(config_data: Dict[str, Any]) -> Result[None]:
        """Validate configuration data.
        
        Args:
            config_data: Dictionary containing configuration data
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Validate required fields
            required_fields = ['name', 'file_path']
            missing_fields = [field for field in required_fields if field not in config_data]
            if missing_fields:
                return Result.failure(ConfigurationError(
                    f"Missing required fields in configuration: {', '.join(missing_fields)}"
                ))
            
            # Validate test structure
            if 'regions' not in config_data and 'steps' not in config_data:
                return Result.failure(ConfigurationError(
                    "Test configuration must contain either 'regions' or 'steps'"
                ))
            
            return Result.success(None)
        except Exception as e:
            return Result.failure(ConfigurationError(f"Configuration validation error: {str(e)}"))
    
    @staticmethod
    def _resolve_file_path(config_path: Path, file_path: str) -> Optional[Path]:
        """Resolve file path relative to config file.
        
        Args:
            config_path: Path to the configuration file
            file_path: Path to the test file (relative to config file)
            
        Returns:
            Resolved absolute path if file exists, None otherwise
        """
        resolved_path = (config_path.parent / file_path).resolve()
        return resolved_path if resolved_path.exists() else None
    
    @staticmethod
    def _parse_metadata(config_data: Dict[str, Any]) -> Optional[TestMetadata]:
        """Parse metadata from configuration.
        
        Args:
            config_data: Dictionary containing configuration data
            
        Returns:
            TestMetadata instance if metadata exists, None otherwise
        """
        if 'metadata' not in config_data:
            return None
        return TestMetadata.from_dict(config_data['metadata'])
    
    @staticmethod
    def _parse_evaluation(config_data: Dict[str, Any]) -> Optional[TestEvaluation]:
        """Parse evaluation criteria from configuration.
        
        Args:
            config_data: Dictionary containing configuration data
            
        Returns:
            TestEvaluation instance if evaluation exists, None otherwise
        """
        if 'evaluation' not in config_data:
            return None
        return TestEvaluation.from_dict(config_data['evaluation']) 