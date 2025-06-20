"""Test runner implementation for Kaizen."""

import os
import sys
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import traceback

# Try to load dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from .test_case import TestCase, TestStatus, LLMEvaluator, AssertionRunner
from .code_region import CodeRegionExtractor, CodeRegionExecutor
from .input_parser import InputParser, InputParsingError

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
    """Runs tests using the code region execution system with support for multiple inputs."""
    
    def __init__(self, test_config: Dict):
        """Initialize the test runner.
        
        Args:
            test_config: Test configuration dictionary
        """
        self.test_config = test_config
        self._validate_config()
        self.workspace_root = self._find_workspace_root()
        self.config_file_path = Path(test_config.get('config_file', ''))
        
        # Load environment variables BEFORE initializing other components
        self._load_environment_variables()
        
        # Get imported dependencies from config
        imported_dependencies = test_config.get('imported_dependencies', {})
        
        self.code_region_extractor = CodeRegionExtractor()
        self.code_region_executor = CodeRegionExecutor(self.workspace_root, imported_dependencies)
        self.llm_evaluator = LLMEvaluator()
        self.assertion_runner = AssertionRunner()
        self.input_parser = InputParser()
        
    def _validate_config(self) -> None:
        """Validate the test configuration structure."""
        required_fields = ['name', 'file_path']
        for field in required_fields:
            if field not in self.test_config:
                raise ValueError(f"Missing required field '{field}' in test configuration")
        
        # Support both old 'tests' format and new 'steps' format
        if 'tests' not in self.test_config and 'steps' not in self.test_config:
            raise ValueError("Test configuration must contain either 'tests' or 'steps' field")
    
    def _find_workspace_root(self) -> Path:
        """Find the workspace root directory.
        
        This method tries multiple strategies to find the workspace root:
        1. Look for common project root indicators (pyproject.toml, setup.py, etc.)
        2. Look for the kaizen-agent directory (for development)
        3. Use the current working directory as fallback
        """
        original_cwd = Path.cwd()
        
        logger.debug("Starting workspace root detection...")
        
        # Strategy 1: Look for common project root indicators
        current = original_cwd
        max_depth = 10  # Prevent infinite loops
        depth = 0
        
        while current.parent != current and depth < max_depth:
            logger.debug(f"Checking directory: {current}")
            
            # Check for project indicators
            project_indicators = [
                'pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt',
                'package.json', 'Cargo.toml', 'go.mod', 'composer.json'
            ]
            
            if any((current / indicator).exists() for indicator in project_indicators):
                logger.info(f"Found project indicator in: {current}")
                return current
            
            # Check for project directories
            project_dirs = ['src', 'lib', 'app', 'main', 'tests', 'docs']
            if any((current / dir_name).exists() for dir_name in project_dirs):
                logger.info(f"Found project directory in: {current}")
                return current
            
            current = current.parent
            depth += 1
        
        if depth >= max_depth:
            logger.warning(f"Reached maximum depth ({max_depth}) while searching for workspace root")

        # Strategy 2: Look for kaizen-agent directory (for development)
        logger.debug("Searching for kaizen-agent directory...")
        for ancestor in [original_cwd] + list(original_cwd.parents):
            logger.debug(f"Checking ancestor: {ancestor}")
            if ancestor.name == 'kaizen-agent':
                logger.info(f"Found kaizen-agent directory at: {ancestor}")
                return ancestor
        
        # Strategy 3: Fallback to current working directory
        logger.warning("Could not determine workspace root, using current working directory")
        return original_cwd
    
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
            
            # DEBUG: Print the raw test case
            logger.info(f"DEBUG: Raw test case: {test_case}")
            
            # Get evaluation targets from the top-level configuration
            evaluation_targets = self.test_config.get('evaluation', {}).get('evaluation_targets', [])
            logger.info(f"DEBUG: Top-level evaluation targets: {evaluation_targets}")
            
            # Convert test case dict to TestCase object, passing the evaluation targets
            test_case_with_evaluation = test_case.copy()
            test_case_with_evaluation['evaluation_targets'] = evaluation_targets
            test_case_obj = TestCase.from_dict(test_case_with_evaluation)
            
            # DEBUG: Print the parsed test case input
            logger.info(f"DEBUG: TestCase input: {test_case_obj.input}")
            
            # Determine region name: use input['region'] if present, else first from top-level 'regions'
            region_name = test_case_obj.input.get('region')
            if not region_name:
                regions = self.test_config.get('regions', [])
                if not regions:
                    raise ValueError("No region specified in test step or top-level 'regions' field.")
                region_name = regions[0]
                logger.info(f"No region specified in test step; using first region from top-level: {region_name}")
            
            logger.info(f"DEBUG: About to extract region '{region_name}' from file: {test_file_path}")
            
            # Extract and analyze the code region
            region_info = self.code_region_extractor.extract_region(
                test_file_path, 
                region_name
            )
            logger.info(f"DEBUG: Region extraction completed. Region info: {region_info}")
            
            # Add imports from test case to region info
            if 'imports' in test_case_obj.input:
                region_info.imports.extend(test_case_obj.input['imports'])
            
            # Parse input data using the new input parser
            input_data = test_case_obj.input.get('input')
            
            # DEBUG: Print the input data before parsing
            logger.info(f"DEBUG: Input data before parsing: {input_data}")
            logger.info(f"DEBUG: Input data type: {type(input_data)}")
            if isinstance(input_data, list):
                logger.info(f"DEBUG: Input data length: {len(input_data)}")
                for i, item in enumerate(input_data):
                    logger.info(f"DEBUG: Input item {i}: {item} (type: {type(item)})")
            
            if input_data is not None:
                try:
                    logger.info(f"DEBUG: About to parse inputs...")
                    parsed_inputs = self.input_parser.parse_inputs(input_data)
                    logger.info(f"DEBUG: Input parsing completed. Parsed {len(parsed_inputs)} input(s) for test case")
                    
                    # DEBUG: Print the parsed inputs
                    for i, parsed_input in enumerate(parsed_inputs):
                        logger.info(f"DEBUG: Parsed input {i}: {parsed_input} (type: {type(parsed_input)})")
                        
                except InputParsingError as e:
                    logger.error(f"Failed to parse inputs: {str(e)}")
                    return {
                        'status': TestStatus.ERROR.value,
                        'error': f"Input parsing error: {str(e)}"
                    }
            else:
                parsed_inputs = []
            
            # Determine if we need variable tracking
            evaluation_targets = test_case_obj.evaluation_targets or []
            tracked_variables = set()
            
            for target in evaluation_targets:
                if target.get('source') == 'variable':
                    tracked_variables.add(target.get('name'))
            
            logger.info(f"DEBUG: Evaluation targets: {evaluation_targets}")
            logger.info(f"DEBUG: Tracked variables: {tracked_variables}")
            
            # Execute the code region with or without tracking
            if tracked_variables:
                logger.info(f"DEBUG: About to execute with variable tracking for: {tracked_variables}")
                execution_result = self.code_region_executor.execute_region_with_tracking(
                    region_info,
                    test_case_obj.input.get('method'),
                    parsed_inputs,
                    tracked_variables
                )
                actual_output = execution_result['result']
                tracked_values = execution_result['tracked_values']
                logger.info(f"DEBUG: Execution with tracking completed")
            else:
                logger.info(f"DEBUG: About to execute without variable tracking")
                actual_output = self.code_region_executor.execute_region(
                    region_info,
                    test_case_obj.input.get('method'),
                    parsed_inputs
                )
                tracked_values = None
                logger.info(f"DEBUG: Execution without tracking completed")
            
            logger.info(f"DEBUG: About to run assertions...")
            # Run assertions
            assertion_results = self.assertion_runner.run_assertions(
                test_case_obj.assertions, 
                actual_output
            )
            logger.info(f"DEBUG: Assertions completed")
            
            logger.info(f"DEBUG: About to evaluate with LLM...")
            # Evaluate with LLM
            llm_evaluation = self.llm_evaluator.evaluate_result(test_case_obj, actual_output, tracked_values)
            logger.info(f"DEBUG: LLM evaluation completed")
            
            # Determine overall test status
            status = self._determine_test_status(assertion_results, llm_evaluation)
            
            # Combine results
            return {
                'status': status,
                'input': test_case_obj.input,
                'parsed_inputs': parsed_inputs,
                'output': actual_output,
                'tracked_values': tracked_values,
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
            logger.error(f"Full traceback: {traceback.format_exc()}")
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
        logger.info(f"DEBUG: Starting run_tests with file path: {test_file_path}")
        results = self._create_initial_results()
        summary = TestSummary()
        
        try:
            # Resolve the file path relative to config file location
            if self.config_file_path:
                resolved_path = self.config_file_path.parent / test_file_path
            else:
                resolved_path = test_file_path
                
            logger.info(f"DEBUG: Resolved file path: {resolved_path}")
                
            if not resolved_path.exists():
                raise FileNotFoundError(f"Test file not found: {resolved_path}")
            
            # Use 'steps' instead of 'tests' for the new format
            test_steps = self.test_config.get('steps', [])
            logger.info(f"DEBUG: Found {len(test_steps)} test steps to run")
            logger.info(f"Running test steps: {test_steps}")
            
            for i, test_case in enumerate(test_steps):
                logger.info(f"DEBUG: Starting test case {i+1}/{len(test_steps)}: {test_case.get('name', 'Unknown')}")
                test_name = test_case.get('name', 'Unknown')
                logger.info(f"Running test case: {test_name}")
                
                logger.info(f"DEBUG: About to call _run_test_case for: {test_name}")
                test_result = self._run_test_case(test_case, resolved_path)
                logger.info(f"DEBUG: _run_test_case completed for: {test_name}")
                logger.info(f"Test result: {test_result}")
                
                results[test_name] = self._create_test_result(test_result)
                
                summary.total_regions += 1
                if test_result['status'] == TestStatus.PASSED.value:
                    summary.passed_regions += 1
                elif test_result['status'] == TestStatus.FAILED.value:
                    summary.failed_regions += 1
                else:
                    summary.error_regions += 1
                
                logger.info(f"DEBUG: Completed test case {i+1}/{len(test_steps)}: {test_name}")
            
            logger.info(f"DEBUG: All test cases completed, creating final results")
            results['overall_status'] = {
                'status': TestStatus.COMPLETED.value,
                'summary': summary.to_dict()
            }
            results['_status'] = TestStatus.COMPLETED.value
            
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            results['overall_status'] = {
                'status': TestStatus.FAILED.value,
                'summary': summary.to_dict()
            }
            results['_status'] = TestStatus.ERROR.value
        
        logger.info(f"DEBUG: run_tests completed, returning results")
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
                'parsed_inputs': test_result.get('parsed_inputs', []),
                'output': test_result.get('output'),
                'tracked_values': test_result.get('tracked_values', []),
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

    def _load_environment_variables(self) -> None:
        """Load environment variables from .env files and user's environment.
        
        This function looks for .env files in the workspace root and loads them
        into the current process environment. This ensures that environment variables
        like GOOGLE_API_KEY are available for the test runner.
        
        Args:
            workspace_root: Root directory of the workspace to search for .env files
        """
        if not DOTENV_AVAILABLE:
            logger.warning("python-dotenv not available. Install with: pip install python-dotenv")
            return
        
        # Look for .env files in the workspace root
        env_files = [
            self.workspace_root / ".env",
            self.workspace_root / ".env.local",
            self.workspace_root / ".env.test"
        ]
        
        loaded_files = []
        for env_file in env_files:
            if env_file.exists():
                try:
                    load_dotenv(env_file, override=True)
                    loaded_files.append(str(env_file))
                    logger.info(f"Loaded environment variables from: {env_file}")
                except Exception as e:
                    logger.warning(f"Failed to load {env_file}: {str(e)}")
        
        if not loaded_files:
            logger.info("No .env files found in workspace root")
        
        # Log important environment variables (without exposing sensitive values)
        important_vars = ['GOOGLE_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
        for var in important_vars:
            if os.getenv(var):
                logger.info(f"Found {var} in environment")
            else:
                logger.warning(f"Missing {var} in environment") 