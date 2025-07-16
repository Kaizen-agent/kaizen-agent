#!/usr/bin/env python3
"""Test script for the analyze_fix_attempt method."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kaizen.cli.commands.memory import ExecutionMemory

print(f"Loaded ExecutionMemory from: {ExecutionMemory.__module__}")
print(f"File: {os.path.abspath(sys.modules[ExecutionMemory.__module__].__file__)}")

def test_analyze_fix_attempt():
    """Test the analyze_fix_attempt method with sample data."""
    
    # Create memory instance
    memory = ExecutionMemory()
    
    # Sample test results before fix
    test_results_before = {
        'summary': {
            'total_tests': 10,
            'passed_tests': 3,
            'failed_tests': 5,
            'error_tests': 2
        },
        'failed_test_cases': [
            {
                'name': 'test_function_1',
                'error_message': 'TypeError: unsupported operand type(s) for +: \'int\' and \'str\'',
                'failing_function': 'calculate_sum',
                'failing_line': 15
            },
            {
                'name': 'test_function_2', 
                'error_message': 'AttributeError: \'NoneType\' object has no attribute \'process\'',
                'failing_function': 'process_data',
                'failing_line': 23
            }
        ]
    }
    
    # Sample test results after fix
    test_results_after = {
        'summary': {
            'total_tests': 10,
            'passed_tests': 7,
            'failed_tests': 2,
            'error_tests': 1
        },
        'failed_test_cases': [
            {
                'name': 'test_function_2',
                'error_message': 'AttributeError: \'NoneType\' object has no attribute \'process\'',
                'failing_function': 'process_data',
                'failing_line': 23
            }
        ]
    }
    
    print("Testing analyze_fix_attempt method...")
    print("=" * 50)
    
    # Test the method
    lessons_learned, why_approach_failed, what_worked_partially = memory.analyze_fix_attempt(
        test_results_before, test_results_after
    )
    
    print("RESULTS:")
    print(f"Lessons Learned: {lessons_learned}")
    print(f"Why Approach Failed: {why_approach_failed}")
    print(f"What Worked Partially: {what_worked_partially}")
    
    # Test with fallback (no API key)
    print("\n" + "=" * 50)
    print("Testing fallback analysis (no API key)...")
    
    # Temporarily remove API key
    original_api_key = os.environ.get("GOOGLE_API_KEY")
    if "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]
    
    try:
        lessons_learned, why_approach_failed, what_worked_partially = memory.analyze_fix_attempt(
            test_results_before, test_results_after
        )
        
        print("FALLBACK RESULTS:")
        print(f"Lessons Learned: {lessons_learned}")
        print(f"Why Approach Failed: {why_approach_failed}")
        print(f"What Worked Partially: {what_worked_partially}")
        
    finally:
        # Restore API key
        if original_api_key:
            os.environ["GOOGLE_API_KEY"] = original_api_key
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    test_analyze_fix_attempt() 