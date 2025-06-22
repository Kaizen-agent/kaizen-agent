#!/usr/bin/env python3
"""
Debug script to examine test results structure and understand why table generation is failing.
"""

import sys
import os
import json
from typing import Dict, Any

# Add the kaizen directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kaizen'))

def create_sample_test_results() -> Dict[str, Any]:
    """Create sample test results that might match the user's structure."""
    return {
        'overall_status': {
            'status': 'failed',
            'summary': {
                'total_regions': 6,
                'passed_regions': 5,
                'failed_regions': 1,
                'error_regions': 0
            }
        },
        'Structural complexity': {
            'test_cases': [
                {
                    'name': 'Structural complexity',  # This might be the issue - no specific test name
                    'status': 'passed',
                    'input': 'test input',
                    'expected_output': 'expected output',
                    'output': 'actual output',
                    'evaluation': 'evaluation details'
                }
            ]
        },
        "Lipinski's rule": {
            'test_cases': [
                {
                    'name': "Lipinski's rule",
                    'status': 'passed',
                    'input': 'test input',
                    'expected_output': 'expected output',
                    'output': 'actual output',
                    'evaluation': 'evaluation details'
                }
            ]
        },
        'Feedback on the model\'s progress': {
            'test_cases': [
                {
                    'name': 'Feedback on the model\'s progress',
                    'status': 'failed',
                    'input': 'test input',
                    'expected_output': 'expected output',
                    'output': 'actual output',
                    'evaluation': 'evaluation details'
                }
            ]
        },
        'Feedback on the ranked molecules': {
            'test_cases': [
                {
                    'name': 'Feedback on the ranked molecules',
                    'status': 'passed',
                    'input': 'test input',
                    'expected_output': 'expected output',
                    'output': 'actual output',
                    'evaluation': 'evaluation details'
                }
            ]
        },
        'Feedback on the evaluation rules': {
            'test_cases': [
                {
                    'name': 'Feedback on the evaluation rules',
                    'status': 'passed',
                    'input': 'test input',
                    'expected_output': 'expected output',
                    'output': 'actual output',
                    'evaluation': 'evaluation details'
                }
            ]
        },
        'Valid feedback on molecular properties': {
            'test_cases': [
                {
                    'name': 'Valid feedback on molecular properties',
                    'status': 'passed',
                    'input': 'test input',
                    'expected_output': 'expected output',
                    'output': 'actual output',
                    'evaluation': 'evaluation details'
                }
            ]
        }
    }

def convert_test_results_to_attempt(test_results: Dict, attempt_name: str) -> Dict:
    """Convert test results to Attempt format expected by PR manager.
    
    Args:
        test_results: Test results from TestRunner
        attempt_name: Name of the attempt
        
    Returns:
        Dict in Attempt format
    """
    
    # Get overall status
    overall_status = test_results.get('overall_status', {})
    status = overall_status.get('status', 'unknown')
    
    # Convert test cases
    test_cases = []
    for region_name, region_data in test_results.items():
        if region_name in ('overall_status', '_status'):
            continue
            
        if isinstance(region_data, dict):
            region_test_cases = region_data.get('test_cases', [])
            for tc in region_test_cases:
                if isinstance(tc, dict):
                    test_case = {
                        'name': f"{region_name}: {tc.get('name', 'Unknown')}",
                        'status': tc.get('status', 'unknown'),
                        'input': tc.get('input'),
                        'expected_output': tc.get('expected_output'),
                        'actual_output': tc.get('output'),
                        'evaluation': tc.get('evaluation'),
                        'reason': tc.get('error') or tc.get('details')
                    }
                    test_cases.append(test_case)
    
    # Create Attempt structure
    attempt = {
        'status': status,
        'test_cases': test_cases
    }
    
    return attempt

def debug_test_structure():
    """Debug the test results structure and conversion."""
    print("Debugging test results structure...")
    
    # Create sample test results
    test_results = create_sample_test_results()
    
    print("\n" + "="*80)
    print("ORIGINAL TEST RESULTS STRUCTURE:")
    print("="*80)
    print(json.dumps(test_results, indent=2))
    
    # Convert to attempt format
    attempt = convert_test_results_to_attempt(test_results, "Test Attempt")
    
    print("\n" + "="*80)
    print("CONVERTED ATTEMPT STRUCTURE:")
    print("="*80)
    print(json.dumps(attempt, indent=2))
    
    # Check what test case names we have
    print("\n" + "="*80)
    print("TEST CASE NAMES:")
    print("="*80)
    for tc in attempt['test_cases']:
        print(f"- {tc['name']}")
    
    # Now let's simulate what happens in the table generation
    from kaizen.autofix.pr.manager import PRManager
    
    # Create test results for PR
    test_results_for_pr = {
        'agent_info': {
            'name': 'Test Agent',
            'version': '1.0.0',
            'description': 'Test agent'
        },
        'attempts': [
            attempt,  # Baseline
            attempt,  # Attempt 1 (same for testing)
            attempt   # Attempt 2 (same for testing)
        ],
        'additional_summary': 'Test summary'
    }
    
    # Generate table
    pr_manager = PRManager({'create_pr': False})
    table = pr_manager._generate_test_results_table(test_results_for_pr)
    
    print("\n" + "="*80)
    print("GENERATED TABLE:")
    print("="*80)
    print(table)
    
    # Let's also check what the table generation function expects
    print("\n" + "="*80)
    print("TABLE GENERATION ANALYSIS:")
    print("="*80)
    
    attempts = test_results_for_pr['attempts']
    baseline_attempt = attempts[0]
    test_case_names = [tc['name'] for tc in baseline_attempt['test_cases']]
    
    print(f"Number of attempts: {len(attempts)}")
    print(f"Test case names from baseline: {test_case_names}")
    
    for i, attempt in enumerate(attempts):
        print(f"\nAttempt {i} test cases:")
        for tc in attempt['test_cases']:
            print(f"  - {tc['name']}: {tc['status']}")

if __name__ == "__main__":
    debug_test_structure() 