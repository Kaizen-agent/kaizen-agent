"""Comprehensive memory system for Kaizen test execution.

This module provides centralized memory functionality to store ALL execution context,
test logs, and enable surgical code fixing with learning from previous attempts.

DATA STRUCTURE OVERVIEW:
=======================

ExecutionMemory stores data in a hierarchical structure:

1. EXECUTION LEVEL (Top Level)
   - execution_id: str - Unique identifier for each test execution
   - start_time: datetime - When execution started
   - config: TestConfiguration - Complete configuration object
   - configuration_context: Dict - Serialized config with metadata
   - test_runs: List[TestRun] - All test execution attempts
   - llm_interactions: List[LLMInteraction] - All LLM conversations
   - fix_attempts: List[FixAttempt] - All code fix attempts
   - original_code_sections: Dict - Original code before fixes
   - learning_history: Dict - Cumulative learning data

2. TEST RUN LEVEL (TestRun dataclass)
   - test_run_id: str - Unique run identifier
   - attempt_number: int - Which attempt this is
   - timestamp: datetime - When run occurred
   - test_inputs: List[Dict] - Input data for tests
   - test_outputs: List[Dict] - Output data from tests
   - llm_logs: Dict - LLM interaction logs
   - test_cases: List[Dict] - Individual test case details
   - summary: Dict - Test summary statistics
   - result: Dict - Overall result info
   - failed_test_cases: List[Dict] - Failed tests only
   - passed_test_cases: List[Dict] - Passed tests only
   - error_test_cases: List[Dict] - Error tests only
   - timing_analysis: Dict - Execution timing data
   - error_analysis: Dict - Error pattern analysis

3. FIX ATTEMPT LEVEL (FixAttempt dataclass)
   - attempt_number: int - Which fix attempt
   - approach_description: str - What was tried
   - code_changes_made: str - Specific changes
   - original_code: str - Code before fix
   - modified_code: str - Code after fix
   - test_results_before: Dict - Test results before fix
   - test_results_after: Dict - Test results after fix
   - success: bool - Whether fix worked
   - llm_interaction: LLMInteraction - Complete LLM data
   - lessons_learned: str - Key insights
   - why_approach_failed: str - Failure analysis
   - what_worked_partially: str - Partial successes
   - config_context: Dict - Configuration context

4. LLM INTERACTION LEVEL (LLMInteraction dataclass)
   - interaction_type: str - Type of interaction
   - prompt: str - Complete prompt sent
   - response: str - Complete LLM response
   - reasoning: str - Step-by-step reasoning
   - metadata: Dict - Model details, tokens, etc.
   - timestamp: datetime - When interaction occurred

5. TEST CASE LEVEL (TestCase dataclass)
   - test_name: str - Name of the test
   - status: str - 'passed', 'failed', 'error'
   - input: Any - Test input data
   - expected_output: Any - Expected result
   - actual_output: Any - Actual result
   - error_message: str - Error details if failed
   - failing_function: str - Function that failed
   - failing_line: int - Line number of failure
   - llm_logs: Dict - LLM logs for this test

USAGE EXAMPLES:
==============

# Start tracking an execution
memory = ExecutionMemory()
memory.start_execution("test_123", config=my_config)

# Log test results
memory.log_test_run("file.py", test_results)

# Log LLM interactions
memory.log_llm_interaction("file.py", "code_fixing", prompt, response)

# Log fix attempts
memory.log_fix_attempt("file.py", 1, original, fixed, success, ...)

# Get learning context for LLM
        context = memory.get_previous_attempts_insights("file.py")

# Inspect memory structure
memory.inspect_structure()  # Prints complete structure
memory.get_memory_summary()  # Gets summary statistics

KEY METHODS:
===========

- start_execution(): Initialize new execution tracking
- log_test_run(): Store complete test execution data
- log_llm_interaction(): Store LLM conversation data
- log_fix_attempt(): Store code fix attempt with learning
- get_previous_attempts_insights(): Extract learning for next attempt
- get_failure_analysis_data(): Get surgical fix targeting data
- inspect_structure(): Debug method to see complete structure
- get_memory_summary(): Get summary statistics
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import json
import os
import google.generativeai as genai


@dataclass
class TestCase:
    """Represents a single test case with full context."""
    test_name: str
    status: str  # 'passed', 'failed', 'error'
    input: Any
    expected_output: Any
    actual_output: Any
    error_message: Optional[str] = None
    failing_function: Optional[str] = None
    failing_line: Optional[int] = None
    llm_logs: Optional[Dict] = None


@dataclass
class LLMInteraction:
    """Represents a single LLM interaction with complete context."""
    interaction_type: str
    prompt: str
    response: str
    reasoning: Optional[str] = None
    metadata: Optional[Dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class FixAttempt:
    """Represents a complete fix attempt with learning context."""
    attempt_number: int
    file_path: str  # Add file_path field
    approach_description: str
    code_changes_made: str
    original_code: str
    modified_code: str
    test_results_before: Dict
    test_results_after: Dict
    success: bool
    llm_interaction: LLMInteraction
    lessons_learned: Optional[str] = None
    why_approach_failed: Optional[str] = None
    what_worked_partially: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TestRun:
    """Represents a complete test run with all details."""
    test_run_id: str
    attempt_number: int
    timestamp: datetime
    test_inputs: List[Dict]
    test_outputs: List[Dict]
    llm_logs: Dict
    code_fix_attempt: Optional[Dict] = None
    attempt_outcome: Optional[Dict] = None
    evaluation_results: Optional[Dict] = None
    
    # Comprehensive test execution data
    test_cases: List[Dict] = None  # Individual test cases with full details
    summary: Dict = None  # Detailed summary statistics
    result: Dict = None  # Overall result information
    failed_test_cases: List[Dict] = None  # Failed test cases only
    passed_test_cases: List[Dict] = None  # Passed test cases only
    error_test_cases: List[Dict] = None  # Error test cases only
    timing_analysis: Dict = None  # Timing analysis
    error_analysis: Dict = None  # Error analysis
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.test_cases is None:
            self.test_cases = []
        if self.failed_test_cases is None:
            self.failed_test_cases = []
        if self.passed_test_cases is None:
            self.passed_test_cases = []
        if self.error_test_cases is None:
            self.error_test_cases = []
        if self.timing_analysis is None:
            self.timing_analysis = {}
        if self.error_analysis is None:
            self.error_analysis = {}


class ExecutionMemory:
    """Single source of truth for ALL execution data, test logs, and LLM interactions."""
    
    def __init__(self):
        self.executions = {}  # execution_id -> execution_data
        self.current_execution = None
        self.logger = logging.getLogger(__name__)

    def _serialize_config_object(self, config, _visited=None) -> Dict:
        """Serialize a TestConfiguration object to a dictionary for storage.
        
        Args:
            config: TestConfiguration object to serialize
            _visited: Set of object IDs already visited (for recursion guard)
            
        Returns:
            Dictionary representation of the complete configuration
        """
        if config is None:
            return {}
        
        config_dict = {}
        
        # Handle different types of config objects
        if hasattr(config, '__dataclass_fields__'):
            # Dataclass object
            for field_name in config.__dataclass_fields__:
                value = getattr(config, field_name, None)
                config_dict[field_name] = self._serialize_value(value, _visited)
        elif hasattr(config, '__dict__'):
            # Regular object with __dict__
            for key, value in config.__dict__.items():
                config_dict[key] = self._serialize_value(value, _visited)
        elif isinstance(config, dict):
            # Already a dictionary
            for key, value in config.items():
                config_dict[key] = self._serialize_value(value, _visited)
        else:
            # Fallback: try to get common attributes
            common_attrs = ['name', 'auto_fix', 'create_pr', 'max_retries', 'file_path', 'config_path']
            for attr in common_attrs:
                if hasattr(config, attr):
                    value = getattr(config, attr, None)
                    config_dict[attr] = self._serialize_value(value, _visited)
        
        return config_dict

    def _serialize_value(self, value, _visited=None) -> Any:
        """Serialize a value to a JSON-serializable format.
        
        Args:
            value: Value to serialize
            _visited: Set of object IDs already visited (for recursion guard)
            
        Returns:
            Serialized value
        """
        if _visited is None:
            _visited = set()
        
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, list):
            return [self._serialize_value(item, _visited) for item in value]
        elif isinstance(value, dict):
            return {key: self._serialize_value(val, _visited) for key, val in value.items()}
        elif isinstance(value, Path):
            return str(value)
        elif hasattr(value, '__dict__'):
            # Handle dataclass objects with recursion guard
            obj_id = id(value)
            if obj_id in _visited:
                # Circular reference detected - return a placeholder
                return f"<Circular reference to {type(value).__name__}>"
            
            _visited.add(obj_id)
            try:
                return {key: self._serialize_value(val, _visited) for key, val in value.__dict__.items()}
            finally:
                _visited.remove(obj_id)
        elif hasattr(value, 'value'):
            # Handle enum-like objects
            return getattr(value, 'value', str(value))
        else:
            # Fallback to string representation
            return str(value)
    
    def start_execution(self, execution_id: str, config=None, config_manager=None):
        """Start tracking a new execution with config context.
        
        Args:
            execution_id: Unique identifier for this execution
            config: Configuration data for this execution
            config_manager: ConfigurationManager instance (optional)
        """
        self.current_execution = {
            'execution_id': execution_id,
            'start_time': datetime.now(),
            'config': config,
            'test_runs': [],
            'llm_interactions': [],
            'fix_attempts': [],
            'original_code_sections': {},
            'learning_history': {
                'failed_approaches': [],
                'successful_patterns': [],
                'llm_reasoning_evolution': [],
                'cumulative_insights': []
            }
        }
        # Store complete configuration object for comprehensive analysis
        if config is not None:
            # Convert the complete config object to a serializable format
            config_dict = self._serialize_config_object(config)
            self.current_execution['configuration_context'] = {
                'complete_config': config_dict,
                'config_values': {
                    'auto_fix': getattr(config, 'auto_fix', None),
                    'create_pr': getattr(config, 'create_pr', None),
                    'max_retries': getattr(config, 'max_retries', None),
                    'better_ai': getattr(config, 'better_ai', False),
                    'language': getattr(getattr(config, 'language', None), 'value', None),
                    'pr_strategy': getattr(config, 'pr_strategy', None),
                    'base_branch': getattr(config, 'base_branch', 'main')
                },
                'config_metadata': {
                    'config_name': getattr(config, 'name', None),
                    'config_file_path': getattr(config, 'config_path', None),
                    'files_to_fix': getattr(config, 'files_to_fix', []),
                    'loaded_successfully': True
                }
            }
        self.executions[execution_id] = self.current_execution
        self.logger.info(f"Started execution tracking: {execution_id}")
    
    def log_test_run(self, file_path: str, test_results: Dict, run_metadata: Optional[Dict] = None) -> None:
        """Log COMPLETE test execution with all details.
        
        Args:
            file_path: Path to the file being tested
            test_results: Complete test results including inputs, outputs, status
            run_metadata: Additional metadata about the test run
        """
        if not self.current_execution:
            self.logger.warning("No current execution to log test run")
            return
        
        # Handle comprehensive test execution data format
        test_cases = test_results.get('test_cases', [])
        summary = test_results.get('summary', {})
        result = test_results.get('result', {})
        failed_test_cases = test_results.get('failed_test_cases', [])
        passed_test_cases = test_results.get('passed_test_cases', [])
        error_test_cases = test_results.get('error_test_cases', [])
        timing_analysis = test_results.get('timing_analysis', {})
        error_analysis = test_results.get('error_analysis', {})
        
        test_run = TestRun(
            test_run_id=f"run_{len(self.current_execution['test_runs']) + 1}",
            attempt_number=len(self.current_execution['test_runs']) + 1,
            timestamp=datetime.now(),
            test_inputs=test_results.get('inputs', []),
            test_outputs=test_results.get('outputs', []),
            llm_logs=test_results.get('llm_logs', {}),
            code_fix_attempt=test_results.get('code_fix_attempt'),
            attempt_outcome=test_results.get('attempt_outcome'),
            evaluation_results=test_results.get('evaluation_results'),
            # Comprehensive test execution data
            test_cases=test_cases,
            summary=summary,
            result=result,
            failed_test_cases=failed_test_cases,
            passed_test_cases=passed_test_cases,
            error_test_cases=error_test_cases,
            timing_analysis=timing_analysis,
            error_analysis=error_analysis
        )
        
        self.current_execution['test_runs'].append(test_run)
        
        # Log detailed information about the test run
        total_tests = len(test_cases)
        failed_count = len(failed_test_cases)
        passed_count = len(passed_test_cases)
        error_count = len(error_test_cases)
        
        self.logger.info(f"Logged comprehensive test run for {file_path}: {test_run.test_run_id}")
        self.logger.info(f"  - Total tests: {total_tests}")
        self.logger.info(f"  - Passed: {passed_count}, Failed: {failed_count}, Errors: {error_count}")
        
        if error_analysis.get('most_common_error'):
            self.logger.info(f"  - Most common error: {error_analysis['most_common_error']}")
        
        if timing_analysis.get('total_execution_time'):
            self.logger.info(f"  - Total execution time: {timing_analysis['total_execution_time']:.2f}s")
    
    def log_llm_interaction(self, file_path: str, interaction_type: str, prompt: str, 
                           response: str, reasoning: Optional[str] = None, 
                           metadata: Optional[Dict] = None) -> None:
        """Log every LLM interaction with complete context.
        
        Args:
            file_path: Path to the file being processed
            interaction_type: Type of interaction ('code_fixing', 'test_evaluation', etc.)
            prompt: Complete prompt sent to LLM
            response: Full LLM response
            reasoning: Step-by-step reasoning if available
            metadata: Model details, tokens, temperature, etc.
        """
        if not self.current_execution:
            self.logger.warning("No current execution to log LLM interaction")
            return
        
        interaction = LLMInteraction(
            interaction_type=interaction_type,
            prompt=prompt,
            response=response,
            reasoning=reasoning,
            metadata=metadata
        )
        
        self.current_execution['llm_interactions'].append(interaction)
        self.logger.debug(f"Logged LLM interaction: {interaction_type} for {file_path}")
    
    def log_fix_attempt(self, file_path: str, attempt_number: int, 
                       original_code: str, fixed_code: str, success: bool,
                       test_results_before: Dict, test_results_after: Dict,
                       approach_description: str, code_changes: str, 
                       llm_interaction: LLMInteraction,
                       lessons_learned: Optional[str] = None,
                       why_approach_failed: Optional[str] = None,
                       what_worked_partially: Optional[str] = None) -> None:
        """Log comprehensive fix attempt data with learning context.
        
        Args:
            file_path: Path to the file being fixed
            attempt_number: Which attempt this is
            original_code: Code before the fix
            fixed_code: Code after the fix
            success: Whether the fix was successful
            test_results_before: Test results before the fix
            test_results_after: Test results after the fix
            approach_description: What the LLM tried to do
            code_changes: Specific changes made to code
            llm_interaction: Complete LLM interaction data
            lessons_learned: Key insights from this attempt
            why_approach_failed: Analysis of failure reasons
            what_worked_partially: Parts that showed improvement
        """
        if not self.current_execution:
            self.logger.warning("No current execution to log fix attempt")
            return
        
        lessons_learned,why_approach_failed,what_worked_partially = self.analyze_fix_attempt(test_results_before,test_results_after)
        
        fix_attempt = FixAttempt(
            attempt_number=attempt_number,
            file_path=file_path,
            approach_description=approach_description,
            code_changes_made=code_changes,
            original_code=original_code,
            modified_code=fixed_code,
            test_results_before=test_results_before,
            test_results_after=test_results_after,
            success=success,
            llm_interaction=llm_interaction,
            lessons_learned=lessons_learned,
            why_approach_failed=why_approach_failed,
            what_worked_partially=what_worked_partially
        )
        # --- ADD COMPREHENSIVE CONFIG CONTEXT TO ATTEMPT ---
        config_context = self.current_execution.get('configuration_context', {})
        complete_config = config_context.get('complete_config', {})
        config_values = config_context.get('config_values', {})
        
        fix_attempt.config_context = {
            'better_ai_enabled': config_values.get('better_ai', False),
            'max_retries_available': config_values.get('max_retries', 1),
            'language_setting': config_values.get('language', 'unknown'),
            'framework_used': complete_config.get('framework', 'unknown'),
            'agent_type': complete_config.get('agent_type'),
            'test_description': complete_config.get('description'),
            'evaluation_criteria': complete_config.get('evaluation'),
            'test_steps': complete_config.get('steps', []),
            'dependencies': complete_config.get('dependencies', []),
            'referenced_files': complete_config.get('referenced_files', []),
            'test_settings': complete_config.get('settings'),
            'agent_entry_point': complete_config.get('agent')
        }
        self.current_execution['fix_attempts'].append(fix_attempt)
        self.logger.info(f"Logged fix attempt {attempt_number} for {file_path}: {'SUCCESS' if success else 'FAILED'}")
    
    def save_original_relevant_code(self, file_path: str, relevant_sections: Dict) -> None:
        """Save original code sections for surgical fixing reference.
        
        Args:
            file_path: Path to the file
            relevant_sections: Dictionary of function names to original code sections
        """
        if not self.current_execution:
            self.logger.warning("No current execution to save original code")
            return
        
        self.current_execution['original_code_sections'][file_path] = relevant_sections
        self.logger.info(f"Saved original code sections for {file_path}: {list(relevant_sections.keys())}")
    
    def get_failure_analysis_data(self, file_path: str) -> Dict:
        """Extract everything needed for surgical fixing including original code.
        
        Args:
            file_path: Path to the file to get context for
            
        Returns:
            Dictionary containing failure analysis data for surgical fixing
        """
        if not self.current_execution:
            return {}
        
        # Extract failed test cases from latest run
        failed_cases = self.get_failed_cases_latest_run(file_path)
        
        # Get original code sections
        original_sections = self.current_execution['original_code_sections'].get(file_path, {})
        
        # Extract function names and line numbers from error messages
        failing_functions = set()
        failing_lines = set()
        error_types = set()
        
        for case in failed_cases:
            if case.error_message:
                # Extract function names
                func_matches = re.findall(r'in ([a-zA-Z_][a-zA-Z0-9_]*)\(', case.error_message)
                failing_functions.update(func_matches)
                
                # Extract line numbers
                line_matches = re.findall(r'line (\d+)', case.error_message)
                line_matches.extend(re.findall(r':(\d+):', case.error_message))
                failing_lines.update([int(line) for line in line_matches])
                
                # Extract error types
                error_matches = re.findall(r'(TypeError|AttributeError|ValueError|IndexError|KeyError):', case.error_message)
                error_types.update(error_matches)
        
        # Get best attempt so far
        best_attempt = self.find_best_attempt(file_path)
        
        # Check for regressions
        regression_analysis = self.detect_regressions_from_last_attempt(file_path)
        
        return {
            'failing_functions': list(failing_functions),
            'failing_lines': list(failing_lines),
            'test_names': [case.test_name for case in failed_cases],
            'error_messages': [case.error_message for case in failed_cases if case.error_message],
            'error_types': list(error_types),
            'original_relevant_sections': original_sections,
            'failed_test_cases': [asdict(case) for case in failed_cases],
            'best_attempt_so_far': best_attempt,
            'regression_analysis': regression_analysis
        }
    
    def get_failed_cases_latest_run(self, file_path: str = None) -> List[TestCase]:
        """Extract only failed test cases from the latest run.
        
        Args:
            file_path: Optional file path filter
            
        Returns:
            List of failed test cases with full context
        """
        if not self.current_execution or not self.current_execution['test_runs']:
            return []
        
        latest_run = self.current_execution['test_runs'][-1]
        failed_cases = []
        
        # Use comprehensive test case data if available
        if latest_run.failed_test_cases:
            for test_case_data in latest_run.failed_test_cases:
                case = TestCase(
                    test_name=test_case_data.get('name', 'Unknown'),
                    status=test_case_data.get('status', 'failed'),
                    input=test_case_data.get('input'),
                    expected_output=test_case_data.get('expected_output'),
                    actual_output=test_case_data.get('actual_output'),
                    error_message=test_case_data.get('error_message'),
                    failing_function=test_case_data.get('failing_function'),
                    failing_line=test_case_data.get('failing_line'),
                    llm_logs=test_case_data.get('llm_logs', {})
                )
                failed_cases.append(case)
        else:
            # Fallback to legacy parsing of test outputs
            for i, output in enumerate(latest_run.test_outputs):
                if output.get('status') in ['failed', 'error']:
                    case = TestCase(
                        test_name=output.get('test_name', f'test_{i}'),
                        status=output.get('status', 'failed'),
                        input=latest_run.test_inputs[i] if i < len(latest_run.test_inputs) else None,
                        expected_output=output.get('expected_output'),
                        actual_output=output.get('actual_output'),
                        error_message=output.get('error_message'),
                        failing_function=output.get('failing_function'),
                        failing_line=output.get('failing_line'),
                        llm_logs=latest_run.llm_logs.get(f'test_{i}', {})
                    )
                    failed_cases.append(case)
        
        return failed_cases
    
    def all_tests_passed_latest_run(self, file_path: str = None) -> bool:
        """Check if ALL tests in the latest run passed (no failures/errors).
        
        Args:
            file_path: Optional file path filter
            
        Returns:
            True if all tests passed, False otherwise
        """
        failed_cases = self.get_failed_cases_latest_run(file_path)
        return len(failed_cases) == 0
    
    def find_best_attempt(self, file_path: str = None) -> Dict:
        """Find the attempt with the highest test success rate.
        
        Args:
            file_path: Optional file path filter
            
        Returns:
            Dictionary containing best attempt data
        """
        if not self.current_execution:
            return {}
        
        # First try to find best attempt from fix_attempts (more accurate)
        fix_attempts = self.current_execution.get('fix_attempts', [])
        file_attempts = [attempt for attempt in fix_attempts if attempt.file_path == file_path] if file_path else fix_attempts
        
        best_attempt = None
        best_success_rate = 0
        
        # Compare fix attempts based on their test results
        for attempt in file_attempts:
            if hasattr(attempt, 'test_results_after') and attempt.test_results_after:
                summary = attempt.test_results_after.get('summary', {})
                total_tests = summary.get('total_tests', 0)
                if total_tests == 0:
                    continue
                
                success_rate = summary.get('success_rate', 0.0)
                passed_tests = summary.get('passed_tests', 0)
                
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_attempt = {
                        'attempt_number': attempt.attempt_number,
                        'file_path': attempt.file_path,
                        'success_rate': success_rate,
                        'passed_tests': passed_tests,
                        'total_tests': total_tests,
                        'timestamp': attempt.timestamp,
                        'success': attempt.success,
                        'approach_description': attempt.approach_description,
                        'lessons_learned': attempt.lessons_learned,
                        'why_approach_failed': attempt.why_approach_failed,
                        'what_worked_partially': attempt.what_worked_partially,
                        'test_results_after': attempt.test_results_after
                    }
        
        # If no fix attempts found, fallback to test_runs
        if best_attempt is None and self.current_execution.get('test_runs'):
            for run in self.current_execution['test_runs']:
                # Use comprehensive summary data if available
                if run.summary:
                    total_tests = run.summary.get('total_tests', 0)
                    if total_tests == 0:
                        continue
                    
                    success_rate = run.summary.get('success_rate', 0.0)
                    passed_tests = run.summary.get('passed_tests', 0)
                    
                    if success_rate > best_success_rate:
                        best_success_rate = success_rate
                        best_attempt = {
                            'attempt_number': run.attempt_number,
                            'success_rate': success_rate,
                            'passed_tests': passed_tests,
                            'total_tests': total_tests,
                            'timestamp': run.timestamp,
                            'summary': run.summary,
                            'result': run.result,
                            'timing_analysis': run.timing_analysis,
                            'error_analysis': run.error_analysis
                        }
                else:
                    # Fallback to legacy calculation
                    total_tests = len(run.test_outputs)
                    if total_tests == 0:
                        continue
                    
                    passed_tests = sum(1 for output in run.test_outputs if output.get('status') == 'passed')
                    success_rate = passed_tests / total_tests
                    
                    if success_rate > best_success_rate:
                        best_success_rate = success_rate
                        best_attempt = {
                            'attempt_number': run.attempt_number,
                            'success_rate': success_rate,
                            'passed_tests': passed_tests,
                            'total_tests': total_tests,
                            'timestamp': run.timestamp
                        }
        
        return best_attempt or {}
    
    def detect_regressions_from_last_attempt(self, file_path: str = None) -> Dict:
        """Compare latest run to previous run to detect regressions.
        
        Args:
            file_path: Optional file path filter
            
        Returns:
            Dictionary containing regression analysis
        """
        if not self.current_execution or len(self.current_execution['test_runs']) < 2:
            return {'has_regressions': False, 'newly_failed_tests': [], 'improvement_from_baseline': 0}
        
        current_run = self.current_execution['test_runs'][-1]
        previous_run = self.current_execution['test_runs'][-2]
        
        # Use comprehensive test case data if available
        if current_run.failed_test_cases and previous_run.passed_test_cases:
            # Get test names that failed in current but passed in previous
            current_failed_names = {tc.get('name') for tc in current_run.failed_test_cases}
            previous_passed_names = {tc.get('name') for tc in previous_run.passed_test_cases}
            
            newly_failed = list(current_failed_names.intersection(previous_passed_names))
            
            # Calculate improvement from baseline (first run)
            baseline_run = self.current_execution['test_runs'][0]
            if baseline_run.summary:
                baseline_passed = baseline_run.summary.get('passed_tests', 0)
                current_passed = current_run.summary.get('passed_tests', 0)
            else:
                baseline_passed = sum(1 for output in baseline_run.test_outputs if output.get('status') == 'passed')
                current_passed = sum(1 for output in current_run.test_outputs if output.get('status') == 'passed')
            
            improvement = current_passed - baseline_passed
            
            return {
                'has_regressions': len(newly_failed) > 0,
                'newly_failed_tests': newly_failed,
                'improvement_from_baseline': improvement
            }
        else:
            # Fallback to legacy comparison
            current_failed = {output.get('test_name') for output in current_run.test_outputs 
                             if output.get('status') in ['failed', 'error']}
            previous_passed = {output.get('test_name') for output in previous_run.test_outputs 
                              if output.get('status') == 'passed'}
            
            newly_failed = list(current_failed.intersection(previous_passed))
            
            # Calculate improvement from baseline (first run)
            baseline_run = self.current_execution['test_runs'][0]
            baseline_passed = sum(1 for output in baseline_run.test_outputs if output.get('status') == 'passed')
            current_passed = sum(1 for output in current_run.test_outputs if output.get('status') == 'passed')
            improvement = current_passed - baseline_passed
            
            return {
                'has_regressions': len(newly_failed) > 0,
                'newly_failed_tests': newly_failed,
                'improvement_from_baseline': improvement
            }
    
    def get_complete_test_history(self, file_path: str = None) -> List[Dict]:
        """Get complete test execution history with all logs.
        
        Args:
            file_path: Optional file path filter
            
        Returns:
            List of test run dictionaries with complete history
        """
        if not self.current_execution:
            return []
        
        return [asdict(run) for run in self.current_execution['test_runs']]
    
    def get_comprehensive_test_analysis(self, file_path: str = None) -> Dict:
        """Get comprehensive analysis of all test runs with detailed information.
        
        Args:
            file_path: Optional file path filter
            
        Returns:
            Dictionary containing comprehensive test analysis
        """
        if not self.current_execution or not self.current_execution['test_runs']:
            return {}
        
        runs = self.current_execution['test_runs']
        
        # Analyze all test runs
        analysis = {
            'total_runs': len(runs),
            'runs_analysis': [],
            'overall_statistics': {
                'total_test_cases': 0,
                'total_passed': 0,
                'total_failed': 0,
                'total_errors': 0,
                'average_success_rate': 0.0,
                'best_success_rate': 0.0,
                'worst_success_rate': 100.0
            },
            'error_patterns': {},
            'timing_patterns': {
                'total_execution_time': 0.0,
                'average_execution_time': 0.0,
                'fastest_run': None,
                'slowest_run': None
            },
            'improvement_trend': []
        }
        
        total_success_rates = []
        total_execution_times = []
        
        for i, run in enumerate(runs):
            run_analysis = {
                'run_id': run.test_run_id,
                'attempt_number': run.attempt_number,
                'timestamp': run.timestamp.isoformat() if run.timestamp else None,
                'summary': run.summary or {},
                'result': run.result or {},
                'timing_analysis': run.timing_analysis or {},
                'error_analysis': run.error_analysis or {},
                'test_cases_count': len(run.test_cases) if run.test_cases else 0,
                'failed_cases_count': len(run.failed_test_cases) if run.failed_test_cases else 0,
                'passed_cases_count': len(run.passed_test_cases) if run.passed_test_cases else 0,
                'error_cases_count': len(run.error_test_cases) if run.error_test_cases else 0
            }
            
            # Calculate success rate
            if run.summary:
                success_rate = run.summary.get('success_rate', 0.0)
                total_success_rates.append(success_rate)
                run_analysis['success_rate'] = success_rate
                
                # Update overall statistics
                analysis['overall_statistics']['total_test_cases'] += run.summary.get('total_tests', 0)
                analysis['overall_statistics']['total_passed'] += run.summary.get('passed_tests', 0)
                analysis['overall_statistics']['total_failed'] += run.summary.get('failed_tests', 0)
                analysis['overall_statistics']['total_errors'] += run.summary.get('error_tests', 0)
                
                # Track best/worst success rates
                if success_rate > analysis['overall_statistics']['best_success_rate']:
                    analysis['overall_statistics']['best_success_rate'] = success_rate
                if success_rate < analysis['overall_statistics']['worst_success_rate']:
                    analysis['overall_statistics']['worst_success_rate'] = success_rate
            
            # Analyze timing
            if run.timing_analysis:
                execution_time = run.timing_analysis.get('total_execution_time')
                if execution_time:
                    total_execution_times.append(execution_time)
                    analysis['timing_patterns']['total_execution_time'] += execution_time
                    
                    if (analysis['timing_patterns']['fastest_run'] is None or 
                        execution_time < analysis['timing_patterns']['fastest_run']):
                        analysis['timing_patterns']['fastest_run'] = execution_time
                    
                    if (analysis['timing_patterns']['slowest_run'] is None or 
                        execution_time > analysis['timing_patterns']['slowest_run']):
                        analysis['timing_patterns']['slowest_run'] = execution_time
            
            # Analyze error patterns
            if run.error_analysis:
                most_common_error = run.error_analysis.get('most_common_error')
                if most_common_error:
                    if most_common_error not in analysis['error_patterns']:
                        analysis['error_patterns'][most_common_error] = 0
                    analysis['error_patterns'][most_common_error] += 1
            
            # Track improvement trend
            if i > 0:
                previous_run = runs[i-1]
                if run.summary and previous_run.summary:
                    current_passed = run.summary.get('passed_tests', 0)
                    previous_passed = previous_run.summary.get('passed_tests', 0)
                    improvement = current_passed - previous_passed
                    analysis['improvement_trend'].append({
                        'from_attempt': previous_run.attempt_number,
                        'to_attempt': run.attempt_number,
                        'improvement': improvement,
                        'current_passed': current_passed,
                        'previous_passed': previous_passed
                    })
            
            analysis['runs_analysis'].append(run_analysis)
        
        # Calculate averages
        if total_success_rates:
            analysis['overall_statistics']['average_success_rate'] = sum(total_success_rates) / len(total_success_rates)
        
        if total_execution_times:
            analysis['timing_patterns']['average_execution_time'] = sum(total_execution_times) / len(total_execution_times)
        
        return analysis
    
    def _generate_digested_knowledge_summary(self, previous_attempts_history: List[Dict], 
                                           failed_approaches_to_avoid: List[str],
                                           successful_patterns_to_build_on: List[str],
                                           failed_cases_current: List[TestCase]) -> Dict:
        """Generate a digested knowledge summary from all attempts information.
        
        This method analyzes the attempts history and creates a concise summary
        of what's working, what's not working, and key insights for future attempts.
        
        Args:
            previous_attempts_history: List of previous attempt data
            failed_approaches_to_avoid: List of failed approaches
            successful_patterns_to_build_on: List of successful patterns
            failed_cases_current: Current failed test cases
            
        Returns:
            Dictionary containing digested knowledge summary
        """
        if not previous_attempts_history:
            return {
                'summary': 'No previous attempts to analyze',
                'key_insights': [],
                'working_strategies': [],
                'failed_strategies': [],
                'recommendations': ['Start with basic debugging approach']
            }
        
        # Analyze attempt patterns
        total_attempts = len(previous_attempts_history)
        successful_attempts = [a for a in previous_attempts_history if a.get('test_results_after', {}).get('success_rate', 0) > 0.5]
        failed_attempts = [a for a in previous_attempts_history if a.get('test_results_after', {}).get('success_rate', 0) <= 0.5]
        
        # Extract key insights from attempts
        key_insights = []
        working_strategies = []
        failed_strategies = []
        
        # Analyze what's working
        for pattern in successful_patterns_to_build_on:
            working_strategies.append(pattern)
        
        # Analyze what's not working
        for approach in failed_approaches_to_avoid:
            failed_strategies.append(approach)
        
        # Extract insights from LLM reasoning
        for attempt in previous_attempts_history:
            if attempt.get('lessons_learned'):
                key_insights.append(attempt['lessons_learned'])
            if attempt.get('why_it_failed'):
                failed_strategies.append(f"Failed in attempt {attempt['attempt_number']}: {attempt['why_it_failed']}")
        
        # Generate recommendations based on patterns
        recommendations = []
        
        if failed_strategies:
            recommendations.append(f"Avoid {len(failed_strategies)} previously failed approaches")
        
        if working_strategies:
            recommendations.append(f"Build on {len(working_strategies)} successful patterns")
        
        if failed_cases_current:
            current_error_types = set()
            for case in failed_cases_current:
                if case.error_message:
                    # Extract error type
                    if 'TypeError' in case.error_message:
                        current_error_types.add('TypeError')
                    elif 'AttributeError' in case.error_message:
                        current_error_types.add('AttributeError')
                    elif 'ValueError' in case.error_message:
                        current_error_types.add('ValueError')
                    elif 'IndexError' in case.error_message:
                        current_error_types.add('IndexError')
                    elif 'KeyError' in case.error_message:
                        current_error_types.add('KeyError')
            
            if current_error_types:
                recommendations.append(f"Focus on fixing {', '.join(current_error_types)} errors")
        
        # Calculate success trend
        if len(previous_attempts_history) >= 2:
            latest_success_rate = previous_attempts_history[-1].get('test_results_after', {}).get('success_rate', 0)
            previous_success_rate = previous_attempts_history[-2].get('test_results_after', {}).get('success_rate', 0)
            
            if latest_success_rate > previous_success_rate:
                trend = "improving"
            elif latest_success_rate < previous_success_rate:
                trend = "regressing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        # Generate overall summary
        if total_attempts == 0:
            summary = "Starting fresh - no previous attempts to learn from"
        elif len(successful_attempts) == 0:
            summary = f"After {total_attempts} attempts, no successful strategies found yet"
        elif len(successful_attempts) == total_attempts:
            summary = f"All {total_attempts} attempts have been successful"
        else:
            success_rate = len(successful_attempts) / total_attempts
            summary = f"After {total_attempts} attempts: {len(successful_attempts)} successful, {len(failed_attempts)} failed ({success_rate:.1%} success rate)"
        
        return {
            'summary': summary,
            'trend': trend,
            'key_insights': key_insights[:5],  # Limit to top 5 insights
            'working_strategies': working_strategies,
            'failed_strategies': failed_strategies,
            'recommendations': recommendations,
            'attempt_statistics': {
                'total_attempts': total_attempts,
                'successful_attempts': len(successful_attempts),
                'failed_attempts': len(failed_attempts),
                'success_rate': len(successful_attempts) / total_attempts if total_attempts > 0 else 0
            }
        }
    
    def get_previous_attempts_insights(self, file_path: str) -> Dict:
        """Extract comprehensive learning context from all previous attempts.
        
        This is the KEY function for LLM learning - provides everything needed
        to avoid repeating failed approaches and build on successful ones.
        
        Args:
            file_path: Path to the file being processed
            
        Returns:
            Dictionary containing comprehensive learning context from previous attempts
        """
        if not self.current_execution:
            return {}
        
        # Get current failed cases
        failed_cases_current = self.get_failed_cases_latest_run(file_path)
        
        # Build previous attempts history
        previous_attempts_history = []
        failed_approaches_to_avoid = []
        successful_patterns_to_build_on = []
        what_not_to_try_again = []
        
        for attempt in self.current_execution['fix_attempts']:
            attempt_data = {
                'attempt_number': attempt.attempt_number,
                'approach_taken': attempt.approach_description,
                'code_changes_made': attempt.code_changes_made,
                'why_it_failed': attempt.why_approach_failed,
                'test_results_after': attempt.test_results_after,
                'lessons_learned': attempt.lessons_learned
            }
            previous_attempts_history.append(attempt_data)
            
            # Extract failed approaches
            if not attempt.success and attempt.why_approach_failed:
                failed_approaches_to_avoid.append(
                    f"{attempt.approach_description}: {attempt.why_approach_failed}"
                )
                what_not_to_try_again.append({
                    'failed_approach': attempt.approach_description,
                    'why_failed': attempt.why_approach_failed,
                    'lesson': attempt.lessons_learned or 'Avoid this approach'
                })
            
            # Extract successful patterns
            if attempt.success or attempt.what_worked_partially:
                successful_patterns_to_build_on.append(
                    f"{attempt.approach_description}: {attempt.what_worked_partially or 'worked completely'}"
                )
            
            # Extract LLM reasoning insights (removed - not currently used)
        
        # --- ADD CONFIGURATION CONTEXT TO LEARNING ---
        config_context = self.current_execution.get('configuration_context', {})
        
        # Generate digested knowledge summary from attempts
        digested_knowledge = self._generate_digested_knowledge_summary(
            previous_attempts_history, 
            failed_approaches_to_avoid, 
            successful_patterns_to_build_on,
            failed_cases_current
        )
        
        learning_context = {
            'failed_cases_current': [asdict(case) for case in failed_cases_current],
            'previous_attempts_history': previous_attempts_history,
            'failed_approaches_to_avoid': failed_approaches_to_avoid,
            'successful_patterns_to_build_on': successful_patterns_to_build_on,
            'what_not_to_try_again': what_not_to_try_again,
            'original_code_sections': self.current_execution['original_code_sections'].get(file_path, {}),
            'digested_knowledge_summary': digested_knowledge
        }
        # Add config factors
        learning_context['configuration_factors'] = {
            'current_config': config_context.get('config_values', {}),
            'config_influence_on_attempts': self._analyze_config_impact_on_attempts(file_path)
        }
        return learning_context

    def _analyze_config_impact_on_attempts(self, file_path: str) -> Dict:
        """Analyze how configuration settings influenced previous attempts."""
        config_context = self.current_execution.get('configuration_context', {})
        config_values = config_context.get('config_values', {})
        complete_config = config_context.get('complete_config', {})
        
        # Enhanced analysis using complete configuration
        analysis = {
            'better_ai_enabled': config_values.get('better_ai', False),
            'max_retries_setting': config_values.get('max_retries', 1),
            'language_context': config_values.get('language', 'unknown'),
            'auto_fix_enabled': config_values.get('auto_fix', False),
            'framework_used': complete_config.get('framework', 'unknown'),
            'agent_type': complete_config.get('agent_type'),
            'test_steps_count': len(complete_config.get('steps', [])),
            'dependencies_count': len(complete_config.get('dependencies', [])),
            'referenced_files_count': len(complete_config.get('referenced_files', [])),
            'evaluation_criteria': complete_config.get('evaluation'),
            'test_settings': complete_config.get('settings'),
            'agent_entry_point': complete_config.get('agent')
        }
        
        return analysis
    
    def get_complete_configuration(self) -> Dict:
        """Get the complete configuration object for detailed analysis.
        
        Returns:
            Dictionary containing the complete TestConfiguration data
        """
        if not self.current_execution:
            return {}
        
        config_context = self.current_execution.get('configuration_context', {})
        return config_context.get('complete_config', {})
    
    def get_configuration_summary(self) -> Dict:
        """Get a summary of key configuration settings for quick reference.
        
        Returns:
            Dictionary containing configuration summary
        """
        if not self.current_execution:
            return {}
        
        config_context = self.current_execution.get('configuration_context', {})
        complete_config = config_context.get('complete_config', {})
        config_values = config_context.get('config_values', {})
        
        return {
            'test_name': complete_config.get('name'),
            'file_path': complete_config.get('file_path'),
            'description': complete_config.get('description'),
            'agent_type': complete_config.get('agent_type'),
            'framework': complete_config.get('framework'),
            'language': config_values.get('language'),
            'auto_fix': config_values.get('auto_fix'),
            'better_ai': config_values.get('better_ai'),
            'max_retries': config_values.get('max_retries'),
            'files_to_fix': complete_config.get('files_to_fix', []),
            'dependencies': complete_config.get('dependencies', []),
            'steps_count': len(complete_config.get('steps', [])),
            'evaluation_criteria': complete_config.get('evaluation'),
            'test_settings': complete_config.get('settings')
        }
    
    def get_config_value(self, key: str, default=None) -> Any:
        """Get a specific configuration value from memory.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self.current_execution:
            return default
        
        config_context = self.current_execution.get('configuration_context', {})
        complete_config = config_context.get('complete_config', {})
        config_values = config_context.get('config_values', {})
        
        # Try config_values first (for commonly accessed values)
        if key in config_values:
            return config_values[key]
        
        # Try complete_config for all other values
        return complete_config.get(key, default)
    
    def get_config_property(self, property_name: str) -> Any:
        """Get a configuration property using dot notation (e.g., 'language.value').
        
        Args:
            property_name: Property name in dot notation (e.g., 'language.value')
            
        Returns:
            Configuration property value or None
        """
        if not self.current_execution:
            return None
        
        config_context = self.current_execution.get('configuration_context', {})
        complete_config = config_context.get('complete_config', {})
        
        # Handle dot notation
        if '.' in property_name:
            parts = property_name.split('.')
            current = complete_config
            
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            
            return current
        else:
            return complete_config.get(property_name)
    
    def has_config_value(self, key: str) -> bool:
        """Check if a configuration value exists in memory.
        
        Args:
            key: Configuration key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.current_execution:
            return False
        
        config_context = self.current_execution.get('configuration_context', {})
        complete_config = config_context.get('complete_config', {})
        config_values = config_context.get('config_values', {})
        
        return key in config_values or key in complete_config
    
    
    def analyze_fix_attempt(self, test_results_before: Dict, test_results_after: Dict) -> tuple[str, str, str]:
        """Analyze fix attempt using LLM to extract insights.
        
        Args:
            test_results_before: Test results before the fix attempt
            test_results_after: Test results after the fix attempt
            
        Returns:
            Tuple of (lessons_learned, why_approach_failed, what_worked_partially)
        """
        try:
            # Initialize LLM model
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                self.logger.warning("GOOGLE_API_KEY not found, using fallback analysis")
                return self._fallback_analysis(test_results_before, test_results_after)
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(test_results_before, test_results_after)
            
            # Get LLM response
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for more focused results
                    max_output_tokens=2000,
                    top_p=0.8,
                    top_k=40,
                )
            )
            
            if not response or not response.text:
                self.logger.warning("Empty LLM response, using fallback analysis")
                return self._fallback_analysis(test_results_before, test_results_after)
            
            # Parse the response
            return self._parse_analysis_response(response.text)
            
        except Exception as e:
            self.logger.error(f"Error in LLM analysis: {str(e)}")
            return self._fallback_analysis(test_results_before, test_results_after)
    
    def _build_analysis_prompt(self, test_results_before: Dict, test_results_after: Dict) -> str:
        """Build prompt for analyzing fix attempt results.
        
        Args:
            test_results_before: Test results before the fix
            test_results_after: Test results after the fix
            
        Returns:
            Formatted prompt for LLM analysis
        """
        # Extract key metrics
        before_summary = test_results_before.get('summary', {})
        after_summary = test_results_after.get('summary', {})
        
        before_passed = before_summary.get('passed_tests', 0)
        before_failed = before_summary.get('failed_tests', 0)
        before_errors = before_summary.get('error_tests', 0)
        before_total = before_summary.get('total_tests', 0)
        
        after_passed = after_summary.get('passed_tests', 0)
        after_failed = after_summary.get('failed_tests', 0)
        after_errors = after_summary.get('error_tests', 0)
        after_total = after_summary.get('total_tests', 0)
        
        # Extract failed test cases for detailed analysis
        failed_before = test_results_before.get('failed_test_cases', [])
        failed_after = test_results_after.get('failed_test_cases', [])
        
        # Calculate percentages safely
        before_percent = (before_passed / before_total * 100) if before_total > 0 else 0
        after_percent = (after_passed / after_total * 100) if after_total > 0 else 0
        
        prompt = f"""You are an expert test analyst. Analyze the test results from a code fix attempt and provide insights.

