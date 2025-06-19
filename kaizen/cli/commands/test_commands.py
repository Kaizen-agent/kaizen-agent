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

from ...autofix.test.runner import TestRunner
from ...utils.test_utils import collect_failed_tests
from .models import TestConfiguration, TestResult, Result
from .errors import TestExecutionError, AutoFixError, DependencyError
from .types import TestStatus, PRStrategy
from ...autofix.main import AutoFix, FixStatus
from .dependency_manager import DependencyManager, ImportResult

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
            
            # Import dependencies and referenced files first
            import_result = self._import_dependencies()
            if not import_result.is_success:
                return Result.failure(import_result.error)
            
            self.logger.info("Dependencies imported successfully")
            
            # Create and validate runner configuration with imported dependencies
            runner_config = self._create_runner_config(import_result.value.namespace if import_result.value else {})
            self.logger.info("Starting test execution...")
            
            # Execute tests
            runner = TestRunner(runner_config)
            results = runner.run_tests(self.config.file_path)
            
            if not results:
                return Result.failure(TestExecutionError("No test results returned from runner"))
            
            self.logger.info("Test execution completed")
            failed_tests = collect_failed_tests(results)
            
            # Handle auto-fix if enabled
            test_attempts = None
            if self.config.auto_fix and failed_tests:
                self.logger.info(f"Found {len(failed_tests)} failed tests")
                test_attempts = self._handle_auto_fix(failed_tests, self.config, runner_config)
            
            # result = TestResult(
            #     name=self.config.name,
            #     file_path=self.config.file_path,
            #     config_path=self.config.config_path,
            #     results=results,
            #     failed_tests=failed_tests,
            #     test_attempts=test_attempts
            # )
            
            # validation_result = result.validate()
            # if not validation_result.is_success:
            #     return Result.failure(validation_result.error)
            
            # return 
            return "test"
            
        except Exception as e:
            self.logger.error(f"Error executing tests: {str(e)}")
            return Result.failure(TestExecutionError(f"Failed to execute tests: {str(e)}"))
        finally:
            # Clean up dependency manager
            self.dependency_manager.cleanup()
    
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
            
            # Create tests for each region
            config_tests_temp = []
            for region in self.config.regions:
                config_tests_temp.append([
                    {
                        'name': step.name,
                        'description': step.description,
                        'input': {
                            'file_path': str(self.config.file_path),
                            'region': region,
                            'method': step.command if hasattr(step, 'command') else None,
                            'input': step.input
                        },
                        'evaluation': self.config.evaluation.__dict__ if self.config.evaluation else None
                    }
                    for step in self.config.steps
                ])
            config['tests'] = [item for sublist in config_tests_temp for item in sublist]
            
        return config
    
    def _handle_auto_fix(self, failed_tests: List[Dict[str, Any]], config: TestConfiguration, runner_config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Handle auto-fix for failed tests.
        
        Args:
            failed_tests: List of failed tests to fix
            
        Returns:
            List of fix attempts if any were made, None otherwise
            
        Raises:
            AutoFixError: If auto-fix process fails
        """
        if not failed_tests:
            return None
            
        self.logger.info(f"Attempting to fix {len(failed_tests)} failing tests (max retries: {self.config.max_retries})")
        
        try:
            # Create AutoFix instance and run fixes
            fixer = AutoFix(self.config, runner_config)
            files_to_fix = self.config.files_to_fix
            self.logger.info(f"Files to fix: {files_to_fix}")
            if files_to_fix:
                fix_results = fixer.fix_code(
                    file_path=str(self.config.file_path),
                    failure_data=failed_tests,
                    files_to_fix=files_to_fix,
                    config=config,
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