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

from kaizen.autofix.test.runner import TestRunner
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
    
    def __init__(self, config: TestConfiguration, logger, verbose: bool = False):
        """Initialize test all command.
        
        Args:
            config: Test configuration
            logger: Logger instance (can be CleanLogger or logging.Logger)
            verbose: Whether to show detailed debug information
        """
        super().__init__(logger)
        self.config = config
        self.verbose = verbose
        self.dependency_manager = DependencyManager()
        # Store the original logger for clean output methods
        self.clean_logger = logger if hasattr(logger, 'print_progress') else None
    
    def execute(self) -> Result[TestResult]:
        """Execute all tests.
        
        Returns:
            Result containing TestResult if successful, error otherwise
        """
        try:
            if self.verbose:
                self.logger.info(f"Running test: {self.config.name}")
                if self.config.description:
                    self.logger.info(f"Description: {self.config.description}")
            else:
                self.logger.info(f"Running test: {self.config.name}")
            
            # Validate environment before proceeding
            self._validate_environment()
            
            self.logger.info("Environment validation passed")
            
            # Import dependencies and referenced files first
            import_result = self._import_dependencies()
            if not import_result.is_success:
                return Result.failure(import_result.error)
            
            self.logger.info("Dependencies imported successfully")
            
            # Create and validate runner configuration with imported dependencies
            runner_config = self._create_runner_config(import_result.value.namespace if import_result.value else {})
            if self.verbose:
                self.logger.info("Starting test execution...")
            
            self.logger.info("Test configuration created successfully")
            
            # Execute tests - now returns unified TestExecutionResult
            self.logger.info(f"Starting test execution for: {self.config.name}")
            runner = TestRunner(runner_config, verbose=self.verbose)
            test_execution_result = runner.run_tests(self.config.file_path)
            
            if not test_execution_result:
                return Result.failure(TestExecutionError("No test results returned from runner"))
            
            self.logger.info("Test execution completed")
            
            # Handle auto-fix if enabled and tests failed
            test_attempts = None
            best_test_execution_result = test_execution_result  # Track best result after auto-fix
            if self.config.auto_fix and not test_execution_result.is_successful():
                failed_count = test_execution_result.get_failure_count()
                self.logger.info(f"Auto-fix enabled: attempting to fix {failed_count} failed tests (max retries: {self.config.max_retries})")
                fix_results = self._handle_auto_fix(test_execution_result, self.config, runner_config)
                
                if fix_results and fix_results.get('attempts'):
                    test_attempts = fix_results['attempts']
                    self.logger.info(f"Auto-fix completed: {len(test_attempts)} attempts made")
                    
                    # Get the best test results after auto-fix
                    if fix_results.get('best_test_execution_result'):
                        best_test_execution_result = fix_results['best_test_execution_result']
                        self.logger.info(f"Using best test results after auto-fix: {best_test_execution_result.get_failure_count()}/{best_test_execution_result.summary.total_tests} tests failed")
                    else:
                        # Fallback: run tests again to get the current state
                        self.logger.info("No test results found in auto-fix results, running tests again to get current state")
                        try:
                            fallback_runner = TestRunner(runner_config)
                            best_test_execution_result = fallback_runner.run_tests(self.config.file_path)
                            self.logger.info(f"Current test run results: {best_test_execution_result.get_failure_count()}/{best_test_execution_result.summary.total_tests} tests failed")
                        except Exception as e:
                            self.logger.warning(f"Failed to run current tests: {str(e)}, using original results")
                else:
                    self.logger.info("Auto-fix completed: no attempts were made")
            
            # Create TestResult object for backward compatibility
            now = datetime.now()
            
            # Determine overall status using best test results (after auto-fix if applicable)
            overall_status = 'passed' if best_test_execution_result.is_successful() else 'failed'
            
            # Show best results summary using best test results
            total_tests = best_test_execution_result.summary.total_tests
            passed_tests = best_test_execution_result.summary.passed_tests
            failed_tests = best_test_execution_result.summary.failed_tests
            self.logger.info(f"Test execution completed: {passed_tests}/{total_tests} tests passed")
            
            result = TestResult(
                name=self.config.name,
                file_path=self.config.file_path,
                config_path=self.config.config_path,
                start_time=now,
                end_time=now,
                status=overall_status,
                results=best_test_execution_result.to_legacy_format(),  # Convert to legacy format for backward compatibility
                error=None if best_test_execution_result.is_successful() else f"{best_test_execution_result.get_failure_count()} tests failed",
                steps=[],  # TODO: Add step results if available
                unified_result=best_test_execution_result,
                test_attempts=test_attempts
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
                if self.verbose:
                    self.logger.info("No dependencies or referenced files to import")
                return Result.success(ImportResult(success=True))
            
            if self.verbose:
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
            'language': self.config.language.value,
        }
        
        if self.verbose:
            self.logger.debug(f"DEBUG: Created runner config with language: {config['language']} (type: {type(config['language'])})")
            self.logger.debug(f"DEBUG: Original config language: {self.config.language} (type: {type(self.config.language)})")
            self.logger.debug(f"DEBUG: Original config language value: {self.config.language.value} (type: {type(self.config.language.value)})")
        
        # Add imported dependencies to the configuration
        if imported_namespace:
            config['imported_dependencies'] = imported_namespace
            if self.verbose:
                self.logger.info(f"Added {len(imported_namespace)} imported dependencies to runner config")
        
        # Add agent entry point if present
        if self.config.agent:
            config['agent'] = {
                'module': self.config.agent.module,
                'class': self.config.agent.class_name,
                'method': self.config.agent.method,
                'fallback_to_function': self.config.agent.fallback_to_function
            }
            if self.verbose:
                self.logger.info(f"Added agent entry point to runner config: {self.config.agent}")
        
        # Handle steps configuration
        if self.config.steps:
            if self.config.regions:
                # Create steps for each region (legacy behavior)
                config['regions'] = self.config.regions
                
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
                
                # DEBUG: Print the test configuration being created (only in verbose mode)
                if self.verbose:
                    self.logger.debug(f"DEBUG: Created {len(config['steps'])} test step(s) for runner (with regions)")
                    for i, test in enumerate(config['steps']):
                        self.logger.debug(f"DEBUG: Test {i}: {test['name']}")
                        self.logger.debug(f"DEBUG: Test {i} input: {test['input']}")
                        self.logger.debug(f"DEBUG: Test {i} method: {test['input'].get('method', 'NOT_FOUND')}")
                        self.logger.debug(f"DEBUG: Test {i} expected_output: {test.get('expected_output', 'NOT_FOUND')}")
                        self.logger.debug(f"DEBUG: Test {i} input type: {type(test['input'])}")
                        if 'input' in test['input']:
                            self.logger.debug(f"DEBUG: Test {i} nested input: {test['input']['input']}")
                            self.logger.debug(f"DEBUG: Test {i} nested input type: {type(test['input']['input'])}")
            else:
                # Direct steps configuration (new behavior)
                config['steps'] = [
                    {
                        'name': step.name,
                        'description': step.description,
                        'input': step.input,  # Use step input directly
                        'expected_output': step.expected_output,
                        'evaluation': self.config.evaluation.__dict__ if self.config.evaluation else None
                    }
                    for step in self.config.steps
                ]
                
                # DEBUG: Print the test configuration being created (only in verbose mode)
                if self.verbose:
                    self.logger.debug(f"DEBUG: Created {len(config['steps'])} test step(s) for runner (direct steps)")
                    for i, test in enumerate(config['steps']):
                        self.logger.debug(f"DEBUG: Test {i}: {test['name']}")
                        self.logger.debug(f"DEBUG: Test {i} input: {test['input']}")
                        self.logger.debug(f"DEBUG: Test {i} expected_output: {test.get('expected_output', 'NOT_FOUND')}")
                        self.logger.debug(f"DEBUG: Test {i} input type: {type(test['input'])}")
        
        return config
    
    def _handle_auto_fix(self, test_execution_result: TestExecutionResult, config: TestConfiguration, runner_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle auto-fix for failed tests.
        
        Args:
            test_execution_result: Unified test execution result
            config: Test configuration
            runner_config: Runner configuration
            
        Returns:
            Dictionary containing fix results including attempts and best test execution result, or None if no fixes were attempted
            
        Raises:
            AutoFixError: If auto-fix process fails
        """
        if self.verbose:
            self.logger.info(f"Attempting to fix {test_execution_result.get_failure_count()} failing tests (max retries: {self.config.max_retries})")
        
        try:
            # Create AutoFix instance and run fixes
            from ...autofix.main import AutoFix
            fixer = AutoFix(self.config, runner_config)
            files_to_fix = self.config.files_to_fix
            if self.verbose:
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
            
            return fix_results
            
        except Exception as e:
            self.logger.error(f"Error during auto-fix process: {str(e)}")
            raise AutoFixError(f"Failed to auto-fix tests: {str(e)}") 