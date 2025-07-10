"""Example demonstrating the unified TestExecutionResult class.

This example shows how to use the new unified test result format
and how it simplifies working with test results throughout the codebase.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from ..models import TestExecutionResult, TestCaseResult, TestStatus

def create_sample_test_result() -> TestExecutionResult:
    """Create a sample test execution result."""
    
    # Create test cases
    test_cases = [
        TestCaseResult(
            name="test_basic_functionality",
            status=TestStatus.PASSED,
            input="test_input_1",
            expected_output="expected_1",
            actual_output="expected_1",
            evaluation={"score": 0.95, "reason": "Output matches expected"},
            timestamp=datetime.now()
        ),
        TestCaseResult(
            name="test_edge_cases",
            status=TestStatus.FAILED,
            input="test_input_2",
            expected_output="expected_2",
            actual_output="actual_2",
            error_message="Test failed: output does not match expected",
            evaluation={"score": 0.3, "reason": "Output differs significantly"},
            timestamp=datetime.now()
        ),
        TestCaseResult(
            name="test_error_handling",
            status=TestStatus.ERROR,
            input="test_input_3",
            expected_output="expected_3",
            actual_output=None,
            error_message="Exception occurred during test execution",
            error_details="TypeError: unsupported operand type(s) for +: 'int' and 'str'",
            timestamp=datetime.now()
        )
    ]
    
    # Create test execution result
    result = TestExecutionResult(
        name="Sample Test Suite",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml")
    )
    
    # Add test cases
    result.add_test_cases(test_cases)
    
    return result

def demonstrate_unified_result_usage():
    """Demonstrate various ways to use the unified test result."""
    
    print("=== Unified Test Result Example ===\n")
    
    # Create a sample result
    test_result = create_sample_test_result()
    
    print(f"Test Name: {test_result.name}")
    print(f"File Path: {test_result.file_path}")
    print(f"Overall Status: {test_result.status.value}")
    print(f"Total Tests: {test_result.summary.total_tests}")
    print(f"Passed: {test_result.summary.passed_tests}")
    print(f"Failed: {test_result.summary.failed_tests}")
    print(f"Errors: {test_result.summary.error_tests}")
    print(f"Success Rate: {test_result.summary.get_success_rate():.1f}%")
    print(f"Is Successful: {test_result.is_successful()}")
    
    print("\n=== Failed Tests ===")
    failed_tests = test_result.get_failed_tests()
    for tc in failed_tests:
        print(f"- {tc.name}: {tc.get_error_summary()}")
    
    print("\n=== Tests by Status ===")
    for status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR]:
        status_tests = test_result.get_tests_by_status(status)
        print(f"{status.value}: {len(status_tests)} tests")
        for tc in status_tests:
            print(f"  - {tc.name}")
    
    print("\n=== Legacy Format Conversion ===")
    legacy_format = test_result.to_legacy_format()
    print(f"Legacy format keys: {list(legacy_format.keys())}")
    print(f"Overall status: {legacy_format['overall_status']['status']}")
    
    print("\n=== Dictionary Format ===")
    dict_format = test_result.to_dict()
    print(f"Dictionary format keys: {list(dict_format.keys())}")
    print(f"Test cases count: {len(dict_format['test_cases'])}")

def demonstrate_simplified_workflow():
    """Demonstrate the simplified workflow with the new approach."""
    
    print("\n=== Simplified Workflow Example ===\n")
    
    # Simulate what happens in the real test runner
    # (In reality, this would come from TestRunner.run_tests())
    test_result = create_sample_test_result()
    
    print("1. TestRunner returns unified TestExecutionResult directly")
    print(f"   Result type: {type(test_result)}")
    print(f"   Test name: {test_result.name}")
    
    print("\n2. Check if tests passed (no need for separate failed_tests)")
    if test_result.is_successful():
        print("   ✅ All tests passed!")
    else:
        print(f"   ❌ {test_result.get_failure_count()} tests failed")
    
    print("\n3. Get failed tests when needed (extract on demand)")
    failed_tests = test_result.get_failed_tests()
    print(f"   Failed tests: {len(failed_tests)}")
    for tc in failed_tests:
        print(f"     - {tc.name}: {tc.get_error_summary()}")
    
    print("\n4. Get specific test data easily")
    passed_tests = test_result.get_passed_tests()
    print(f"   Passed tests: {len(passed_tests)}")
    

    
    print("\n5. Access rich metadata")
    for tc in test_result.test_cases:
        print(f"   {tc.name}:")
        print(f"     Status: {tc.status.value}")
        print(f"     Input: {tc.input}")
        print(f"     Output: {tc.actual_output}")
        if tc.evaluation:
            print(f"     Evaluation score: {tc.evaluation.get('score', 'N/A')}")
        if tc.error_message:
            print(f"     Error: {tc.error_message}")
    
    print("\n6. Convert to legacy format only when needed")
    legacy_format = test_result.to_legacy_format()
    print(f"   Legacy format available for backward compatibility")

def demonstrate_backward_compatibility():
    """Demonstrate backward compatibility with legacy format."""
    
    print("\n=== Backward Compatibility Example ===\n")
    
    # Create legacy format data
    legacy_results = {
        'overall_status': {
            'status': 'failed',
            'summary': {
                'total_regions': 2,
                'passed_regions': 0,
                'failed_regions': 1,
                'error_regions': 1
            }
        },
        'test_region_1': {
            'test_cases': [{
                'name': 'test_basic_functionality',
                'status': 'failed',
                'input': 'test_input_1',
                'expected_output': 'expected_1',
                'output': 'actual_1',
                'evaluation': {'score': 0.3},
                'error': 'Test failed'
            }]
        },
        'test_region_2': {
            'test_cases': [{
                'name': 'test_error_handling',
                'status': 'error',
                'input': 'test_input_2',
                'expected_output': 'expected_2',
                'output': None,
                'error': 'Exception occurred'
            }]
        }
    }
    
    # Convert to unified format
    unified_result = TestExecutionResult.from_legacy_format(
        name="Legacy Test",
        file_path=Path("legacy_test.py"),
        config_path=Path("legacy_config.yaml"),
        legacy_results=legacy_results
    )
    
    print(f"Converted from legacy format:")
    print(f"  Name: {unified_result.name}")
    print(f"  Status: {unified_result.status.value}")
    print(f"  Total Tests: {unified_result.summary.total_tests}")
    print(f"  Failed Tests: {len(unified_result.get_failed_tests())}")
    
    # Convert back to legacy format
    converted_back = unified_result.to_legacy_format()
    print(f"\nConverted back to legacy format:")
    print(f"  Keys: {list(converted_back.keys())}")
    print(f"  Overall status: {converted_back['overall_status']['status']}")

if __name__ == "__main__":
    demonstrate_unified_result_usage()
    demonstrate_simplified_workflow()
    demonstrate_backward_compatibility() 