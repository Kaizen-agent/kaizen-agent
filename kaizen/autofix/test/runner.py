"""Test runner implementation for Kaizen."""

import os
import sys
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from .test_case import TestCase, TestStatus, LLMEvaluator, AssertionRunner
from .code_region import CodeRegionExtractor, CodeRegionExecutor

# Configure logging
logger = logging.getLogger(__name__)

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
        self.workspace_root = self._find_workspace_root()
        self.config_file_path = Path(test_config.get('config_file', ''))
        self.code_region_extractor = CodeRegionExtractor()
        self.code_region_executor = CodeRegionExecutor(self.workspace_root)
        self.llm_evaluator = LLMEvaluator()
        self.assertion_runner = AssertionRunner()
        
    
    
    def _validate_config(self) -> None:
        """Validate the test configuration structure."""
        required_fields = ['name', 'file_path']
        for field in required_fields:
            if field not in self.test_config:
                raise ValueError(f"Missing required field '{field}' in test configuration")
        
        if 'tests' not in self.test_config:
            raise ValueError("Test configuration must contain 'tests' field")
    
    def _find_workspace_root(self) -> Path:
        """Find the workspace root directory."""
        current = Path.cwd()
        while current.name != 'kaizen-agent' and current.parent != current:
            current = current.parent
        if current.name != 'kaizen-agent':
            raise ValueError("Could not find workspace root directory")
        return current
    
    def _run_test_case(self, test_case: Dict, test_file_path: Path) -> Dict:
        """
        Run a single test case with proper assertions and LLM evaluation.
        
        Args:
            test_case: Test case configuration
            test_file_path: Path to the test file
            
        Returns:
            Dict containing test case results
        """
        try:
            logger.info(f"Running test case: {test_case.get('name', 'Unknown')}")
            # Convert test case dict to TestCase object
            test_case_obj = TestCase.from_dict(test_case)
            
            # Extract and analyze the code region
            region_info = self.code_region_extractor.extract_region(
                test_file_path, 
                test_case_obj.input['region']
            )
            
            # Add imports from test case to region info
            if 'imports' in test_case_obj.input:
                region_info.imports.extend(test_case_obj.input['imports'])
            
            # Execute the code region
            actual_output = self.code_region_executor.execute_region(
                region_info,
                test_case_obj.input.get('method'),
                test_case_obj.input.get('input')
            )
            
            # Run assertions
            assertion_results = self.assertion_runner.run_assertions(
                test_case_obj.assertions, 
                actual_output
            )
            
            # Evaluate with LLM
            llm_evaluation = self.llm_evaluator.evaluate_result(test_case_obj, actual_output)
            
            # Determine overall test status
            status = self._determine_test_status(assertion_results, llm_evaluation)
            
            # Combine results
            return {
                'status': status,
                'input': test_case_obj.input,
                'output': actual_output,
                'assertions': assertion_results,
                'llm_evaluation': llm_evaluation,
                'expected_output': test_case_obj.expected_output,
                'region_info': {
                    'type': region_info.type.value,
                    'name': region_info.name,
                    'methods': region_info.class_methods
                }
            }
            
        except Exception as e:
            logger.error(f"Error in test case {test_case.get('name', 'Unknown')}: {str(e)}")
            return {
                'status': TestStatus.ERROR.value,
                'error': str(e)
            }
    
    def _determine_test_status(self, assertion_results: List[Dict], llm_evaluation: Dict) -> str:
        """Determine the overall test status based on assertions and LLM evaluation."""
        # Check if any assertions failed
        if any(not result['passed'] for result in assertion_results):
            return TestStatus.FAILED.value
        
        # Check LLM evaluation status
        if llm_evaluation.get('status') == TestStatus.FAILED.value:
            return TestStatus.FAILED.value
        
        return TestStatus.PASSED.value
    
    def run_tests(self, test_file_path: Path) -> Dict:
        """
        Run tests and return results.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dict containing test results
        """
        results = self._create_initial_results()
        summary = TestSummary()
        
        try:
            # Resolve the file path relative to config file location
            if self.config_file_path:
                resolved_path = self.config_file_path.parent / test_file_path
            else:
                resolved_path = test_file_path
                
            if not resolved_path.exists():
                raise FileNotFoundError(f"Test file not found: {resolved_path}")
            
            logger.info(f"Running tests: {self.test_config.get('tests', [])}")
            for test_case in self.test_config.get('tests', []):
                logger.info(f"Running test case: {test_case.get('name', 'Unknown')}")
                test_name = test_case.get('name', 'Unknown')
                test_result = self._run_test_case(test_case, resolved_path)
                logger.info(f"Test result: {test_result}")
                results[test_name] = self._create_test_result(test_result)
                
                summary.total_regions += 1
                if test_result['status'] == TestStatus.PASSED.value:
                    summary.passed_regions += 1
                elif test_result['status'] == TestStatus.FAILED.value:
                    summary.failed_regions += 1
                else:
                    summary.error_regions += 1
            
            results['overall_status'] = {
                'status': TestStatus.COMPLETED.value,
                'summary': summary.to_dict()
            }
            results['_status'] = TestStatus.COMPLETED.value
            
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            results['overall_status'] = {
                'status': TestStatus.FAILED.value,
                'summary': summary.to_dict()
            }
            results['_status'] = TestStatus.ERROR.value
        
        return results

    def _create_initial_results(self) -> Dict:
        """Create initial results structure."""
        return {
            'overall_status': {
                'status': TestStatus.PENDING.value,
                'summary': TestSummary().to_dict()
            },
            '_status': TestStatus.RUNNING.value
        }

    def _create_test_result(self, test_result: Dict) -> Dict:
        """
        Create a structured test result dictionary.
        
        Args:
            test_result: Raw test result dictionary
            
        Returns:
            Dict containing structured test result
        """
        return {
            'status': test_result['status'],
            'test_cases': [{
                'status': test_result['status'],
                'input': test_result.get('input'),
                'output': test_result.get('output'),
                'assertions': test_result.get('assertions', []),
                'llm_evaluation': test_result.get('llm_evaluation', {}),
                'expected_output': test_result.get('expected_output'),
                'region_info': test_result.get('region_info', {}),
                'error': test_result.get('error')
            }],
            'summary': {
                'total': 1,
                'passed': 1 if test_result['status'] == TestStatus.PASSED.value else 0,
                'failed': 1 if test_result['status'] == TestStatus.FAILED.value else 0,
                'error': 1 if test_result['status'] == TestStatus.ERROR.value else 0
            }
        } 