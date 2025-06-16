"""Test utility functions."""

from typing import Dict, Any, List

def collect_failed_tests(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect all failed tests from the test results dictionary.
    
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