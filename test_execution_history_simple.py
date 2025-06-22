#!/usr/bin/env python3
"""
Simple test for TestExecutionHistory class without importing problematic modules.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Import only the models module directly
from kaizen.cli.commands.models import (
    TestExecutionResult, TestCaseResult, TestStatus, TestExecutionHistory
)

def test_execution_history():
    """Test the TestExecutionHistory class functionality."""
    
    print("=== Testing TestExecutionHistory ===\n")
    
    # Create sample test case results
    test_case_1 = TestCaseResult(
        name="test_function_1",
        status=TestStatus.PASSED,
        input="sample input 1",
        expected_output="expected output 1",
        actual_output="expected output 1",
        evaluation="exact_match",
        execution_time=0.1,
        error=None,
        metadata={"region": "function_1"}
    )
    
    test_case_2 = TestCaseResult(
        name="test_function_2",
        status=TestStatus.FAILED,
        input="sample input 2",
        expected_output="expected output 2",
        actual_output="wrong output 2",
        evaluation="failed",
        execution_time=0.2,
        error="AssertionError: expected 'expected output 2', got 'wrong output 2'",
        metadata={"region": "function_2"}
    )
    
    # Create baseline test execution result
    baseline_result = TestExecutionResult(
        test_cases=[test_case_1, test_case_2],
        execution_time=0.3,
        metadata={"run_type": "baseline", "timestamp": "2024-01-01T10:00:00Z"}
    )
    
    # Create improved test case for fix attempt
    improved_test_case_2 = TestCaseResult(
        name="test_function_2",
        status=TestStatus.PASSED,
        input="sample input 2",
        expected_output="expected output 2",
        actual_output="expected output 2",
        evaluation="exact_match",
        execution_time=0.18,
        error=None,
        metadata={"region": "function_2", "fix_applied": True}
    )
    
    # Create fix attempt result
    fix_attempt_result = TestExecutionResult(
        test_cases=[test_case_1, improved_test_case_2],
        execution_time=0.28,
        metadata={"run_type": "fix_attempt_1", "timestamp": "2024-01-01T10:05:00Z"}
    )
    
    # Create test execution history
    history = TestExecutionHistory()
    
    print("1. Adding baseline result...")
    history.add_baseline_result(baseline_result)
    print(f"   Baseline status: {baseline_result.get_overall_status()}")
    print(f"   Failed tests: {len(baseline_result.get_failed_tests())}")
    
    print("\n2. Adding fix attempt result...")
    history.add_fix_attempt_result(fix_attempt_result)
    print(f"   Fix attempt status: {fix_attempt_result.get_overall_status()}")
    print(f"   Failed tests: {len(fix_attempt_result.get_failed_tests())}")
    
    print(f"\n3. Test execution history summary:")
    print(f"   Total runs: {len(history)}")
    print(f"   Latest result: {history.get_latest_result().get_overall_status()}")
    
    print(f"\n4. Improvement analysis:")
    improvement = history.get_improvement_summary()
    for key, value in improvement.items():
        print(f"   {key}: {value}")
    
    print(f"\n5. Failed tests progression:")
    progression = history.get_failed_tests_progression()
    for step in progression:
        print(f"   {step['run_type']}: {step['failed_count']} failed tests")
        if step['failed_tests']:
            print(f"     Failed: {', '.join(step['failed_tests'])}")
    
    print(f"\n6. All test results in chronological order:")
    all_results = history.get_all_results()
    for i, result in enumerate(all_results):
        run_type = result.metadata.get('run_type', 'unknown')
        print(f"   {i+1}. {run_type}: {result.get_overall_status()} ({len(result.get_failed_tests())} failed)")
    
    print(f"\n7. String representation:")
    print(f"   {history}")
    
    print("\n✅ TestExecutionHistory test completed successfully!")
    return history

if __name__ == "__main__":
    test_execution_history() 