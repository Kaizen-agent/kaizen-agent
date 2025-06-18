"""Configuration validation for test commands.

This module provides validation functionality for test configurations,
ensuring that all required fields are present and valid.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .errors import ConfigurationError
from .result import Result

@dataclass
class ValidationRule:
    """A validation rule for configuration fields.
    
    Attributes:
        field: The field name to validate
        required: Whether the field is required
        type: The expected type of the field
        validator: Optional custom validation function
    """
    field: str
    required: bool = True
    type: Optional[type] = None
    validator: Optional[callable] = None

class ConfigurationValidator:
    """Validates test configuration data.
    
    This class provides methods to validate test configuration data,
    ensuring that all required fields are present and valid.
    """
    
    def __init__(self):
        """Initialize the validator with default rules."""
        self.rules = [
            ValidationRule('name', type=str),
            ValidationRule('file_path', type=str),
            ValidationRule('description', required=False, type=str),
            ValidationRule('agent_type', required=False, type=str),
            ValidationRule('regions', required=False, type=list),
            ValidationRule('steps', required=False, type=list),
            ValidationRule('metadata', required=False, type=dict),
            ValidationRule('evaluation', required=False, type=dict),
            ValidationRule('assertions', required=False, type=list),
            ValidationRule('expected_output', required=False, type=dict)
        ]
    
    def validate(self, config_data: Dict[str, Any]) -> Result[Dict[str, Any]]:
        """Validate configuration data.
        
        Args:
            config_data: The configuration data to validate
            
        Returns:
            Result containing the validated data or an error
        """
        try:
            # Check if config_data is a dictionary
            if not isinstance(config_data, dict):
                return Result.failure(
                    ConfigurationError(
                        "Invalid configuration format: expected a dictionary",
                        {"config": config_data}
                    )
                )
            
            # Validate required fields
            missing_fields = self._validate_required_fields(config_data)
            if missing_fields:
                return Result.failure(
                    ConfigurationError(
                        f"Missing required fields: {', '.join(missing_fields)}",
                        {"missing_fields": missing_fields}
                    )
                )
            
            # Validate field types
            type_errors = self._validate_field_types(config_data)
            if type_errors:
                return Result.failure(
                    ConfigurationError(
                        f"Type validation errors: {', '.join(type_errors)}",
                        {"type_errors": type_errors}
                    )
                )
            
            # Validate field values
            value_errors = self._validate_field_values(config_data)
            if value_errors:
                return Result.failure(
                    ConfigurationError(
                        f"Value validation errors: {', '.join(value_errors)}",
                        {"value_errors": value_errors}
                    )
                )
            
            return Result.success(config_data)
            
        except Exception as e:
            return Result.failure(
                ConfigurationError(
                    f"Unexpected error during validation: {str(e)}",
                    {"error": str(e)}
                )
            )
    
    def _validate_required_fields(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate that all required fields are present.
        
        Args:
            config_data: The configuration data to validate
            
        Returns:
            List of missing required fields
        """
        missing_fields = []
        for rule in self.rules:
            if rule.required and rule.field not in config_data:
                missing_fields.append(rule.field)
        return missing_fields
    
    def _validate_field_types(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate that all fields have the correct type.
        
        Args:
            config_data: The configuration data to validate
            
        Returns:
            List of type validation errors
        """
        type_errors = []
        for rule in self.rules:
            if rule.field in config_data and rule.type is not None:
                if not isinstance(config_data[rule.field], rule.type):
                    type_errors.append(
                        f"Field '{rule.field}' must be of type {rule.type.__name__}, "
                        f"got {type(config_data[rule.field]).__name__}"
                    )
        return type_errors
    
    def _validate_field_values(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate field values using custom validators.
        
        Args:
            config_data: The configuration data to validate
            
        Returns:
            List of value validation errors
        """
        value_errors = []
        for rule in self.rules:
            if rule.field in config_data and rule.validator is not None:
                try:
                    rule.validator(config_data[rule.field])
                except ValueError as e:
                    value_errors.append(f"Field '{rule.field}': {str(e)}")
        return value_errors 