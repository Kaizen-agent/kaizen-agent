import os
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

class TestRunner:
    """A class for running tests and processing results."""
    
    def __init__(self, test_config: Dict):
        """
        Initialize the test runner.
        
        Args:
            test_config: Test configuration dictionary
        """
        self.test_config = test_config
        
    def run_tests(self, test_file_path: Path) -> Dict:
        """
        Run tests and return results.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dict containing test results
        """
        try:
            # Log test execution start
            logger.info("Starting test execution", extra={
                'test_file': str(test_file_path)
            })
            
            # Extract test configuration
            regions = self.test_config.get('regions', {})
            steps = self.test_config.get('steps', [])
            
            # Initialize results
            results = {
                'overall_status': 'pending',
                '_status': 'running'
            }
            
            # Run tests for each region
            for region_name, region_config in regions.items():
                try:
                    # Run region tests
                    region_results = self._run_region_tests(region_name, region_config, test_file_path)
                    results[region_name] = region_results
                    
                except Exception as e:
                    logger.error(f"Error running tests for region {region_name}", extra={
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    results[region_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Process overall results
            self._process_overall_results(results)
            
            # Log test execution completion
            logger.info("Test execution completed", extra={
                'overall_status': results['overall_status']
            })
            
            return results
            
        except Exception as e:
            logger.error("Test execution failed", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {
                'overall_status': 'error',
                'error': str(e)
            }
    
    def _run_region_tests(self, region_name: str, region_config: Dict, test_file_path: Path) -> Dict:
        """
        Run tests for a specific region.
        
        Args:
            region_name: Name of the region
            region_config: Configuration for the region
            test_file_path: Path to the test file
            
        Returns:
            Dict containing region test results
        """
        try:
            # Initialize region results
            region_results = {
                'status': 'pending',
                'test_cases': []
            }
            
            # Get test cases for the region
            test_cases = region_config.get('test_cases', [])
            
            # Run each test case
            for test_case in test_cases:
                try:
                    # Run test case
                    test_result = self._run_test_case(test_case, test_file_path)
                    region_results['test_cases'].append(test_result)
                    
                except Exception as e:
                    logger.error(f"Error running test case in region {region_name}", extra={
                        'test_case': test_case.get('name', 'Unknown'),
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    region_results['test_cases'].append({
                        'name': test_case.get('name', 'Unknown'),
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Process region results
            self._process_region_results(region_results)
            
            return region_results
            
        except Exception as e:
            logger.error(f"Error processing region {region_name}", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {
                'status': 'error',
                'error': str(e)
            }
    
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
    
    def _process_overall_results(self, results: Dict) -> None:
        """
        Process overall test results.
        
        Args:
            results: Overall test results
        """
        try:
            # Count region results
            total_regions = sum(1 for k in results.keys() 
                              if k not in ('overall_status', '_status'))
            passed_regions = sum(1 for k, v in results.items() 
                               if k not in ('overall_status', '_status') 
                               and v.get('status') == 'passed')
            failed_regions = sum(1 for k, v in results.items() 
                               if k not in ('overall_status', '_status') 
                               and v.get('status') == 'failed')
            error_regions = sum(1 for k, v in results.items() 
                              if k not in ('overall_status', '_status') 
                              and v.get('status') == 'error')
            
            # Set overall status
            if error_regions > 0:
                results['overall_status'] = 'error'
            elif failed_regions > 0:
                results['overall_status'] = 'failed'
            elif passed_regions == total_regions:
                results['overall_status'] = 'passed'
            else:
                results['overall_status'] = 'pending'
            
            # Add summary
            results['summary'] = {
                'total_regions': total_regions,
                'passed_regions': passed_regions,
                'failed_regions': failed_regions,
                'error_regions': error_regions
            }
            
            # Set final status
            results['_status'] = 'completed'
            
        except Exception as e:
            logger.error("Error processing overall results", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            results['overall_status'] = 'error'
            results['error'] = str(e)
            results['_status'] = 'error' 