TEST RESULTS COMPARISON:
Before Fix:
- Passed: {before_passed}/{before_total} ({before_percent:.1f}%)
- Failed: {before_failed}
- Errors: {before_errors}

After Fix:
- Passed: {after_passed}/{after_total} ({after_percent:.1f}%)
- Failed: {after_failed}
- Errors: {after_errors}

FAILED TESTS BEFORE FIX:
{json.dumps(failed_before[:5], indent=2) if failed_before else "None"}

FAILED TESTS AFTER FIX:
{json.dumps(failed_after[:5], indent=2) if failed_after else "None"}

ANALYSIS TASK:
Based on the test results comparison, provide three concise insights:

1. LESSONS_LEARNED: What key insights can be extracted from this fix attempt? (max 100 words)
2. WHY_APPROACH_FAILED: If tests still fail, what went wrong with this approach? (max 100 words)
3. WHAT_WORKED_PARTIALLY: What aspects of the fix showed improvement? (max 100 words)

Format your response exactly as:
LESSONS_LEARNED: [your insight here]
WHY_APPROACH_FAILED: [your analysis here]
WHAT_WORKED_PARTIALLY: [your observation here]

Be specific, actionable, and focus on patterns that can inform future fix attempts."""
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> tuple[str, str, str]:
        """Parse LLM response to extract the three analysis components.
        
        Args:
            response: LLM response text
            
        Returns:
            Tuple of (lessons_learned, why_approach_failed, what_worked_partially)
        """
        lessons_learned = ""
        why_approach_failed = ""
        what_worked_partially = ""
        
        try:
            # Extract each section
            if "LESSONS_LEARNED:" in response:
                lessons_start = response.find("LESSONS_LEARNED:") + len("LESSONS_LEARNED:")
                lessons_end = response.find("WHY_APPROACH_FAILED:") if "WHY_APPROACH_FAILED:" in response else len(response)
                lessons_learned = response[lessons_start:lessons_end].strip()
            
            if "WHY_APPROACH_FAILED:" in response:
                failed_start = response.find("WHY_APPROACH_FAILED:") + len("WHY_APPROACH_FAILED:")
                failed_end = response.find("WHAT_WORKED_PARTIALLY:") if "WHAT_WORKED_PARTIALLY:" in response else len(response)
                why_approach_failed = response[failed_start:failed_end].strip()
            
            if "WHAT_WORKED_PARTIALLY:" in response:
                worked_start = response.find("WHAT_WORKED_PARTIALLY:") + len("WHAT_WORKED_PARTIALLY:")
                what_worked_partially = response[worked_start:].strip()
            
            # Clean up any remaining formatting
            lessons_learned = lessons_learned.replace('\n', ' ').strip()
            why_approach_failed = why_approach_failed.replace('\n', ' ').strip()
            what_worked_partially = what_worked_partially.replace('\n', ' ').strip()
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {str(e)}")
        
        return lessons_learned, why_approach_failed, what_worked_partially
    
    def _fallback_analysis(self, test_results_before: Dict, test_results_after: Dict) -> tuple[str, str, str]:
        """Fallback analysis when LLM is not available.
        
        Args:
            test_results_before: Test results before the fix
            test_results_after: Test results after the fix
            
        Returns:
            Tuple of (lessons_learned, why_approach_failed, what_worked_partially)
        """
        before_summary = test_results_before.get('summary', {})
        after_summary = test_results_after.get('summary', {})
        
        before_passed = before_summary.get('passed_tests', 0)
        after_passed = after_summary.get('passed_tests', 0)
        
        if after_passed > before_passed:
            lessons_learned = f"Fix attempt improved test success from {before_passed} to {after_passed} passed tests"
            why_approach_failed = "Some tests still failing, need additional fixes"
            what_worked_partially = f"Successfully fixed {after_passed - before_passed} tests"
        elif after_passed == before_passed:
            lessons_learned = "Fix attempt maintained same test success rate"
            why_approach_failed = "No improvement in test results"
            what_worked_partially = "No tests were broken by the fix"
        else:
            lessons_learned = f"Fix attempt reduced test success from {before_passed} to {after_passed} passed tests"
            why_approach_failed = "Fix introduced regressions or broke existing functionality"
            what_worked_partially = "No improvements observed"
        
        return lessons_learned, why_approach_failed, what_worked_partially

    def get_memory_schema(self) -> Dict:
        """Get the complete schema of the memory data structure.
        
        Returns:
            Dictionary describing the memory schema
        """
        schema = {
            'execution_level': {
                'description': 'Top-level execution data',
                'fields': {
                    'execution_id': {'type': 'str', 'description': 'Unique identifier for execution'},
                    'start_time': {'type': 'datetime', 'description': 'When execution started'},
                    'config': {'type': 'TestConfiguration', 'description': 'Original config object'},
                    'configuration_context': {'type': 'Dict', 'description': 'Serialized config with metadata'},
                    'test_runs': {'type': 'List[TestRun]', 'description': 'All test execution attempts'},
                    'llm_interactions': {'type': 'List[LLMInteraction]', 'description': 'All LLM conversations'},
                    'fix_attempts': {'type': 'List[FixAttempt]', 'description': 'All code fix attempts'},
                    'original_code_sections': {'type': 'Dict', 'description': 'Original code before fixes'},
                    'learning_history': {'type': 'Dict', 'description': 'Cumulative learning data'}
                }
            },
            'test_run_level': {
                'description': 'Individual test run data (TestRun dataclass)',
                'fields': {
                    'test_run_id': {'type': 'str', 'description': 'Unique run identifier'},
                    'attempt_number': {'type': 'int', 'description': 'Which attempt this is'},
                    'timestamp': {'type': 'datetime', 'description': 'When run occurred'},
                    'test_inputs': {'type': 'List[Dict]', 'description': 'Input data for tests'},
                    'test_outputs': {'type': 'List[Dict]', 'description': 'Output data from tests'},
                    'llm_logs': {'type': 'Dict', 'description': 'LLM interaction logs'},
                    'test_cases': {'type': 'List[Dict]', 'description': 'Individual test case details'},
                    'summary': {'type': 'Dict', 'description': 'Test summary statistics'},
                    'result': {'type': 'Dict', 'description': 'Overall result info'},
                    'failed_test_cases': {'type': 'List[Dict]', 'description': 'Failed tests only'},
                    'passed_test_cases': {'type': 'List[Dict]', 'description': 'Passed tests only'},
                    'error_test_cases': {'type': 'List[Dict]', 'description': 'Error tests only'},
                    'timing_analysis': {'type': 'Dict', 'description': 'Execution timing data'},
                    'error_analysis': {'type': 'Dict', 'description': 'Error pattern analysis'}
                }
            },
            'fix_attempt_level': {
                'description': 'Individual fix attempt data (FixAttempt dataclass)',
                'fields': {
                    'attempt_number': {'type': 'int', 'description': 'Which fix attempt'},
                    'approach_description': {'type': 'str', 'description': 'What was tried'},
                    'code_changes_made': {'type': 'str', 'description': 'Specific changes'},
                    'original_code': {'type': 'str', 'description': 'Code before fix'},
                    'modified_code': {'type': 'str', 'description': 'Code after fix'},
                    'test_results_before': {'type': 'Dict', 'description': 'Test results before fix'},
                    'test_results_after': {'type': 'Dict', 'description': 'Test results after fix'},
                    'success': {'type': 'bool', 'description': 'Whether fix worked'},
                    'llm_interaction': {'type': 'LLMInteraction', 'description': 'Complete LLM data'},
                    'lessons_learned': {'type': 'str', 'description': 'Key insights'},
                    'why_approach_failed': {'type': 'str', 'description': 'Failure analysis'},
                    'what_worked_partially': {'type': 'str', 'description': 'Partial successes'},
                    'config_context': {'type': 'Dict', 'description': 'Configuration context'}
                }
            },
            'llm_interaction_level': {
                'description': 'Individual LLM interaction data (LLMInteraction dataclass)',
                'fields': {
                    'interaction_type': {'type': 'str', 'description': 'Type of interaction'},
                    'prompt': {'type': 'str', 'description': 'Complete prompt sent'},
                    'response': {'type': 'str', 'description': 'Complete LLM response'},
                    'reasoning': {'type': 'str', 'description': 'Step-by-step reasoning'},
                    'metadata': {'type': 'Dict', 'description': 'Model details, tokens, etc.'},
                    'timestamp': {'type': 'datetime', 'description': 'When interaction occurred'}
                }
            },
            'test_case_level': {
                'description': 'Individual test case data (TestCase dataclass)',
                'fields': {
                    'test_name': {'type': 'str', 'description': 'Name of the test'},
                    'status': {'type': 'str', 'description': "'passed', 'failed', 'error'"},
                    'input': {'type': 'Any', 'description': 'Test input data'},
                    'expected_output': {'type': 'Any', 'description': 'Expected result'},
                    'actual_output': {'type': 'Any', 'description': 'Actual result'},
                    'error_message': {'type': 'str', 'description': 'Error details if failed'},
                    'failing_function': {'type': 'str', 'description': 'Function that failed'},
                    'failing_line': {'type': 'int', 'description': 'Line number of failure'},
                    'llm_logs': {'type': 'Dict', 'description': 'LLM logs for this test'}
                }
            }
        }
        
        return schema 

    def should_continue_fixing(self, file_path: str = None) -> Dict[str, Any]:
        """Determine if auto-fix should continue based on memory analysis.
        
        This method analyzes the previous fix attempts and determines if it's
        worthwhile to continue trying to fix the code. It considers factors like:
        - Number of previous attempts
        - Success rate trends
        - Whether improvements are being made
        - Configuration limits
        
        Args:
            file_path: Optional file path to analyze (if None, uses current execution)
            
        Returns:
            Dictionary with:
            - should_continue: bool - Whether to continue fixing
            - reason: str - Explanation for the decision
            - analysis: Dict - Detailed analysis data
        """
        if not self.current_execution:
            return {
                'should_continue': True,
                'reason': 'No execution history available',
                'analysis': {}
            }
        
        # Get configuration limits
        max_retries = self.get_config_value('max_retries', 3)
        if max_retries is None:
            max_retries = 3  # Default fallback
        
        # Get fix attempts for this file
        fix_attempts = self.current_execution.get('fix_attempts', [])
        file_attempts = [attempt for attempt in fix_attempts if attempt.file_path == file_path] if file_path else fix_attempts
        
        # Basic checks
        if len(file_attempts) >= max_retries:
            return {
                'should_continue': False,
                'reason': f'Maximum retry limit reached ({max_retries} attempts)',
                'analysis': {
                    'attempts_made': len(file_attempts),
                    'max_retries': max_retries
                }
            }
        
        # Analyze success patterns
        if len(file_attempts) >= 2:
            # Check if we're making progress
            success_rates = []
            for attempt in file_attempts[-3:]:  # Look at last 3 attempts
                if hasattr(attempt, 'test_results_after') and attempt.test_results_after:
                    summary = attempt.test_results_after.get('summary', {})
                    total_tests = summary.get('total_tests', 0)
                    passed_tests = summary.get('passed_tests', 0)
                    if total_tests > 0:
                        success_rates.append(passed_tests / total_tests)
            
            if len(success_rates) >= 2:
                # Check if success rate is improving
                if success_rates[-1] <= success_rates[-2]:
                    # No improvement in last attempt
                    if len(success_rates) >= 3 and success_rates[-1] <= success_rates[-3]:
                        return {
                            'should_continue': False,
                            'reason': 'No improvement in success rate over multiple attempts',
                            'analysis': {
                                'success_rates': success_rates,
                                'attempts_analyzed': len(success_rates),
                                'trend': 'declining' if success_rates[-1] < success_rates[-2] else 'stagnant'
                            }
                        }
        
        # Check for repeated failure patterns
        if len(file_attempts) >= 2:
            recent_attempts = file_attempts[-2:]
            all_failed = all(not attempt.success for attempt in recent_attempts)
            
            if all_failed:
                # Check if the same errors are occurring repeatedly
                error_patterns = []
                for attempt in recent_attempts:
                    if hasattr(attempt, 'test_results_after') and attempt.test_results_after:
                        failed_cases = attempt.test_results_after.get('failed_test_cases', [])
                        for case in failed_cases:
                            error_msg = case.get('error_message', '')
                            if error_msg:
                                error_patterns.append(error_msg)
                
                # If we have the same error patterns, it might indicate a fundamental issue
                if len(set(error_patterns)) <= 2:  # Very few unique error types
                    return {
                        'should_continue': False,
                        'reason': 'Repeated failure patterns suggest fundamental code issues',
                        'analysis': {
                            'error_patterns': list(set(error_patterns)),
                            'unique_errors': len(set(error_patterns)),
                            'recent_attempts_failed': len(recent_attempts)
                        }
                    }
        
        # Check if we've achieved significant improvement
        if len(file_attempts) >= 1:
            latest_attempt = file_attempts[-1]
            if hasattr(latest_attempt, 'test_results_after') and latest_attempt.test_results_after:
                summary = latest_attempt.test_results_after.get('summary', {})
                total_tests = summary.get('total_tests', 0)
                passed_tests = summary.get('passed_tests', 0)
                
                if total_tests > 0 and passed_tests / total_tests >= 0.8:  # 80% success rate
                    return {
                        'should_continue': False,
                        'reason': 'High success rate achieved (80%+)',
                        'analysis': {
                            'success_rate': passed_tests / total_tests,
                            'passed_tests': passed_tests,
                            'total_tests': total_tests
                        }
                    }
        
        # Default: continue fixing
        return {
            'should_continue': True,
            'reason': f'Continuing with attempt {len(file_attempts) + 1} of {max_retries}',
            'analysis': {
                'attempts_made': len(file_attempts),
                'max_retries': max_retries,
                'remaining_attempts': max_retries - len(file_attempts)
            }
        } 