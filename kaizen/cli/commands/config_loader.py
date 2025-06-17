"""Configuration loading for test commands.

This module provides functionality for loading test configurations from files,
handling file operations and YAML parsing.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .errors import ConfigurationError
from .result import Result
from .config_validator import ConfigurationValidator

class ConfigurationLoader:
    """Loads test configuration from files.
    
    This class provides methods to load test configuration from files,
    handling file operations and YAML parsing.
    """
    
    def __init__(self, validator: Optional[ConfigurationValidator] = None):
        """Initialize the loader.
        
        Args:
            validator: Optional validator to use for configuration validation
        """
        self.validator = validator or ConfigurationValidator()
    
    def load_from_file(self, config_path: Path) -> Result[Dict[str, Any]]:
        """Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Result containing the loaded configuration or an error
        """
        try:
            # Check if file exists
            if not config_path.exists():
                return Result.failure(
                    ConfigurationError(
                        f"Configuration file not found: {config_path}",
                        {"path": str(config_path)}
                    )
                )
            
            # Load and parse YAML
            with open(config_path) as f:
                try:
                    config_data = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    return Result.failure(
                        ConfigurationError(
                            f"Failed to parse YAML configuration: {str(e)}",
                            {"error": str(e)}
                        )
                    )
            
            # Validate configuration
            validation_result = self.validator.validate(config_data)
            if not validation_result.is_success:
                return validation_result
            
            return Result.success(config_data)
            
        except Exception as e:
            return Result.failure(
                ConfigurationError(
                    f"Unexpected error loading configuration: {str(e)}",
                    {"error": str(e)}
                )
            ) 