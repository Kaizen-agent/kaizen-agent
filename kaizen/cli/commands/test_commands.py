"""Test command implementations for Kaizen CLI.

This module provides the core command implementations for running tests in Kaizen.
It includes the base command interface and concrete implementations for different
test execution strategies. The module handles test execution, result collection,
and auto-fix functionality.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from abc import ABC, abstractmethod
from datetime import datetime

from ...autofix.test.runner import TestRunner
from ...utils.test_utils import get_failed_tests_dict_from_unified
from .models import TestConfiguration, TestResult, Result, TestExecutionResult, TestStatus
from .errors import TestExecutionError, AutoFixError, DependencyError
from .types import TestStatus as LegacyTestStatus, PRStrategy
from .dependency_manager import DependencyManager, ImportResult
from kaizen.cli.utils.env_setup import check_environment_setup, get_missing_variables

@runtime_checkable
class TestCommand(Protocol):
    """Protocol for test commands."""
    
    def execute(self) -> Result[TestResult]:
        """Execute the test command.
        
        Returns:
            Result containing TestResult if successful, error otherwise
        """
        ...

class BaseTestCommand(ABC):
    """Base class for test commands."""
    
    def __init__(self, logger: logging.Logger):
        """Initialize base test command.
        
        Args:
            logger: Logger instance for command execution
        """
        self.logger = logger
    
    @abstractmethod
    def execute(self) -> Result[TestResult]:
        """Execute the test command.
        
        Returns:
            Result containing TestResult if successful, error otherwise
        """
        pass

class TestAllCommand(BaseTestCommand):
    """Command to run all tests."""
    
    def __init__(self, config: TestConfiguration, logger: logging.Logger):
        """Initialize test all command.
        
        Args:
            config: Test configuration
            logger: Logger instance for command execution
        """
        super().__init__(logger)
        self.config = config
        self.dependency_manager = DependencyManager()
    
    def execute(self) -> Result[TestResult]:
        """Execute all tests.
        
        Returns:
            Result containing TestResult if successful, error otherwise
        """
        try:
            self.logger.info(f"Running test: {self.config.name}")
            if self.config.description:
                self.logger.info(f"Description: {self.config.description}")
            
            # Validate environment before proceeding
            self._validate_environment()
            
            # Import dependencies and referenced files first
            import_result = self._import_dependencies()
            if not import_result.is_success:
                return Result.failure(import_result.error)
            
            self.logger.info("Dependencies imported successfully")
            
            # Create and validate runner configuration with imported dependencies
            runner_config = self._create_runner_config(import_result.value.namespace if import_result.value else {})
            self.logger.info("Starting test execution...")
            
            # Execute tests - now returns unified TestExecutionResult
            runner = TestRunner(runner_config)
            test_execution_result = runner.run_tests(self.config.file_path)
            
            if not test_execution_result:
                return Result.failure(TestExecutionError("No test results returned from runner"))
            
            self.logger.info("Test execution completed")
            
            # Handle auto-fix if enabled and tests failed
            test_attempts = None
            if self.config.auto_fix and not test_execution_result.is_successful():
                self.logger.info(f"Found {test_execution_result.get_failure_count()} failed tests")
                test_attempts = self._handle_auto_fix(test_execution_result, self.config, runner_config)
            
            # Create TestResult object for backward compatibility
            now = datetime.now()
            
            # Determine overall status
            overall_status = 'passed' if test_execution_result.is_successful() else 'failed'
            
            result = TestResult(
                name=self.config.name,
                file_path=self.config.file_path,
                config_path=self.config.config_path,
                start_time=now,
                end_time=now,
                status=overall_status,
                results=test_execution_result.to_legacy_format(),  # Convert to legacy format for backward compatibility
                error=None if test_execution_result.is_successful() else f"{test_execution_result.get_failure_count()} tests failed",
                steps=[]  # TODO: Add step results if available
            )
            
            return Result.success(result)
            
        except Exception as e:
            self.logger.error(f"Error executing tests: {str(e)}")
            return Result.failure(TestExecutionError(f"Failed to execute tests: {str(e)}"))
        finally:
            # Clean up dependency manager
            self.dependency_manager.cleanup()
    
    def _validate_environment(self) -> None:
        """Validate environment setup before proceeding.
        
        Raises:
            TestExecutionError: If environment is not properly configured
        """
        # Determine required features based on configuration
        required_features = ['core']  # Core is always required
        
        if self.config.create_pr:
            required_features.append('github')
        
        # Check environment setup
        if not check_environment_setup(required_features=required_features):
            missing_vars = get_missing_variables(required_features)
            error_msg = f"Environment is not properly configured. Missing variables: {', '.join(missing_vars)}"
            error_msg += "\n\nRun 'kaizen setup check-env' to see detailed status and setup instructions."
            error_msg += "\nRun 'kaizen setup create-env-example' to create a .env.example file."
            raise TestExecutionError(error_msg)
    
    def _import_dependencies(self) -> Result[ImportResult]:
        """Import dependencies and referenced files.
        
        Returns:
            Result containing import result or error
        """
        try:
            if not self.config.dependencies and not self.config.referenced_files:
                self.logger.info("No dependencies or referenced files to import")
                return Result.success(ImportResult(success=True))
            
            self.logger.info(f"Importing {len(self.config.dependencies)} dependencies and {len(self.config.referenced_files)} referenced files")
            
            import_result = self.dependency_manager.import_dependencies(
                dependencies=self.config.dependencies,
                referenced_files=self.config.referenced_files,
                config_path=self.config.config_path
            )
            
            if not import_result.is_success:
                return import_result
            
            if not import_result.value.success:
                # Log warnings for failed imports but don't fail the test
                for error in import_result.value.errors:
                    self.logger.warning(f"Dependency import warning: {error}")
            
            return import_result
            
        except Exception as e:
            self.logger.error(f"Error importing dependencies: {str(e)}")
            return Result.failure(DependencyError(f"Failed to import dependencies: {str(e)}"))
    
    def _create_runner_config(self, imported_namespace: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create configuration for test runner.
        
        Args:
            imported_namespace: Dictionary containing imported modules and dependencies
            
        Returns:
            Dictionary containing runner configuration
        """
        config = {
            'name': self.config.name,
            'file_path': str(self.config.file_path),
            'config_file': str(self.config.config_path),
            'agent_type': self.config.agent_type,
            'description': self.config.description,
            'metadata': self.config.metadata.__dict__ if self.config.metadata else None,
        }
        
        # Add imported dependencies to the configuration
        if imported_namespace:
            config['imported_dependencies'] = imported_namespace
            self.logger.info(f"Added {len(imported_namespace)} imported dependencies to runner config")
        
        if self.config.regions:
            config['regions'] = self.config.regions
            
            # Create steps for each region
            config_steps_temp = []
            for region in self.config.regions:
                config_steps_temp.append([
                    {
                        'name': step.name,
                        'description': step.description,
                        'input': {
                            'file_path': str(self.config.file_path),
                            'region': region,
                            'method': step.command,
                            'input': step.input  # This now supports multiple inputs
                        },
                        'expected_output': step.expected_output,
                        'evaluation': self.config.evaluation.__dict__ if self.config.evaluation else None
                    }
                    for step in self.config.steps
                ])
            config['steps'] = [item for sublist in config_steps_temp for item in sublist]
            
            # DEBUG: Print the test configuration being created
            self.logger.info(f"DEBUG: Created {len(config['steps'])} test step(s) for runner")
            for i, test in enumerate(config['steps']):
                self.logger.info(f"DEBUG: Test {i}: {test['name']}")
                self.logger.info(f"DEBUG: Test {i} input: {test['input']}")
                self.logger.info(f"DEBUG: Test {i} method: {test['input'].get('method', 'NOT_FOUND')}")
                self.logger.info(f"DEBUG: Test {i} expected_output: {test.get('expected_output', 'NOT_FOUND')}")
                self.logger.info(f"DEBUG: Test {i} input type: {type(test['input'])}")
                if 'input' in test['input']:
                    self.logger.info(f"DEBUG: Test {i} nested input: {test['input']['input']}")
                    self.logger.info(f"DEBUG: Test {i} nested input type: {type(test['input']['input'])}")
            
        return config
    
    def _handle_auto_fix(self, test_execution_result: TestExecutionResult, config: TestConfiguration, runner_config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Handle auto-fix for failed tests.
        
        Args:
            test_execution_result: Unified test execution result
            config: Test configuration
            runner_config: Runner configuration
            
        Returns:
            List of fix attempts if any were made, None otherwise
            
        Raises:
            AutoFixError: If auto-fix process fails
        """
        self.logger.info(f"Attempting to fix {test_execution_result.get_failure_count()} failing tests (max retries: {self.config.max_retries})")
        
        try:
            # Create AutoFix instance and run fixes
            from ...autofix.main import AutoFix
            fixer = AutoFix(self.config, runner_config)
            files_to_fix = self.config.files_to_fix
            self.logger.info(f"Files to fix: {files_to_fix}")
            if files_to_fix:
                fix_results = fixer.fix_code(
                    file_path=str(self.config.file_path),
                    test_execution_result=test_execution_result,  # Pass unified result directly
                    config=config,
                    files_to_fix=files_to_fix,
                )
            else:
                raise AutoFixError("No files to fix were provided")
            
            # Process and return attempts
            attempts = fix_results.get('attempts', [])
            if not attempts:
                self.logger.warning("No fix attempts were made")
                return None
                
            
            return attempts
            
        except Exception as e:
            self.logger.error(f"Error during auto-fix process: {str(e)}")
            raise AutoFixError(f"Failed to auto-fix tests: {str(e)}") 