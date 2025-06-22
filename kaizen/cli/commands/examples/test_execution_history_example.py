#!/usr/bin/env python3
"""
Example demonstrating the TestExecutionHistory class for unified test result management.

This example shows how TestExecutionHistory provides a consistent way to store and analyze
all test execution results from baseline tests, fix attempts, and final results.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from kaizen.cli.commands.models import (
    TestExecutionResult, TestCaseResult, TestStatus, TestExecutionHistory
)
from kaizen.autofix.test.runner import TestRunner

def create_sample_test_results():
    """Create sample test results for demonstration."""
    
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
    
    test_case_3 = TestCaseResult(
        name="test_function_3",
        status=TestStatus.PASSED,
        input="sample input 3",
        expected_output="expected output 3",
        actual_output="expected output 3",
        evaluation="exact_match",
        execution_time=0.15,
        error=None,
        metadata={"region": "function_3"}
    )
    
    # Create baseline test execution result
    baseline_result = TestExecutionResult(
        test_cases=[test_case_1, test_case_2, test_case_3],
        execution_time=0.45,
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
        test_cases=[test_case_1, improved_test_case_2, test_case_3],
        execution_time=0.43,
        metadata={"run_type": "fix_attempt_1", "timestamp": "2024-01-01T10:05:00Z"}
    )
    
    # Create final result (same as fix attempt but marked as final)
    final_result = TestExecutionResult(
        test_cases=[test_case_1, improved_test_case_2, test_case_3],
        execution_time=0.42,
        metadata={"run_type": "final", "timestamp": "2024-01-01T10:10:00Z"}
    )
    
    return baseline_result, fix_attempt_result, final_result

def demonstrate_test_execution_history():
    """Demonstrate the TestExecutionHistory class functionality."""
    
    print("=== TestExecutionHistory Demonstration ===\n")
    
    # Create sample test results
    baseline, fix_attempt, final = create_sample_test_results()
    
    # Create test execution history
    history = TestExecutionHistory()
    
    print("1. Adding baseline result...")
    history.add_baseline_result(baseline)
    print(f"   Baseline status: {baseline.get_overall_status()}")
    print(f"   Failed tests: {len(baseline.get_failed_tests())}")
    
    print("\n2. Adding fix attempt result...")
    history.add_fix_attempt_result(fix_attempt)
    print(f"   Fix attempt status: {fix_attempt.get_overall_status()}")
    print(f"   Failed tests: {len(fix_attempt.get_failed_tests())}")
    
    print("\n3. Setting final result...")
    history.set_final_result(final)
    print(f"   Final status: {final.get_overall_status()}")
    print(f"   Failed tests: {len(final.get_failed_tests())}")
    
    print(f"\n4. Test execution history summary:")
    print(f"   Total runs: {len(history)}")
    print(f"   Latest result: {history.get_latest_result().get_overall_status()}")
    
    print(f"\n5. Improvement analysis:")
    improvement = history.get_improvement_summary()
    for key, value in improvement.items():
        print(f"   {key}: {value}")
    
    print(f"\n6. Failed tests progression:")
    progression = history.get_failed_tests_progression()
    for step in progression:
        print(f"   {step['run_type']}: {step['failed_count']} failed tests")
        if step['failed_tests']:
            print(f"     Failed: {', '.join(step['failed_tests'])}")
    
    print(f"\n7. All test results in chronological order:")
    all_results = history.get_all_results()
    for i, result in enumerate(all_results):
        run_type = result.metadata.get('run_type', 'unknown')
        print(f"   {i+1}. {run_type}: {result.get_overall_status()} ({len(result.get_failed_tests())} failed)")
    
    print(f"\n8. Legacy format conversion:")
    legacy_format = history.to_legacy_format()
    print(f"   Keys in legacy format: {list(legacy_format.keys())}")
    
    print(f"\n9. String representation:")
    print(f"   {history}")
    
    return history

def demonstrate_usage_patterns():
    """Demonstrate common usage patterns with TestExecutionHistory."""
    
    print("\n=== Usage Patterns ===\n")
    
    history = TestExecutionHistory()
    
    # Pattern 1: Progressive test result tracking
    print("Pattern 1: Progressive test result tracking")
    print("   - Add baseline result")
    print("   - Add each fix attempt result")
    print("   - Set final result when done")
    print("   - Use get_latest_result() for current state")
    
    # Pattern 2: Improvement analysis
    print("\nPattern 2: Improvement analysis")
    print("   - Use get_improvement_summary() for overall progress")
    print("   - Use get_failed_tests_progression() for detailed tracking")
    print("   - Compare baseline vs latest for success metrics")
    
    # Pattern 3: Complete history access
    print("\nPattern 3: Complete history access")
    print("   - Use get_all_results() for chronological access")
    print("   - Use len(history) for total run count")
    print("   - Use to_legacy_format() for backward compatibility")
    
    # Pattern 4: Integration with AutoFix
    print("\nPattern 4: Integration with AutoFix")
    print("   - AutoFix creates TestExecutionHistory internally")
    print("   - All test runs are automatically tracked")
    print("   - Results include complete test history")
    print("   - PR creation uses unified test history")

if __name__ == "__main__":
    # Run the demonstration
    history = demonstrate_test_execution_history()
    demonstrate_usage_patterns()
    
    print("\n=== Benefits of TestExecutionHistory ===")
    print("✅ Unified storage: All test results in one place")
    print("✅ Consistent format: Same structure for all runs")
    print("✅ Rich analysis: Built-in improvement tracking")
    print("✅ Easy comparison: Compare any two test runs")
    print("✅ Backward compatibility: Legacy format support")
    print("✅ Progressive tracking: See how tests improve over time")
    print("✅ Simplified API: One class handles all test result needs") 