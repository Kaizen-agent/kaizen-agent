"""Configuration parsing for test commands.

This module provides functionality for parsing test configuration data into
appropriate model objects, with validation and type safety.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .errors import ConfigurationError
from .result import Result
from .models import TestMetadata, TestEvaluation, TestSettings

@dataclass
class ParseResult:
    """Result of parsing configuration data.
    
    Attributes:
        metadata: Parsed metadata if present
        evaluation: Parsed evaluation if present
        errors: List of parsing errors if any
    """
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[TestEvaluation] = None
    errors: list[str] = None

    def __post_init__(self):
        """Initialize errors list if None."""
        if self.errors is None:
            self.errors = []

    @property
    def has_errors(self) -> bool:
        """Check if there are any parsing errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return len(self.errors) > 0

class ConfigurationParser:
    """Parses test configuration data into model objects.
    
    This class provides methods to parse configuration data into appropriate
    model objects, with validation and type safety.
    """
    
    def parse_configuration(self, config_data: Dict[str, Any]) -> Result[ParseResult]:
        """Parse configuration data into model objects.
        
        Args:
            config_data: Configuration data to parse
            
        Returns:
            Result containing parsed objects or errors
        """
        try:
            result = ParseResult()
            
            # Parse metadata if present
            if 'metadata' in config_data:
                metadata_result = self._parse_metadata(config_data['metadata'])
                if metadata_result.is_success:
                    result.metadata = metadata_result.value
                else:
                    result.errors.append(str(metadata_result.error))
            
            # Parse evaluation if present
            if 'evaluation' in config_data:
                evaluation_result = self._parse_evaluation(config_data['evaluation'])
                if evaluation_result.is_success:
                    result.evaluation = evaluation_result.value
                else:
                    result.errors.append(str(evaluation_result.error))
            
            if result.has_errors:
                return Result.failure(
                    ConfigurationError(
                        "Failed to parse configuration",
                        {"errors": result.errors}
                    )
                )
            
            return Result.success(result)
            
        except Exception as e:
            return Result.failure(
                ConfigurationError(
                    f"Unexpected error parsing configuration: {str(e)}",
                    {"error": str(e)}
                )
            )
    
    def _parse_metadata(self, metadata_data: Dict[str, Any]) -> Result[TestMetadata]:
        """Parse metadata from configuration data.
        
        Args:
            metadata_data: Metadata configuration data
            
        Returns:
            Result containing parsed TestMetadata or error
        """
        try:
            if not isinstance(metadata_data, dict):
                return Result.failure(
                    ConfigurationError(
                        "Invalid metadata format: expected a dictionary",
                        {"data": metadata_data}
                    )
                )
            
            # Validate required fields
            required_fields = ['version']
            missing_fields = [
                field for field in required_fields
                if field not in metadata_data
            ]
            if missing_fields:
                return Result.failure(
                    ConfigurationError(
                        f"Missing required metadata fields: {', '.join(missing_fields)}",
                        {"missing_fields": missing_fields}
                    )
                )
            
            metadata = TestMetadata(
                version=metadata_data['version'],
                author=metadata_data.get('author'),
                created_at=metadata_data.get('created_at'),
                updated_at=metadata_data.get('updated_at'),
                description=metadata_data.get('description')
            )
            
            return Result.success(metadata)
            
        except Exception as e:
            return Result.failure(
                ConfigurationError(
                    f"Failed to parse metadata: {str(e)}",
                    {"error": str(e)}
                )
            )
    
    def _parse_evaluation(self, evaluation_data: Dict[str, Any]) -> Result[TestEvaluation]:
        """Parse evaluation criteria from configuration data.
        
        Args:
            evaluation_data: Evaluation configuration data
            
        Returns:
            Result containing parsed TestEvaluation or error
        """
        try:
            if not isinstance(evaluation_data, dict):
                return Result.failure(
                    ConfigurationError(
                        "Invalid evaluation format: expected a dictionary",
                        {"data": evaluation_data}
                    )
                )
            
            # Validate required fields
            required_fields = ['criteria']
            missing_fields = [
                field for field in required_fields
                if field not in evaluation_data
            ]
            if missing_fields:
                return Result.failure(
                    ConfigurationError(
                        f"Missing required evaluation fields: {', '.join(missing_fields)}",
                        {"missing_fields": missing_fields}
                    )
                )
            
            # Parse settings
            settings_data = evaluation_data.get('settings', {})
            settings = TestSettings(
                timeout=settings_data.get('timeout'),
                retries=settings_data.get('retries')
            )
            
            evaluation = TestEvaluation(
                criteria=evaluation_data['criteria'],
                thresholds=evaluation_data.get('thresholds', {}),
                settings=settings
            )
            
            return Result.success(evaluation)
            
        except Exception as e:
            return Result.failure(
                ConfigurationError(
                    f"Failed to parse evaluation: {str(e)}",
                    {"error": str(e)}
                )
            ) 