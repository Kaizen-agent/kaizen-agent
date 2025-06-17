"""Test runner implementation for Kaizen."""

import os
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """Enum for test status values."""
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    ERROR = 'error'
    COMPLETED = 'completed'

@dataclass
class TestSummary:
    """Data class for test summary statistics."""
    total_regions: int = 0
    passed_regions: int = 0
    failed_regions: int = 0
    error_regions: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Convert summary to dictionary."""
        return {
            'total_regions': self.total_regions,
            'passed_regions': self.passed_regions,
            'failed_regions': self.failed_regions,
            'error_regions': self.error_regions
        }

class TestRunner:
    """A class for running tests and processing results."""
    
    def __init__(self, test_config: Dict):
        """
        Initialize the test runner.
        
        Args:
            test_config: Test configuration dictionary
        """
        self.test_config = test_config
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate the test configuration structure."""
        required_fields = ['name', 'file_path']
        for field in required_fields:
            if field not in self.test_config:
                raise ValueError(f"Missing required field '{field}' in test configuration")
        
        if 'regions' not in self.test_config and 'steps' not in self.test_config:
            raise ValueError("Test configuration must contain either 'regions' or 'steps'")
            
    def _create_error_result(self, error: Exception, context: str) -> Dict:
        """
        Create a standardized error result.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            
        Returns:
            Dict containing error information
        """
        logger.error(f"Error in {context}", extra={
            'error': str(error),
            'error_type': type(error).__name__
        })
        return {
            'status': TestStatus.ERROR.value,
            'error': str(error)
        }
        
    def _create_initial_results(self) -> Dict:
        """
        Create initial results structure.
        
        Returns:
            Dict containing initial results structure
        """
        return {
            'overall_status': {
                'status': TestStatus.PENDING.value,
                'summary': TestSummary().to_dict()
            },
            '_status': TestStatus.RUNNING.value
        }
        
    def run_tests(self, test_file_path: Path) -> Dict:
        """
        Run tests and return results.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dict containing test results
        """
        try:
            logger.info("Starting test execution", extra={
                'test_file': str(test_file_path)
            })
            
            results = self._create_initial_results()
            
            if 'regions' in self.test_config:
                self._run_region_tests(results, test_file_path)
            elif 'steps' in self.test_config:
                self._run_step_tests(results, test_file_path)
            
            self._process_overall_results(results)
            
            logger.info("Test execution completed", extra={
                'overall_status': results['overall_status']
            })
            
            return results
            
        except Exception as e:
            return self._create_error_result(e, "test execution")
            
    def _run_region_tests(self, results: Dict, test_file_path: Path) -> None:
        """
        Run tests for all regions.
        
        Args:
            results: Results dictionary to update
            test_file_path: Path to the test file
        """
        for region_name, region_config in self.test_config['regions'].items():
            try:
                region_results = self._run_region_tests_single(region_name, region_config, test_file_path)
                results[region_name] = region_results
            except Exception as e:
                results[region_name] = self._create_error_result(e, f"region {region_name}")
                
    def _run_step_tests(self, results: Dict, test_file_path: Path) -> None:
        """
        Run tests for all steps.
        
        Args:
            results: Results dictionary to update
            test_file_path: Path to the test file
        """
        for step in self.test_config['steps']:
            try:
                step_name = step.get('name', f"Step {step.get('step_index', 'Unknown')}")
                region_results = self._run_step_test(step, test_file_path)
                results[step_name] = region_results
            except Exception as e:
                results[step_name] = self._create_error_result(e, f"step {step_name}")
                
    def _run_region_tests_single(self, region_name: str, region_config: Dict, test_file_path: Path) -> Dict:
        """
        Run tests for a single region.
        
        Args:
            region_name: Name of the region
            region_config: Configuration for the region
            test_file_path: Path to the test file
            
        Returns:
            Dict containing region test results
        """
        try:
            region_results = {
                'status': TestStatus.PENDING.value,
                'test_cases': []
            }
            
            test_cases = region_config.get('test_cases', [])
            for test_case in test_cases:
                try:
                    test_result = self._run_test_case(test_case, test_file_path)
                    region_results['test_cases'].append(test_result)
                except Exception as e:
                    region_results['test_cases'].append(self._create_error_result(e, f"test case {test_case.get('name', 'Unknown')}"))
            
            self._process_region_results(region_results)
            return region_results
            
        except Exception as e:
            return self._create_error_result(e, f"region {region_name}")
            
    def _run_step_test(self, step: Dict, test_file_path: Path) -> Dict:
        """
        Run a test step.
        
        Args:
            step: Step configuration
            test_file_path: Path to the test file
            
        Returns:
            Dict containing step test results
        """
        try:
            step_results = {
                'status': TestStatus.PENDING.value,
                'test_cases': []
            }
            
            step_input = step.get('input', {})
            test_case = {
                'name': step.get('name', 'Unknown'),
                'input': {
                    'region': step_input.get('region'),
                    'method': step_input.get('method'),
                    'input': step_input.get('input')
                }
            }
            
            test_result = self._run_test_case(test_case, test_file_path)
            step_results['test_cases'].append(test_result)
            
            self._process_region_results(step_results)
            return step_results
            
        except Exception as e:
            return self._create_error_result(e, f"step {step.get('name', 'Unknown')}")
            
    def _process_overall_results(self, results: Dict) -> None:
        """
        Process overall test results.
        
        Args:
            results: Test results dictionary
        """
        try:
            summary = TestSummary()
            
            for region_name, region_result in results.items():
                if region_name in ['overall_status', '_status']:
                    continue
                    
                summary.total_regions += 1
                if isinstance(region_result, dict):
                    status = region_result.get('status', TestStatus.UNKNOWN.value)
                    if status == TestStatus.PASSED.value:
                        summary.passed_regions += 1
                    elif status == TestStatus.FAILED.value:
                        summary.failed_regions += 1
                    elif status == TestStatus.ERROR.value:
                        summary.error_regions += 1
            
            status = TestStatus.ERROR.value if summary.total_regions == 0 else \
                    TestStatus.FAILED.value if summary.failed_regions > 0 or summary.error_regions > 0 else \
                    TestStatus.PASSED.value
            
            results['overall_status'] = {
                'status': status,
                'summary': summary.to_dict()
            }
            results['_status'] = TestStatus.COMPLETED.value
            
        except Exception as e:
            results['overall_status'] = self._create_error_result(e, "overall results processing")
            results['_status'] = TestStatus.ERROR.value
    
    def _run_test_case(self, test_case: Dict, test_file_path: Path) -> Dict:
        """
        Run a single test case.
        
        Args:
            test_case: Test case configuration
            test_file_path: Path to the test file
            
        Returns:
            Dict containing test case results
        """
        try:
            # Initialize test case results
            test_result = {
                'name': test_case.get('name', 'Unknown'),
                'status': 'pending'
            }
            
            # Get test case configuration
            test_name = test_case.get('name')
            test_input = test_case.get('input', {})
            test_expected = test_case.get('expected', {})
            
            # Run the test
            try:
                # Import the test module
                import importlib.util
                spec = importlib.util.spec_from_file_location("test_module", test_file_path)
                test_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(test_module)
                
                # Get the test function
                test_func = getattr(test_module, test_name)
                
                # Run the test
                result = test_func(**test_input)
                
                # Check the result
                if self._check_test_result(result, test_expected):
                    test_result['status'] = 'passed'
                else:
                    test_result['status'] = 'failed'
                    test_result['error'] = f"Test result does not match expected output"
                    test_result['actual'] = result
                    test_result['expected'] = test_expected
                
            except Exception as e:
                test_result['status'] = 'error'
                test_result['error'] = str(e)
            
            return test_result
            
        except Exception as e:
            logger.error(f"Error running test case", extra={
                'test_case': test_case.get('name', 'Unknown'),
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {
                'name': test_case.get('name', 'Unknown'),
                'status': 'error',
                'error': str(e)
            }
    
    def _check_test_result(self, result: Any, expected: Dict) -> bool:
        """
        Check if a test result matches the expected output.
        
        Args:
            result: Actual test result
            expected: Expected test result
            
        Returns:
            bool: True if the result matches, False otherwise
        """
        try:
            # Check if result is None
            if result is None and expected.get('value') is None:
                return True
            
            # Check if result is a boolean
            if isinstance(result, bool):
                return result == expected.get('value', True)
            
            # Check if result is a string
            if isinstance(result, str):
                return result == expected.get('value', '')
            
            # Check if result is a number
            if isinstance(result, (int, float)):
                return result == expected.get('value', 0)
            
            # Check if result is a list
            if isinstance(result, list):
                expected_list = expected.get('value', [])
                if len(result) != len(expected_list):
                    return False
                return all(self._check_test_result(r, {'value': e}) 
                          for r, e in zip(result, expected_list))
            
            # Check if result is a dict
            if isinstance(result, dict):
                expected_dict = expected.get('value', {})
                if set(result.keys()) != set(expected_dict.keys()):
                    return False
                return all(self._check_test_result(result[k], {'value': expected_dict[k]})
                          for k in expected_dict)
            
            # Default case
            return False
            
        except Exception as e:
            logger.error("Error checking test result", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return False
    
    def _process_region_results(self, region_results: Dict) -> None:
        """
        Process results for a region.
        
        Args:
            region_results: Region test results
        """
        try:
            # Count test results
            total_tests = len(region_results['test_cases'])
            passed_tests = sum(1 for tc in region_results['test_cases'] 
                             if tc['status'] == 'passed')
            failed_tests = sum(1 for tc in region_results['test_cases'] 
                             if tc['status'] == 'failed')
            error_tests = sum(1 for tc in region_results['test_cases'] 
                            if tc['status'] == 'error')
            
            # Set region status
            if error_tests > 0:
                region_results['status'] = 'error'
            elif failed_tests > 0:
                region_results['status'] = 'failed'
            elif passed_tests == total_tests:
                region_results['status'] = 'passed'
            else:
                region_results['status'] = 'pending'
            
            # Add summary
            region_results['summary'] = {
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'error': error_tests
            }
            
        except Exception as e:
            logger.error("Error processing region results", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            region_results['status'] = 'error'
            region_results['error'] = str(e) 