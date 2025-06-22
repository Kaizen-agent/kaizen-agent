"""Test utility functions."""

from typing import Dict, Any, List, Optional
from pathlib import Path

from ..cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus

def collect_failed_tests(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect all failed tests from the legacy test results dictionary.
    
    This function is kept for backward compatibility with legacy code.
    For new code, use TestExecutionResult.get_failed_tests() instead.
    
    Args:
        results: Dictionary containing test results by region
        
    Returns:
        List of dictionaries containing failed test information
    """
    failed_tests = []
    
    # Check overall status first
    overall_status = results.get('overall_status', {})
    if overall_status.get('status') == 'failed':
        # Add overall failure if there's an error message
        if 'error' in overall_status:
            failed_tests.append({
                'region': 'overall',
                'test_name': 'Overall Test Execution',
                'error_message': overall_status['error'],
                'output': 'No output available'
            })
        
        # Add evaluation failure if present
        if 'evaluation' in overall_status:
            eval_results = overall_status['evaluation']
            if eval_results.get('status') == 'failed':
                failed_tests.append({
                    'region': 'evaluation',
                    'test_name': 'LLM Evaluation',
                    'error_message': f"Evaluation failed with score: {eval_results.get('overall_score')}",
                    'output': str(eval_results.get('criteria', {}))
                })
        
        # Add evaluation error if present
        if 'evaluation_error' in overall_status:
            failed_tests.append({
                'region': 'evaluation',
                'test_name': 'LLM Evaluation',
                'error_message': overall_status['evaluation_error'],
                'output': 'No output available'
            })
    
    # Check individual test cases
    for region, result in results.items():
        if region == 'overall_status':
            continue
            
        if not isinstance(result, dict):
            continue
            
        test_cases = result.get('test_cases', [])
        if not isinstance(test_cases, list):
            continue
            
        for test_case in test_cases:
            if not isinstance(test_case, dict):
                continue
                
            if test_case.get('status') == 'failed':
                failed_tests.append({
                    'region': region,
                    'test_name': test_case.get('name', 'Unknown Test'),
                    'error_message': test_case.get('details', 'Test failed'),
                    'input': test_case.get('input', 'No input available'),
                    'output': test_case.get('output', 'No output available'),
                    'evaluation': test_case.get('evaluation', {})
                })
    
    return failed_tests

def get_failed_tests_dict_from_unified(test_result: TestExecutionResult) -> List[Dict[str, Any]]:
    """
    Get failed test cases from a unified TestExecutionResult in the legacy dictionary format.
    
    This function is used for backward compatibility with auto-fix and other legacy systems.
    For new code, use test_result.get_failed_tests() directly.
    
    Args:
        test_result: TestExecutionResult object
        
    Returns:
        List of dictionaries containing failed test information (legacy format)
    """
    failed_tests = []
    for tc in test_result.get_failed_tests():
        failed_tests.append({
            'region': tc.region,
            'test_name': tc.name,
            'error_message': tc.get_error_summary(),
            'input': tc.input,
            'output': tc.actual_output,
            'evaluation': tc.evaluation
        })
    return failed_tests

def create_test_execution_result(name: str, file_path: Path, config_path: Path, 
                               test_cases: Optional[List[TestCaseResult]] = None) -> TestExecutionResult:
    """
    Create a new TestExecutionResult with the given parameters.
    
    Args:
        name: Test name
        file_path: Path to the test file
        config_path: Path to the config file
        test_cases: Optional list of test cases to add
        
    Returns:
        TestExecutionResult object
    """
    result = TestExecutionResult(
        name=name,
        file_path=file_path,
        config_path=config_path
    )
    
    if test_cases:
        result.add_test_cases(test_cases)
    
    return result

def is_test_successful(test_result: TestExecutionResult) -> bool:
    """
    Check if a test execution was successful.
    
    Args:
        test_result: TestExecutionResult object
        
    Returns:
        True if all tests passed, False otherwise
    """
    return test_result.is_successful()

def get_test_summary(test_result: TestExecutionResult) -> Dict[str, Any]:
    """
    Get a summary of test execution results.
    
    Args:
        test_result: TestExecutionResult object
        
    Returns:
        Dictionary containing test summary
    """
    return test_result.summary.to_dict() 