"""Configuration handling for Kaizen CLI test commands."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .models import TestConfiguration, TestMetadata, TestEvaluation, TestSettings, Result
from .types import ConfigurationError, PRStrategy

class ConfigurationManager:
    """Manages test configuration loading and validation."""
    
    @staticmethod
    def load_configuration(
        config_path: Path,
        auto_fix: bool = False,
        create_pr: bool = False,
        max_retries: int = 1,
        base_branch: str = 'main',
        pr_strategy: str = 'ALL_PASSING'
    ) -> Result[TestConfiguration]:
        """Load and validate test configuration from file.
        
        Args:
            config_path: Path to the configuration file
            auto_fix: Whether to automatically fix failing tests
            create_pr: Whether to create a pull request with fixes
            max_retries: Maximum number of retry attempts
            base_branch: Base branch for pull request
            pr_strategy: Strategy for when to create PRs ('ALL_PASSING', 'ANY_IMPROVEMENT', 'NONE')
            
        Returns:
            Result containing TestConfiguration if successful, error otherwise
        """
        try:
            # Load config file
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
            
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
            
            # Add CLI arguments to config data
            config_data.update({
                'auto_fix': auto_fix,
                'create_pr': create_pr,
                'max_retries': max_retries,
                'base_branch': base_branch,
                'pr_strategy': pr_strategy
            })
            
            # Create configuration
            config = TestConfiguration.from_dict(config_data, config_path)
            return Result.success(config)
            
        except Exception as e:
            return Result.failure(ConfigurationError(f"Failed to load configuration: {str(e)}"))
    
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