"""Validation utilities for test configuration.

This module contains validation utilities for test configuration,
including the ConfigurationValidator class.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from .errors import ConfigurationError
from .types import DEFAULT_MAX_RETRIES

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
            ConfigurationError: If validation failed
        """
        if not self.is_valid:
            raise ConfigurationError("\n".join(self.errors))

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
            ConfigurationError: If any validation fails
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
        """Validate max_retries field."""
        max_retries = self.data.get('max_retries', DEFAULT_MAX_RETRIES)
        
        if not isinstance(max_retries, int):
            raise ConfigurationError("max_retries must be an integer")
        
        if max_retries < 0:
            raise ConfigurationError("max_retries must be non-negative")
        
        if max_retries > 10:
            raise ConfigurationError("max_retries cannot exceed 10")

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