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
from .memory import ExecutionMemory, LLMInteraction

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
    
    def __init__(self, config: TestConfiguration, logger, verbose: bool = False, memory: ExecutionMemory = None, config_manager=None):
        """Initialize test all command.
        
        Args:
            config: Test configuration
            logger: Logger instance (can be CleanLogger or logging.Logger)
            verbose: Whether to show detailed debug information
            memory: ExecutionMemory instance for tracking execution context
            config_manager: ConfigurationManager instance (optional)
        """
        super().__init__(logger)
        self.config = config
        self.verbose = verbose
        self.memory = memory
        self.config_manager = config_manager
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
            
            # Store configuration manager information in memory if available
            if self.memory and self.config_manager:
                self._store_config_manager_in_memory()
            
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
            
            # Log test execution to memory if available
            if self.memory:
                test_metadata = {
                    'start_time': datetime.now(),
                    'config': self.config.__dict__,
                    'environment': 'test environment details'
                }
                
                # Convert test execution result to comprehensive memory format
                test_results_for_memory = self._convert_test_execution_result_to_memory_format(test_execution_result)
                
                self.memory.log_test_run(
                    file_path=str(self.config.file_path),
                    test_results=test_results_for_memory,
                    run_metadata=test_metadata
                )
            
            # Handle auto-fix if enabled and tests failed
            test_attempts = None
            best_test_execution_result = test_execution_result  # Track best result after auto-fix
            if self.config.auto_fix and not test_execution_result.is_successful():
                failed_count = test_execution_result.get_failure_count()
                self.logger.info(f"Auto-fix enabled: attempting to fix {failed_count} failed tests (max retries: {self.config.max_retries})")
                
                # Handle auto-fix with optional memory enhancement
                fix_results = self._handle_auto_fix_implementation(test_execution_result, self.config, runner_config)
                
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
                test_attempts=test_attempts,
                baseline_result=test_execution_result  # Store the baseline result (before auto-fix)
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
            'framework': self.config.framework.value,
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
    

    

    def _handle_auto_fix_implementation(self, test_execution_result: TestExecutionResult, config: TestConfiguration, runner_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle auto-fix implementation with memory-based learning when available.
        
        Args:
            test_execution_result: Unified test execution result
            config: Test configuration
            runner_config: Runner configuration
            
        Returns:
            Dictionary containing fix results including attempts and best test execution result
            
        Raises:
            AutoFixError: If auto-fix process fails
        """
        if self.verbose:
            self.logger.info(f"Attempting to fix {test_execution_result.get_failure_count()} failing tests (max retries: {self.config.max_retries})")
        
        try:
            files_to_fix = self.config.files_to_fix
            if not files_to_fix:
                raise AutoFixError("No files to fix were provided")
            
            if self.verbose:
                self.logger.info(f"Files to fix: {files_to_fix}")
            
            # Create AutoFix instance with memory when available
            from ...autofix.main import AutoFix
            fixer = AutoFix(self.config, runner_config, memory=self.memory)
            
            if self.verbose:
                if self.memory:
                    self.logger.info("Using AutoFix with memory-enhanced learning")
                else:
                    self.logger.info("Using AutoFix with standard learning")
            
            # Run fixes using AutoFix (which now handles memory internally)
            fix_results = fixer.fix_code(
                file_path=str(self.config.file_path),
                test_execution_result=test_execution_result,
                config=config,
                files_to_fix=self.config.files_to_fix,
            )
            
            return fix_results
            
        except Exception as e:
            self.logger.error(f"Error during auto-fix process: {str(e)}")
            raise AutoFixError(f"Failed to auto-fix tests: {str(e)}")
    
    def _store_config_manager_in_memory(self):
        """Store configuration manager information in memory for analysis."""
        try:
            # Get the current execution from memory
            if not self.memory.current_execution:
                self.logger.warning("No current execution in memory to store config manager info")
                return
            
            # Extract configuration manager information
            config_manager_info = {
                'config_manager_type': type(self.config_manager).__name__,
                'config_validation_status': 'validated',  # Assuming it passed validation to get here
                'config_loading_method': 'ConfigurationManager.load_configuration',
                'config_environment': {
                    'auto_fix': self.config.auto_fix,
                    'create_pr': self.config.create_pr,
                    'max_retries': self.config.max_retries,
                    'better_ai': getattr(self.config, 'better_ai', False),
                    'language': getattr(getattr(self.config, 'language', None), 'value', None),
                    'pr_strategy': getattr(self.config, 'pr_strategy', None),
                    'base_branch': getattr(self.config, 'base_branch', 'main')
                },
                'config_metadata': {
                    'config_name': getattr(self.config, 'name', None),
                    'config_file_path': getattr(self.config, 'config_path', None),
                    'files_to_fix': getattr(self.config, 'files_to_fix', []),
                    'dependencies': getattr(self.config, 'dependencies', []),
                    'referenced_files': getattr(self.config, 'referenced_files', []),
                    'agent_type': getattr(self.config, 'agent_type', None),
                    'description': getattr(self.config, 'description', None)
                }
            }
            
            # Store in memory's current execution
            self.memory.current_execution['config_manager_info'] = config_manager_info
            
            # Update the configuration context with additional config manager details
            if 'configuration_context' in self.memory.current_execution:
                self.memory.current_execution['configuration_context']['config_manager_details'] = {
                    'manager_type': config_manager_info['config_manager_type'],
                    'validation_status': config_manager_info['config_validation_status'],
                    'loading_method': config_manager_info['config_loading_method']
                }
            
            self.logger.info(f"Stored configuration manager information in memory: {config_manager_info['config_manager_type']}")
            
        except Exception as e:
            self.logger.warning(f"Failed to store configuration manager information in memory: {str(e)}")
    
    def _convert_test_execution_result_to_memory_format(self, test_execution_result: TestExecutionResult) -> Dict[str, Any]:
        """Convert TestExecutionResult to comprehensive memory format capturing all valuable information.
        
        Args:
            test_execution_result: The unified test execution result
            
        Returns:
            Dictionary containing all test execution data in memory format
        """
        try:
            # Convert individual test cases with full details
            test_cases_for_memory = []
            for test_case in test_execution_result.test_cases:
                test_case_data = {
                    'name': test_case.name,
                    'status': test_case.status.value if hasattr(test_case.status, 'value') else str(test_case.status),
                    'input': test_case.input,
                    'expected_output': test_case.expected_output,
                    'actual_output': test_case.actual_output,
                    'error_message': test_case.error_message,
                    'error_details': test_case.error_details,
                    'evaluation': test_case.evaluation,
                    'evaluation_score': test_case.evaluation_score,
                    'execution_time': test_case.execution_time,
                    'timestamp': test_case.timestamp.isoformat() if test_case.timestamp else None,
                    'metadata': test_case.metadata,
                    'is_failed': test_case.is_failed() if hasattr(test_case, 'is_failed') else test_case.status in ['failed', 'error'],
                    'is_passed': test_case.is_passed() if hasattr(test_case, 'is_passed') else test_case.status == 'passed',
                    'error_summary': test_case.get_error_summary() if hasattr(test_case, 'get_error_summary') else test_case.error_message
                }
                test_cases_for_memory.append(test_case_data)
            
            # Convert summary with detailed statistics
            summary_data = {
                'total_tests': test_execution_result.summary.total_tests,
                'passed_tests': test_execution_result.summary.passed_tests,
                'failed_tests': test_execution_result.summary.failed_tests,
                'error_tests': test_execution_result.summary.error_tests,
                'skipped_tests': test_execution_result.summary.skipped_tests,
                'success_rate': test_execution_result.summary.get_success_rate() if hasattr(test_execution_result.summary, 'get_success_rate') else 0.0,
                'is_successful': test_execution_result.summary.is_successful(),
                'start_time': test_execution_result.summary.start_time.isoformat() if test_execution_result.summary.start_time else None,
                'end_time': test_execution_result.summary.end_time.isoformat() if test_execution_result.summary.end_time else None,
                'total_execution_time': test_execution_result.summary.total_execution_time
            }
            
            # Convert overall result information
            result_data = {
                'name': test_execution_result.name,
                'file_path': str(test_execution_result.file_path),
                'config_path': str(test_execution_result.config_path),
                'status': test_execution_result.status.value if hasattr(test_execution_result.status, 'value') else str(test_execution_result.status),
                'error_message': test_execution_result.error_message,
                'error_details': test_execution_result.error_details,
                'start_time': test_execution_result.start_time.isoformat() if test_execution_result.start_time else None,
                'end_time': test_execution_result.end_time.isoformat() if test_execution_result.end_time else None,
                'metadata': test_execution_result.metadata,
                'is_successful': test_execution_result.is_successful(),
                'get_failure_count': test_execution_result.get_failure_count(),
                'get_failed_tests_count': len(test_execution_result.get_failed_tests()) if hasattr(test_execution_result, 'get_failed_tests') else 0,
                'get_passed_tests_count': len(test_execution_result.get_passed_tests()) if hasattr(test_execution_result, 'get_passed_tests') else 0
            }
            
            # Legacy compatibility methods (if available)
            legacy_inputs = []
            legacy_outputs = []
            llm_logs = {}
            
            if hasattr(test_execution_result, 'get_test_inputs'):
                try:
                    legacy_inputs = test_execution_result.get_test_inputs()
                except Exception as e:
                    self.logger.debug(f"Could not get test inputs: {e}")
            
            if hasattr(test_execution_result, 'get_test_outputs'):
                try:
                    legacy_outputs = test_execution_result.get_test_outputs()
                except Exception as e:
                    self.logger.debug(f"Could not get test outputs: {e}")
            
            if hasattr(test_execution_result, 'get_llm_logs'):
                try:
                    llm_logs = test_execution_result.get_llm_logs()
                except Exception as e:
                    self.logger.debug(f"Could not get LLM logs: {e}")
            
            if hasattr(test_execution_result, 'get_evaluation_results'):
                try:
                    evaluation_results = test_execution_result.get_evaluation_results()
                except Exception as e:
                    self.logger.debug(f"Could not get evaluation results: {e}")
                    evaluation_results = None
            else:
                evaluation_results = None
            
            # Build comprehensive memory format
            memory_format = {
                # Individual test cases with full details
                'test_cases': test_cases_for_memory,
                
                # Summary statistics
                'summary': summary_data,
                
                # Overall result information
                'result': result_data,
                
                # Legacy compatibility
                'inputs': legacy_inputs,
                'outputs': legacy_outputs,
                'llm_logs': llm_logs,
                'evaluation_results': evaluation_results,
                
                # Attempt tracking
                'code_fix_attempt': None,  # Will be populated during auto-fix
                'attempt_outcome': {
                    'success': test_execution_result.is_successful(),
                    'total_tests': test_execution_result.summary.total_tests,
                    'passed_tests': test_execution_result.summary.passed_tests,
                    'failed_tests': test_execution_result.summary.failed_tests,
                    'error_tests': test_execution_result.summary.error_tests,
                    'skipped_tests': test_execution_result.summary.skipped_tests,
                    'success_rate': summary_data['success_rate'],
                    'failure_count': test_execution_result.get_failure_count()
                },
                
                # Additional analysis data
                'failed_test_cases': [
                    tc for tc in test_cases_for_memory 
                    if tc['is_failed']
                ],
                'passed_test_cases': [
                    tc for tc in test_cases_for_memory 
                    if tc['is_passed']
                ],
                'error_test_cases': [
                    tc for tc in test_cases_for_memory 
                    if tc['status'] in ['error', 'failed']
                ],
                
                # Timing analysis
                'timing_analysis': {
                    'total_execution_time': summary_data['total_execution_time'],
                    'average_test_time': (
                        summary_data['total_execution_time'] / summary_data['total_tests']
                        if summary_data['total_tests'] > 0 and summary_data['total_execution_time']
                        else None
                    ),
                    'start_time': summary_data['start_time'],
                    'end_time': summary_data['end_time']
                },
                
                # Error analysis
                'error_analysis': {
                    'total_errors': len([tc for tc in test_cases_for_memory if tc['error_message']]),
                    'unique_error_types': list(set([
                        tc['error_message'] for tc in test_cases_for_memory 
                        if tc['error_message']
                    ])),
                    'most_common_error': self._get_most_common_error(test_cases_for_memory)
                }
            }
            
            if self.verbose:
                self.logger.debug(f"Converted TestExecutionResult to memory format with {len(test_cases_for_memory)} test cases")
            
            return memory_format
            
        except Exception as e:
            self.logger.error(f"Error converting TestExecutionResult to memory format: {str(e)}")
            # Fallback to basic format
            return {
                'inputs': [],
                'outputs': [],
                'llm_logs': {},
                'code_fix_attempt': None,
                'attempt_outcome': {
                    'success': test_execution_result.is_successful() if hasattr(test_execution_result, 'is_successful') else False,
                    'total_tests': getattr(test_execution_result.summary, 'total_tests', 0),
                    'passed_tests': getattr(test_execution_result.summary, 'passed_tests', 0),
                    'failed_tests': getattr(test_execution_result.summary, 'failed_tests', 0)
                },
                'evaluation_results': None,
                'error': f"Failed to convert test execution result: {str(e)}"
            }
    
    def _get_most_common_error(self, test_cases: List[Dict]) -> Optional[str]:
        """Get the most common error message from test cases.
        
        Args:
            test_cases: List of test case dictionaries
            
        Returns:
            Most common error message or None if no errors
        """
        error_counts = {}
        for test_case in test_cases:
            if test_case.get('error_message'):
                error_msg = test_case['error_message']
                error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
        
        if not error_counts:
            return None
        
        return max(error_counts.items(), key=lambda x: x[1])[0] 