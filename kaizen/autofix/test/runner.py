"""Test runner implementation for Kaizen."""

import os
import sys
import logging
import yaml
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager

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
    UNKNOWN = 'unknown'

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

class RegionType(Enum):
    """Types of code regions that can be tested."""
    CLASS = 'class'
    FUNCTION = 'function'
    MODULE = 'module'

@dataclass
class RegionInfo:
    """Information about a code region."""
    type: RegionType
    name: str
    code: str
    start_line: int
    end_line: int
    imports: List[str]

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
    
    def _parse_region_code(self, code: str) -> RegionInfo:
        """
        Parse region code to determine its type and structure.
        
        Args:
            code: The code to parse
            
        Returns:
            RegionInfo object containing parsed information
            
        Raises:
            ValueError: If code cannot be parsed or is invalid
        """
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Find all imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            imports.append(name.name)
                    else:
                        module = node.module or ''
                        for name in node.names:
                            imports.append(f"{module}.{name.name}")
            
            # Determine region type
            region_type = None
            region_name = None
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    region_type = RegionType.CLASS
                    region_name = node.name
                    break
                elif isinstance(node, ast.FunctionDef):
                    region_type = RegionType.FUNCTION
                    region_name = node.name
                    break
            
            if not region_type:
                region_type = RegionType.MODULE
                region_name = "module"
            
            return RegionInfo(
                type=region_type,
                name=region_name,
                code=code,
                start_line=tree.body[0].lineno if tree.body else 1,
                end_line=tree.body[-1].end_lineno if tree.body else 1,
                imports=imports
            )
            
        except SyntaxError as e:
            raise ValueError(f"Invalid Python code in region: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse region code: {str(e)}")

    def _extract_region_code(self, file_path: Path, region_name: str) -> RegionInfo:
        """
        Extract code for a specific region from a file.
        
        Args:
            file_path: Path to the file
            region_name: Name of the region to extract
            
        Returns:
            RegionInfo object containing the extracted code and metadata
            
        Raises:
            ValueError: If region markers are not found or code is invalid
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            start_marker = f"# kaizen:start:{region_name}"
            end_marker = f"# kaizen:end:{region_name}"
            
            start_idx = content.find(start_marker)
            if start_idx == -1:
                raise ValueError(f"Start marker for region '{region_name}' not found")
                
            end_idx = content.find(end_marker)
            if end_idx == -1:
                raise ValueError(f"End marker for region '{region_name}' not found")
                
            # Extract code between markers (excluding the markers themselves)
            start_idx = content.find('\n', start_idx) + 1
            code = content[start_idx:end_idx].strip()
            
            # Parse the region code
            return self._parse_region_code(code)
            
        except Exception as e:
            raise ValueError(f"Failed to extract region '{region_name}': {str(e)}")

    @contextmanager
    def _create_safe_namespace(self, imports: List[str]) -> Dict:
        """
        Create a safe namespace for code execution.
        
        Args:
            imports: List of imports to include
            
        Yields:
            Dict containing the safe namespace
        """
        # Create a new namespace
        namespace = {}
        
        # Add allowed imports
        for imp in imports:
            try:
                if '.' in imp:
                    module_name, attr_name = imp.rsplit('.', 1)
                    module = importlib.import_module(module_name)
                    namespace[attr_name] = getattr(module, attr_name)
                else:
                    namespace[imp] = importlib.import_module(imp)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to import {imp}: {str(e)}")
        
        yield namespace

    def _create_region_function(self, region_info: RegionInfo, method_name: str) -> Callable:
        """
        Create a function from region code.
        
        Args:
            region_info: Information about the region
            method_name: Name of the method to call
            
        Returns:
            callable: The created function
            
        Raises:
            ValueError: If function creation fails
        """
        try:
            with self._create_safe_namespace(region_info.imports) as namespace:
                # Execute the code in the safe namespace
                exec(region_info.code, namespace)
                
                if region_info.type == RegionType.CLASS:
                    # Get the class and create an instance
                    test_class = namespace[region_info.name]
                    if not hasattr(test_class, method_name):
                        raise ValueError(f"Method '{method_name}' not found in class '{region_info.name}'")
                    instance = test_class()
                    return getattr(instance, method_name)
                    
                elif region_info.type == RegionType.FUNCTION:
                    # Get the function directly
                    if region_info.name != method_name:
                        raise ValueError(f"Function name '{region_info.name}' does not match requested method '{method_name}'")
                    return namespace[region_info.name]
                    
                else:  # MODULE
                    # Get the function from the module
                    if not hasattr(namespace, method_name):
                        raise ValueError(f"Function '{method_name}' not found in module")
                    return getattr(namespace, method_name)
                
        except Exception as e:
            raise ValueError(f"Failed to create function from region '{region_info.name}': {str(e)}")
            
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
                'status': TestStatus.PENDING.value
            }
            
            # Get test case configuration
            test_input = test_case.get('input', {})
            if not isinstance(test_input, dict):
                raise ValueError(f"Invalid test input format: {test_input}")
                
            region = test_input.get('region')
            method = test_input.get('method')
            input_text = test_input.get('input')
            
            if not all([region, method]):
                raise ValueError(f"Missing required test input fields: region={region}, method={method}")
            
            # Extract and create the test function
            region_info = self._extract_region_code(test_file_path, region)
            test_function = self._create_region_function(region_info, method)
            
            # Run the test
            result = test_function(input_text)
            
            # Check the result
            test_result['status'] = TestStatus.PASSED.value
            test_result['output'] = result
            
            return test_result
            
        except Exception as e:
            return self._create_error_result(e, f"test case {test_case.get('name', 'Unknown')}")
    
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