"""Configuration parsing for test commands.

This module provides functionality for parsing test configuration data into
appropriate model objects, with validation and type safety.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .errors import ConfigurationError
from .models import (
    TestMetadata,
    TestEvaluation,
    TestSettings,
    TestStep,
    TestConfiguration,
    Result
)
from .types import DEFAULT_MAX_RETRIES, DEFAULT_LANGUAGE

@dataclass
class ParseResult:
    """Result of parsing configuration data.
    
    Attributes:
        metadata: Parsed metadata if present
        evaluation: Parsed evaluation if present
        steps: List of parsed test steps
        errors: List of parsing errors if any
    """
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[TestEvaluation] = None
    steps: List[TestStep] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize errors list if None."""
        if self.errors is None:
            self.errors = []
        if self.steps is None:
            self.steps = []

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
    
    def parse_configuration(self, config_data: Dict[str, Any]) -> Result[TestConfiguration]:
        """Parse configuration data into model objects.
        
        Args:
            config_data: Configuration data to parse
            
        Returns:
            Result containing parsed objects or errors
        """
        try:
            # Validate required fields
            required_fields = ['name', 'file_path']
            missing_fields = [f for f in required_fields if f not in config_data]
            if missing_fields:
                return Result.failure(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            # Parse metadata if present
            metadata = None
            if 'metadata' in config_data:
                metadata_result = self._parse_metadata(config_data['metadata'])
                if not metadata_result.is_success:
                    return Result.failure(str(metadata_result.error))
                metadata = metadata_result.value
            
            # Parse evaluation if present
            evaluation = None
            if 'evaluation' in config_data:
                evaluation_result = self._parse_evaluation(config_data['evaluation'])
                if not evaluation_result.is_success:
                    return Result.failure(str(evaluation_result.error))
                evaluation = evaluation_result.value
            
            # Parse steps if present
            steps = []
            if 'steps' in config_data:
                steps_result = self._parse_steps(config_data['steps'])
                if not steps_result.is_success:
                    return Result.failure(str(steps_result.error))
                steps = steps_result.value
            
            # Parse language from config data
            language = DEFAULT_LANGUAGE
            if 'language' in config_data:
                try:
                    from .types import Language
                    language = Language.from_str(config_data['language'])
                    
                except ValueError as e:
                    return Result.failure(f"Invalid language: {str(e)}")
            
            # Create configuration
            config = TestConfiguration(
                name=config_data['name'],
                file_path=config_data['file_path'],
                config_path=config_data.get('config_path'),
                auto_fix=config_data.get('auto_fix', False),
                create_pr=config_data.get('create_pr', False),
                max_retries=config_data.get('max_retries', DEFAULT_MAX_RETRIES),
                base_branch=config_data.get('base_branch', 'main'),
                pr_strategy=config_data.get('pr_strategy', 'ALL_PASSING'),
                description=config_data.get('description'),
                agent_type=config_data.get('agent_type'),
                regions=config_data.get('regions', []),
                steps=steps,
                metadata=metadata,
                evaluation=evaluation,
                dependencies=config_data.get('dependencies', []),
                referenced_files=config_data.get('referenced_files', []),
                files_to_fix=config_data.get('files_to_fix', []),
                language=language
            )
            
            return Result.success(config)
            
        except Exception as e:
            return Result.failure(f"Unexpected error parsing configuration: {str(e)}")
    
    def _parse_metadata(self, metadata_data: Dict[str, Any]) -> Result[TestMetadata]:
        """Parse metadata from configuration data.
        
        Args:
            metadata_data: Metadata configuration data
            
        Returns:
            Result containing parsed TestMetadata or error
        """
        try:
            if not isinstance(metadata_data, dict):
                return Result.failure("Invalid metadata format: expected a dictionary")
            
            metadata = TestMetadata(
                version=metadata_data.get('version', '1.0.0'),
                dependencies=metadata_data.get('dependencies', []),
                environment_variables=metadata_data.get('environment_variables', []),
                author=metadata_data.get('author'),
                created_at=metadata_data.get('created_at'),
                updated_at=metadata_data.get('updated_at'),
                description=metadata_data.get('description')
            )
            
            return Result.success(metadata)
            
        except Exception as e:
            return Result.failure(f"Failed to parse metadata: {str(e)}")
    
    def _parse_evaluation(self, evaluation_data: Dict[str, Any]) -> Result[TestEvaluation]:
        """Parse evaluation criteria from configuration data.
        
        Args:
            evaluation_data: Evaluation configuration data
            
        Returns:
            Result containing parsed TestEvaluation or error
        """
        try:
            if not isinstance(evaluation_data, dict):
                return Result.failure("Invalid evaluation format: expected a dictionary")
            
            evaluation = TestEvaluation.from_dict(evaluation_data)
            
            return Result.success(evaluation)
            
        except Exception as e:
            return Result.failure(f"Failed to parse evaluation: {str(e)}")

    def _parse_steps(self, steps_data: List[Dict[str, Any]]) -> Result[List[TestStep]]:
        """Parse test steps from configuration data.
        
        Args:
            steps_data: List of step configuration data
            
        Returns:
            Result containing parsed list of TestStep or error
        """
        try:
            if not isinstance(steps_data, list):
                return Result.failure("Invalid steps format: expected a list")
            
            steps = []
            for step_data in steps_data:
                try:
                    # Use TestStep.from_dict which has proper input parsing logic
                    step = TestStep.from_dict(step_data)
                    steps.append(step)
                except Exception as e:
                    return Result.failure(f"Failed to parse step '{step_data.get('name', 'Unknown')}': {str(e)}")
            
            return Result.success(steps)
            
        except Exception as e:
            return Result.failure(f"Failed to parse steps: {str(e)}") 