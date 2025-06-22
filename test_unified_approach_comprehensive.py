#!/usr/bin/env python3
"""
Comprehensive test for the unified test result approach.

This test covers:
1. TestExecutionResult creation and methods
2. TestExecutionHistory functionality
3. End-to-end workflow
4. Backward compatibility
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime

# Import the unified models
from kaizen.cli.commands.models import (
    TestExecutionResult, TestCaseResult, TestStatus, TestExecutionHistory
)

def test_test_execution_result_creation():
    """Test TestExecutionResult creation and basic functionality."""
    
    # Create sample test cases
    test_case_1 = TestCaseResult(
        name="test_function_1",
        status=TestStatus.PASSED,
        region="function_1",
        input="sample input 1",
        expected_output="expected output 1",
        actual_output="expected output 1",
        evaluation="exact_match",
        execution_time=0.1,
        error_message=None,
        metadata={"region": "function_1"}
    )
    
    test_case_2 = TestCaseResult(
        name="test_function_2",
        status=TestStatus.FAILED,
        region="function_2",
        input="sample input 2",
        expected_output="expected output 2",
        actual_output="wrong output 2",
        evaluation="failed",
        execution_time=0.2,
        error_message="AssertionError: expected 'expected output 2', got 'wrong output 2'",
        metadata={"region": "function_2"}
    )
    
    # Create TestExecutionResult
    result = TestExecutionResult(
        name="test_run",
        file_path=Path("dummy.py"),
        config_path=Path("dummy.yaml"),
        test_cases=[test_case_1, test_case_2],
        metadata={"run_type": "test", "timestamp": "2024-01-01T10:00:00Z"}
    )
    
    # Test basic properties
    assert len(result.test_cases) == 2
    assert result.metadata["run_type"] == "test"
    
    # Test status methods
    assert not result.is_successful()
    assert result.get_failure_count() == 1
    assert result.summary.passed_tests == 1
    assert result.status.value == "failed"
    
    # Test failed tests extraction
    failed_tests = result.get_failed_tests()
    assert len(failed_tests) == 1
    assert failed_tests[0].name == "test_function_2"
    
    # Test passed tests extraction
    passed_tests = result.get_passed_tests()
    assert len(passed_tests) == 1
    assert passed_tests[0].name == "test_function_1"
    
    # Test legacy format conversion
    legacy_format = result.to_legacy_format()
    assert "overall_status" in legacy_format
    assert legacy_format["overall_status"]["status"] == "failed"
    
    print("✅ TestExecutionResult creation and methods work correctly")

def test_test_execution_history():
    """Test TestExecutionHistory functionality."""
    
    # Create sample test results
    baseline_result = TestExecutionResult(
        name="baseline_test_run",
        file_path=Path("dummy.py"),
        config_path=Path("dummy.yaml"),
        test_cases=[
            TestCaseResult(
                name="test_1",
                status=TestStatus.PASSED,
                region="input1",
                input="input1",
                expected_output="output1",
                actual_output="output1",
                evaluation="exact_match",
                execution_time=0.1,
                error_message=None,
                metadata={}
            ),
            TestCaseResult(
                name="test_2",
                status=TestStatus.FAILED,
                region="input2",
                input="input2",
                expected_output="output2",
                actual_output="wrong",
                evaluation="failed",
                execution_time=0.2,
                error_message="AssertionError",
                metadata={}
            )
        ],
        metadata={"run_type": "baseline"}
    )
    
    fix_attempt_result = TestExecutionResult(
        name="fix_attempt_1_test_run",
        file_path=Path("dummy.py"),
        config_path=Path("dummy.yaml"),
        test_cases=[
            TestCaseResult(
                name="test_1",
                status=TestStatus.PASSED,
                region="input1",
                input="input1",
                expected_output="output1",
                actual_output="output1",
                evaluation="exact_match",
                execution_time=0.1,
                error_message=None,
                metadata={}
            ),
            TestCaseResult(
                name="test_2",
                status=TestStatus.PASSED,  # Fixed!
                region="input2",
                input="input2",
                expected_output="output2",
                actual_output="output2",
                evaluation="exact_match",
                execution_time=0.15,
                error_message=None,
                metadata={}
            )
        ],
        metadata={"run_type": "fix_attempt_1"}
    )
    
    # Create and populate history
    history = TestExecutionHistory()
    history.add_baseline_result(baseline_result)
    history.add_fix_attempt_result(fix_attempt_result)
    
    # Test basic functionality
    assert len(history) == 2
    assert history.get_latest_result() == fix_attempt_result
    assert len(history.get_all_results()) == 2
    
    # Test improvement analysis
    improvement = history.get_improvement_summary()
    assert improvement["baseline_failed"] == 1
    assert improvement["current_failed"] == 0
    assert improvement["improvement"] == 1
    assert improvement["has_improvement"] == True
    assert improvement["all_passed"] == True
    
    # Test failed tests progression
    progression = history.get_failed_tests_progression()
    assert len(progression) == 2
    assert progression[0]["run_type"] == "baseline"
    assert progression[0]["failed_count"] == 1
    assert progression[1]["run_type"] == "fix_attempt_1"
    assert progression[1]["failed_count"] == 0
    
    # Test legacy format conversion
    legacy_format = history.to_legacy_format()
    assert "baseline" in legacy_format
    assert "fix_attempts" in legacy_format
    assert "improvement_summary" in legacy_format
    
    print("✅ TestExecutionHistory functionality works correctly")

def test_end_to_end_workflow():
    """Test the complete end-to-end workflow."""
    
    # 1. Create baseline test result
    baseline_result = TestExecutionResult(
        name="baseline_test_run",
        file_path=Path("dummy.py"),
        config_path=Path("dummy.yaml"),
        test_cases=[
            TestCaseResult(
                name="test_function",
                status=TestStatus.FAILED,
                region="test input",
                input="test input",
                expected_output="expected output",
                actual_output="wrong output",
                evaluation="failed",
                execution_time=0.1,
                error_message="AssertionError",
                metadata={"region": "function"}
            )
        ],
        metadata={"run_type": "baseline"}
    )
    
    # 2. Create test execution history
    history = TestExecutionHistory()
    history.add_baseline_result(baseline_result)
    
    # 3. Simulate a fix attempt
    fixed_result = TestExecutionResult(
        name="fix_attempt_1_test_run",
        file_path=Path("dummy.py"),
        config_path=Path("dummy.yaml"),
        test_cases=[
            TestCaseResult(
                name="test_function",
                status=TestStatus.PASSED,
                region="test input",
                input="test input",
                expected_output="expected output",
                actual_output="expected output",
                evaluation="exact_match",
                execution_time=0.1,
                error_message=None,
                metadata={"region": "function", "fix_applied": True}
            )
        ],
        metadata={"run_type": "fix_attempt_1"}
    )
    history.add_fix_attempt_result(fixed_result)
    
    # 4. Set final result
    history.set_final_result(fixed_result)
    
    # 5. Verify the complete workflow
    assert len(history) == 3  # baseline + fix_attempt + final
    assert history.get_latest_result() == fixed_result
    assert history.get_latest_result().is_successful()
    
    # 6. Test improvement analysis
    improvement = history.get_improvement_summary()
    assert improvement["baseline_failed"] == 1
    assert improvement["current_failed"] == 0
    assert improvement["improvement"] == 1
    assert improvement["has_improvement"] == True
    assert improvement["all_passed"] == True
    
    # 7. Test failed tests progression
    progression = history.get_failed_tests_progression()
    assert len(progression) == 3
    assert progression[0]["failed_count"] == 1  # baseline
    assert progression[1]["failed_count"] == 0  # fix attempt
    assert progression[2]["failed_count"] == 0  # final
    
    # 8. Test legacy format conversion
    legacy_format = history.to_legacy_format()
    assert "baseline" in legacy_format
    assert "fix_attempts" in legacy_format
    assert "final" in legacy_format
    assert "improvement_summary" in legacy_format
    
    print("✅ End-to-end workflow works correctly")

def test_backward_compatibility():
    """Test backward compatibility with legacy formats."""
    
    # Create a test execution result
    test_result = TestExecutionResult(
        name="test_run",
        file_path=Path("dummy.py"),
        config_path=Path("dummy.yaml"),
        test_cases=[
            TestCaseResult(
                name="test_1",
                status=TestStatus.PASSED,
                region="input1",
                input="input1",
                expected_output="output1",
                actual_output="output1",
                evaluation="exact_match",
                execution_time=0.1,
                error_message=None,
                metadata={}
            ),
            TestCaseResult(
                name="test_2",
                status=TestStatus.FAILED,
                region="input2",
                input="input2",
                expected_output="output2",
                actual_output="wrong",
                evaluation="failed",
                execution_time=0.2,
                error_message="AssertionError",
                metadata={}
            )
        ],
        metadata={"run_type": "test"}
    )
    
    # Convert to legacy format
    legacy_format = test_result.to_legacy_format()
    
    # Verify legacy format structure
    assert "overall_status" in legacy_format
    assert "input1" in legacy_format
    assert "input2" in legacy_format
    
    # Verify test case structure
    assert "test_cases" in legacy_format["input1"]
    assert "test_cases" in legacy_format["input2"]
    
    # Verify overall status
    summary = legacy_format["overall_status"]["summary"]
    assert summary["total_tests"] == 2
    assert summary["passed_tests"] == 1
    assert summary["failed_tests"] == 1
    
    print("✅ Backward compatibility works correctly")

if __name__ == "__main__":
    print("Running comprehensive tests for unified test result approach...\n")
    
    try:
        test_test_execution_result_creation()
        test_test_execution_history()
        test_end_to_end_workflow()
        test_backward_compatibility()
        
        print("\n🎉 All tests passed! The unified test result approach is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 