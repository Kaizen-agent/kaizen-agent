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
from .errors import TestExecutionError, AutoFixError
from .types import TestStatus, PRStrategy
from ...autofix.main import AutoFix, FixStatus

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
    
    def execute(self) -> Result[TestResult]:
        """Execute all tests.
        
        Returns:
            Result containing TestResult if successful, error otherwise
        """
        try:
            self.logger.info(f"Running test: {self.config.name}")
            if self.config.description:
                self.logger.info(f"Description: {self.config.description}")
            
            # Create and validate runner configuration
            runner_config = self._create_runner_config()
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
                test_attempts = self._handle_auto_fix(failed_tests)
            
            result = TestResult(
                name=self.config.name,
                file_path=self.config.file_path,
                config_path=self.config.config_path,
                results=results,
                failed_tests=failed_tests,
                test_attempts=test_attempts
            )
            
            validation_result = result.validate()
            if not validation_result.is_success:
                return Result.failure(validation_result.error)
            
            return Result.success(result)
            
        except Exception as e:
            self.logger.error(f"Error executing tests: {str(e)}")
            return Result.failure(TestExecutionError(f"Failed to execute tests: {str(e)}"))
    
    def _create_runner_config(self) -> Dict[str, Any]:
        """Create configuration for test runner.
        
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
    
    def _handle_auto_fix(self, failed_tests: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
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
            fixer = AutoFix(self.config)
            fix_results = fixer.fix_code(
                file_path=str(self.config.file_path),
                failure_data=failed_tests
            )
            
            # Process and return attempts
            attempts = fix_results.get('attempts', [])
            if not attempts:
                self.logger.warning("No fix attempts were made")
                return None
                
            # Log results of each attempt
            for attempt in attempts:
                status = attempt.get('status', 'unknown')
                attempt_num = attempt.get('attempt_number', 'unknown')
                self.logger.info(f"Attempt {attempt_num}: {status}")
                
                if status == FixStatus.SUCCESS.name:
                    self.logger.info("Successfully fixed all failing tests!")
                    if self.config.settings.create_pr:
                        pr_data = fix_results.get('pr')
                        if pr_data:
                            self.logger.info(f"Created pull request: {pr_data.get('url', 'Unknown URL')}")
                elif status == FixStatus.FAILED.name:
                    self.logger.warning("Failed to fix all tests after all attempts")
                elif status == FixStatus.ERROR.name:
                    error = attempt.get('error', 'Unknown error')
                    self.logger.error(f"Error during fix attempt: {error}")
            
            return attempts
            
        except Exception as e:
            self.logger.error(f"Error during auto-fix process: {str(e)}")
            raise AutoFixError(f"Failed to auto-fix tests: {str(e)}") 