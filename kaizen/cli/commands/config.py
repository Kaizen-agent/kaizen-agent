"""Configuration management for Kaizen CLI test commands.

This module provides a high-level interface for managing test configurations,
combining loading, validation, and configuration object creation. It handles
the parsing and validation of test configuration files, ensuring they meet
the required schema and contain all necessary information for test execution.

The ConfigurationManager class serves as the main entry point for configuration
operations, providing methods for loading, validating, and parsing test
configurations.
"""

# Standard library imports
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Local application imports
from kaizen.cli.commands.config_loader import ConfigurationLoader
from kaizen.cli.commands.config_parser import ConfigurationParser
from kaizen.cli.commands.config_validator import ConfigurationValidator
from kaizen.cli.commands.errors import ConfigurationError
from kaizen.cli.commands.models import (
    TestConfiguration,
    TestEvaluation,
    TestMetadata,
)
from kaizen.cli.commands.models.settings import TestSettings
from kaizen.cli.commands.result import Result
from kaizen.cli.commands.types import PRStrategy, DEFAULT_MAX_RETRIES, Language, DEFAULT_LANGUAGE

# Configure logging
logger = logging.getLogger(__name__)

class ConfigurationManager:
    """Manages test configuration loading and validation.
    
    This class provides a high-level interface for managing test configurations,
    combining loading, validation, and configuration object creation.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.validator = ConfigurationValidator()
        self.loader = ConfigurationLoader(self.validator)
        self.parser = ConfigurationParser()
    
    def load_configuration(
        self,
        config_path: Path,
        auto_fix: bool = False,
        create_pr: bool = False,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_branch: str = 'main',
        pr_strategy: str = 'ALL_PASSING'
    ) -> Result[TestConfiguration]:
        """Load and validate test configuration, allowing CLI overrides except for language.
        
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
            logger.debug(f"Loaded configuration data: {config_data}")

            # Prepare CLI overrides (except language)
            cli_overrides = {
                'auto_fix': auto_fix,
                'create_pr': create_pr,
                'max_retries': max_retries,
                'base_branch': base_branch,
                'pr_strategy': pr_strategy
            }

            logger.debug(f"Original config_data language: {config_data.get('language', 'NOT_SET')}")
            logger.debug(f"CLI overrides: {cli_overrides}")

            # Create configuration object with CLI overrides (except language)
            try:
                config = TestConfiguration.from_dict(config_data, config_path, cli_overrides)
                logger.debug(f"Final config language: {config.language}")
            except ValueError as e:
                return Result.failure(ConfigurationError(str(e)))

            logger.info(f"Created configuration object: {config}")
            return Result.success(config)

        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}", exc_info=True)
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
    
    def _parse_metadata(self, metadata_data: Dict[str, Any]) -> Optional[TestMetadata]:
        """Parse metadata from configuration data.
        
        Args:
            metadata_data: Metadata configuration data
            
        Returns:
            Parsed TestMetadata object or None if invalid
        """
        if not isinstance(metadata_data, dict):
            return None
            
        return TestMetadata(
            version=metadata_data.get('version'),
            author=metadata_data.get('author'),
            created_at=metadata_data.get('created_at'),
            updated_at=metadata_data.get('updated_at'),
            description=metadata_data.get('description')
        )
    
    def _parse_evaluation(self, evaluation_data: Dict[str, Any]) -> Optional[TestEvaluation]:
        """Parse evaluation criteria from configuration data.
        
        Args:
            evaluation_data: Evaluation configuration data
            
        Returns:
            Parsed TestEvaluation object or None if invalid
        """
        if not isinstance(evaluation_data, dict):
            return None
            
        return TestEvaluation(
            criteria=evaluation_data.get('criteria', []),
            thresholds=evaluation_data.get('thresholds', {}),
            settings=TestSettings(
                timeout=evaluation_data.get('settings', {}).get('timeout'),
                retries=evaluation_data.get('settings', {}).get('retries')
            )
        ) 