"""Test runner implementation for Kaizen."""

import os
import sys
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import traceback
from datetime import datetime

# Try to load dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from .test_case import TestCase, TestStatus, LLMEvaluator, AssertionRunner
from .code_region import CodeRegionExtractor, CodeRegionExecutor, RegionInfo, RegionType, AgentEntryPoint
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
    
    def __init__(self, test_config: Dict, verbose: bool = False):
        """Initialize the test runner.
        
        Args:
            test_config: Test configuration dictionary
            verbose: Whether to show detailed debug information
        """
        self.test_config = test_config
        self.verbose = verbose
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
        
        if self.verbose:
            logger.debug("Starting workspace root detection...")
        
        # Strategy 1: Look for common project root indicators
        current = original_cwd
        max_depth = 10  # Prevent infinite loops
        depth = 0
        
        while current.parent != current and depth < max_depth:
            if self.verbose:
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
        if self.verbose:
            logger.debug("Searching for kaizen-agent directory...")
        for ancestor in [original_cwd] + list(original_cwd.parents):
            if self.verbose:
                logger.debug(f"Checking ancestor: {ancestor}")
            if ancestor.name == 'kaizen-agent':
                logger.info(f"Found kaizen-agent directory at: {ancestor}")
                return ancestor
        
        # Strategy 3: Fallback to current working directory
        logger.warning("Could not determine workspace root, using current working directory")
        return original_cwd
    
    def _run_test_case(self, test_case: Dict, test_file_path: Path):
        """
        Run a single test case with proper assertions and LLM evaluation.
        
        Args:
            test_case: Test case configuration
            test_file_path: Path to the test file
            
        Returns:
            TestCaseResult containing test case results
        """
        # Import here to avoid circular import
        from ...cli.commands.models import TestCaseResult, TestStatus as UnifiedTestStatus
        
        try:
            logger.info(f"Running test case: {test_case.get('name', 'Unknown')}")
            
            # Get language from test config, require it to be set
            language = self.test_config.get("language")
            if not language:
                raise ValueError("No language specified in test configuration. Please set the 'language' field.")
            if self.verbose:
                logger.debug(f"DEBUG: Using language: {language} (type: {type(language)})")
                logger.debug(f"DEBUG: Language comparison - language == 'typescript': {language == 'typescript'}")
                logger.debug(f"DEBUG: Language comparison - language == 'python': {language == 'python'}")
                logger.debug(f"DEBUG: Test config keys: {list(self.test_config.keys())}")
                logger.debug(f"DEBUG: Full test config: {self.test_config}")
            
            # DEBUG: Print the raw test case
            if self.verbose:
                logger.debug(f"DEBUG: Raw test case: {test_case}")
            
            # Get evaluation targets from the top-level configuration
            evaluation_targets = self.test_config.get('evaluation', {}).get('evaluation_targets', [])
            if self.verbose:
                logger.debug(f"DEBUG: Top-level evaluation targets: {evaluation_targets}")
            
            # Convert test case dict to TestCase object, passing the evaluation targets
            test_case_with_evaluation = test_case.copy()
            test_case_with_evaluation['evaluation_targets'] = evaluation_targets
            test_case_obj = TestCase.from_dict(test_case_with_evaluation)
            
            # DEBUG: Print the parsed test case input
            if self.verbose:
                logger.debug(f"DEBUG: TestCase input: {test_case_obj.input}")
            
            # Check if we have agent entry point configuration (new system)
            agent_entry_point_dict = self.test_config.get('agent')
            if agent_entry_point_dict:
                # Convert dictionary to AgentEntryPoint object
                agent_entry_point = AgentEntryPoint(
                    module=agent_entry_point_dict['module'],
                    class_name=agent_entry_point_dict.get('class'),
                    method=agent_entry_point_dict.get('method'),
                    fallback_to_function=agent_entry_point_dict.get('fallback_to_function', True)
                )
                
                # Use the new agent entry point system
                if self.verbose:
                    logger.debug(f"DEBUG: Using agent entry point system: {agent_entry_point}")
                
                # Validate the entry point
                logger.debug(f"DEBUG: About to validate entry point. Language: '{language}' (type: {type(language)})")
                if language == "typescript":
                    logger.debug(f"DEBUG: Using TypeScript validation")
                    if not self.code_region_extractor.validate_entry_point_ts(agent_entry_point, test_file_path):
                        raise ValueError(f"Invalid agent entry point(ts): {agent_entry_point}")
                else:
                    logger.debug(f"DEBUG: Using Python validation")
                    if not self.code_region_extractor.validate_entry_point(agent_entry_point, test_file_path):
                        raise ValueError(f"Invalid agent entry point(python): {agent_entry_point}")
                
                # Extract region using entry point based on language
                if language == "typescript":
                    region_info = self.code_region_extractor.extract_region_by_entry_point_ts(
                        test_file_path, 
                        agent_entry_point
                    )
                else:
                    region_info = self.code_region_extractor.extract_region_by_entry_point(
                        test_file_path, 
                        agent_entry_point
                    )
                region_name = f"{agent_entry_point.module}.{agent_entry_point.class_name or agent_entry_point.method}"
            
            else:
                # Use the legacy marker-based system
                if self.verbose:
                    logger.debug(f"DEBUG: Using legacy marker-based system")
                
                # Determine region name: use input['region'] if present, else first from top-level 'regions'
                region_name = test_case_obj.input.get('region')
                if not region_name:
                    regions = self.test_config.get('regions', [])
                    if not regions:
                        if agent_entry_point_dict:
                            # Use agent entry point logic (already handled above)
                            pass  # Do nothing, agent entry point logic is above
                        else:
                            # No agent entry point, fallback to method in step input
                            method_name = test_case_obj.input.get('method')
                            if not method_name:
                                raise ValueError("No method specified in test step and no regions configured")
                            if self.verbose:
                                logger.debug(f"DEBUG: Extracting function '{method_name}' from test file")
                            if language == "typescript":
                                region_info = self.code_region_extractor.extract_region_ts_by_name(
                                    test_file_path, 
                                    method_name
                                )
                            else:
                                region_info = self.code_region_extractor.extract_region(
                                    test_file_path, 
                                    method_name
                                )
                            region_name = method_name
                    else:
                        region_name = regions[0]
                        logger.info(f"No region specified in test step; using first region from top-level: {region_name}")
                        if self.verbose:
                            logger.debug(f"DEBUG: About to extract region '{region_name}' from file: {test_file_path}")
                        if language == "typescript":
                            region_info = self.code_region_extractor.extract_region_ts(
                                test_file_path, 
                                region_name
                            )
                        else:
                            region_info = self.code_region_extractor.extract_region(
                                test_file_path, 
                                region_name
                            )
                else:
                    if self.verbose:
                        logger.debug(f"DEBUG: About to extract region '{region_name}' from file: {test_file_path}")
                    if language == "typescript":
                        region_info = self.code_region_extractor.extract_region_ts(
                            test_file_path, 
                            region_name
                        )
                    else:
                        region_info = self.code_region_extractor.extract_region(
                            test_file_path, 
                            region_name
                        )
            
            if self.verbose:
                logger.debug(f"DEBUG: Region extraction completed. Region info: {region_info}")
            
            # Add imports from test case to region info
            if 'imports' in test_case_obj.input:
                region_info.imports.extend(test_case_obj.input['imports'])
            
            # Parse input data using the new input parser
            input_data = test_case_obj.input.get('input')
            
            # Extract method name from test case input (only for legacy system)
            method_name = None
            if not agent_entry_point_dict:
                method_name = test_case_obj.input.get('method')
            
            # DEBUG: Print the input data before parsing
            if self.verbose:
                logger.debug(f"DEBUG: Input data before parsing: {input_data}")
                logger.debug(f"DEBUG: Input data type: {type(input_data)}")
                logger.debug(f"DEBUG: Method name: {method_name}")
                if isinstance(input_data, list):
                    logger.debug(f"DEBUG: Input data length: {len(input_data)}")
                    for i, item in enumerate(input_data):
                        logger.debug(f"DEBUG: Input item {i}: {item} (type: {type(item)})")
            
            if input_data is not None:
                try:
                    if self.verbose:
                        logger.debug(f"DEBUG: About to parse inputs...")
                    parsed_inputs = self.input_parser.parse_inputs(input_data)
                    if self.verbose:
                        logger.debug(f"DEBUG: Input parsing completed. Parsed {len(parsed_inputs)} input(s) for test case")
                except InputParsingError as e:
                    logger.error(f"Input parsing failed: {str(e)}")
                    return TestCaseResult(
                        name=test_case.get('name', 'Unknown'),
                        status=UnifiedTestStatus.ERROR,
                        region=region_name,
                        input=input_data,
                        expected_output=test_case_obj.expected_output,
                        error_message=f"Input parsing failed: {str(e)}",
                        timestamp=datetime.now()
                    )
            else:
                parsed_inputs = []
            
            # Execute the code region with parsed inputs based on language
            if self.verbose:
                logger.debug(f"DEBUG: About to execute code region...")
            
            # Get timeout from test configuration
            timeout = test_case.get('timeout')
            
            # Precompile Mastra agents for faster execution
            if language == "typescript":
                # Check if this is a Mastra agent and precompile if needed
                if hasattr(self.code_region_executor, 'precompile_mastra_agent'):
                    precompiled = self.code_region_executor.precompile_mastra_agent(region_info)
                    if precompiled and self.verbose:
                        logger.debug(f"DEBUG: Precompiled Mastra agent: {region_info.name}")
                
                execution_result = self.code_region_executor.execute_typescript_region_with_tracking(
                    region_info, 
                    method_name=method_name,
                    input_data=parsed_inputs,
                    tracked_variables=set(),  # Empty set for no specific tracking
                    timeout=timeout
                )
            else:
                execution_result = self.code_region_executor.execute_region_with_tracking(
                    region_info, 
                    method_name=method_name,
                    input_data=parsed_inputs,
                    tracked_variables=set()  # Empty set for no specific tracking
                )
            actual_output = execution_result['result']
            tracked_values = execution_result['tracked_values']
            if self.verbose:
                logger.debug(f"DEBUG: Code region execution completed")
            
            # Run assertions
            if self.verbose:
                logger.debug(f"DEBUG: About to run assertions...")
            assertion_results = self.assertion_runner.run_assertions(test_case_obj.assertions, actual_output)
            if self.verbose:
                logger.debug(f"DEBUG: Assertions completed")
            
            # Run LLM evaluation
            if self.verbose:
                logger.debug(f"DEBUG: About to evaluate with LLM...")
            llm_evaluation = self.llm_evaluator.evaluate_result(test_case_obj, actual_output, tracked_values)
            if self.verbose:
                logger.debug(f"DEBUG: LLM evaluation completed")
            
            # Determine overall test status
            status = self._determine_test_status(assertion_results, llm_evaluation)
            
            # Convert to unified TestStatus
            unified_status = self._convert_to_unified_status(status)
            
            # Create TestCaseResult
            return TestCaseResult(
                name=test_case.get('name', 'Unknown'),
                status=unified_status,
                region=region_name,
                input=input_data,
                expected_output=test_case_obj.expected_output,
                actual_output=actual_output,
                error_message=None if unified_status == UnifiedTestStatus.PASSED else "Test failed",
                evaluation=llm_evaluation,
                metadata={
                    'parsed_inputs': parsed_inputs,
                    'tracked_values': tracked_values,
                    'assertions': assertion_results,
                    'region_info': {
                        'type': region_info.type.value,
                        'name': region_info.name,
                        'methods': region_info.class_methods,
                        'entry_point': agent_entry_point_dict
                    }
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in test case {test_case.get('name', 'Unknown')}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return TestCaseResult(
                name=test_case.get('name', 'Unknown'),
                status=UnifiedTestStatus.ERROR,
                region=test_case.get('region', 'unknown'),
                input=test_case.get('input'),
                expected_output=test_case.get('expected_output'),
                error_message=str(e),
                error_details=traceback.format_exc(),
                timestamp=datetime.now()
            )
    
    def _determine_test_status(self, assertion_results: List[Dict], llm_evaluation: Dict) -> str:
        """Determine the overall test status based on assertions and LLM evaluation."""
        # Check if any assertions failed
        if any(not result['passed'] for result in assertion_results):
            return TestStatus.FAILED.value
        
        # Check LLM evaluation status
        if llm_evaluation.get('status') == TestStatus.FAILED.value:
            return TestStatus.FAILED.value
        
        return TestStatus.PASSED.value
    
    def _convert_to_unified_status(self, legacy_status: str):
        """Convert legacy TestStatus to unified TestStatus."""
        # Import here to avoid circular import
        from ...cli.commands.models import TestStatus as UnifiedTestStatus
        
        status_mapping = {
            TestStatus.PASSED.value: UnifiedTestStatus.PASSED,
            TestStatus.FAILED.value: UnifiedTestStatus.FAILED,
            TestStatus.ERROR.value: UnifiedTestStatus.ERROR,
            TestStatus.PENDING.value: UnifiedTestStatus.PENDING,
            TestStatus.RUNNING.value: UnifiedTestStatus.RUNNING,
            TestStatus.COMPLETED.value: UnifiedTestStatus.PASSED,  # Completed is considered passed
        }
        return status_mapping.get(legacy_status, UnifiedTestStatus.ERROR)
    
    def run_tests(self, test_file_path: Path):
        """
        Run tests and return unified TestExecutionResult.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            TestExecutionResult containing all test results
        """
        # Import here to avoid circular import
        from ...cli.commands.models import TestExecutionResult, TestStatus as UnifiedTestStatus
        
        logger.info("Starting test execution")
        
        if self.verbose:
            logger.debug(f"DEBUG: Starting run_tests with file path: {test_file_path}")
        
        # Create the unified test execution result
        test_result = TestExecutionResult(
            name=self.test_config.get('name', 'Unknown Test'),
            file_path=test_file_path,
            config_path=self.config_file_path
        )
        
        logger.info(f"Test configuration loaded: {self.test_config.get('name', 'Unknown Test')}")
        
        try:
            # Resolve the file path relative to config file location
            if self.config_file_path:
                resolved_path = self.config_file_path.parent / test_file_path
            else:
                resolved_path = test_file_path
                
            if self.verbose:
                logger.debug(f"DEBUG: Resolved file path: {resolved_path}")
                
            if not resolved_path.exists():
                raise FileNotFoundError(f"Test file not found: {resolved_path}")
            
            logger.info(f"Test file found: {resolved_path}")
            
            # Use 'steps' instead of 'tests' for the new format
            test_steps = self.test_config.get('steps', [])
            if self.verbose:
                logger.debug(f"DEBUG: Found {len(test_steps)} test steps to run")
            logger.info(f"Running {len(test_steps)} test steps")
            
            for i, test_case in enumerate(test_steps):
                if self.verbose:
                    logger.debug(f"DEBUG: Starting test case {i+1}/{len(test_steps)}: {test_case.get('name', 'Unknown')}")
                test_name = test_case.get('name', 'Unknown')
                logger.info(f"Running test case: {test_name}")
                
                if self.verbose:
                    logger.debug(f"DEBUG: About to call _run_test_case for: {test_name}")
                test_case_result = self._run_test_case(test_case, resolved_path)
                if self.verbose:
                    logger.debug(f"DEBUG: _run_test_case completed for: {test_name}")
                    logger.debug(f"Test result: {test_case_result}")
                
                # Add the test case result to the unified result
                test_result.add_test_case(test_case_result)
                
                # Show test case completion status
                status_emoji = "✅" if test_case_result.status.value == "passed" else "❌"
                logger.info(f"{status_emoji} Test case completed: {test_name}")
                
                if self.verbose:
                    logger.debug(f"DEBUG: Completed test case {i+1}/{len(test_steps)}: {test_name}")
            
            logger.info("All test cases completed")
            
            if self.verbose:
                logger.debug(f"DEBUG: All test cases completed")
            
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Add error information to the test result
            test_result.error_message = f"Test execution failed: {str(e)}"
            test_result.error_details = traceback.format_exc()
            test_result.status = UnifiedTestStatus.ERROR
        
        logger.info("Test execution completed")
        
        if self.verbose:
            logger.debug(f"DEBUG: run_tests completed, returning unified result")
        
        return test_result

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
                if self.verbose:
                    logger.debug(f"Found {var} in environment")
            else:
                logger.warning(f"Missing {var} in environment") 