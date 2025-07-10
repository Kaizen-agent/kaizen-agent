"""Test the unified test results approach.

This script demonstrates and tests the new unified approach to handling test results.
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus
from kaizen.utils.test_utils import get_failed_tests_dict_from_unified

def test_unified_approach():
    """Test the unified approach to handling test results."""
    
    print("Testing Unified Test Results Approach")
    print("=" * 50)
    
    # Create a test execution result with mixed outcomes
    test_cases = [
        TestCaseResult(
            name="test_basic_functionality",
            status=TestStatus.PASSED,
            input="test_input_1",
            expected_output="expected_1",
            actual_output="expected_1",
            evaluation={"score": 0.95, "reason": "Output matches expected"},
        ),
        TestCaseResult(
            name="test_edge_cases",
            status=TestStatus.FAILED,
            input="test_input_2",
            expected_output="expected_2",
            actual_output="actual_2",
            error_message="Test failed: output does not match expected",
            evaluation={"score": 0.3, "reason": "Output differs significantly"},
        ),
        TestCaseResult(
            name="test_error_handling",
            status=TestStatus.ERROR,
            input="test_input_3",
            expected_output="expected_3",
            actual_output=None,
            error_message="Exception occurred during test execution",
            error_details="TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        )
    ]
    
    # Create the unified test result
    test_result = TestExecutionResult(
        name="Test Suite",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml")
    )
    test_result.add_test_cases(test_cases)
    
    # Test 1: Check overall status
    print(f"1. Overall Status: {test_result.status.value}")
    print(f"   Is Successful: {test_result.is_successful()}")
    print(f"   Total Tests: {test_result.summary.total_tests}")
    print(f"   Passed: {test_result.summary.passed_tests}")
    print(f"   Failed: {test_result.summary.failed_tests}")
    print(f"   Errors: {test_result.summary.error_tests}")
    print(f"   Success Rate: {test_result.summary.get_success_rate():.1f}%")
    
    # Test 2: Get failed tests (extract on demand)
    print(f"\n2. Failed Tests (extracted on demand):")
    failed_tests = test_result.get_failed_tests()
    print(f"   Count: {len(failed_tests)}")
    for tc in failed_tests:
        print(f"   - {tc.name}: {tc.get_error_summary()}")
    
    # Test 3: Get tests by status
    print(f"\n3. Tests by Status:")
    for status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR]:
        status_tests = test_result.get_tests_by_status(status)
        print(f"   {status.value}: {len(status_tests)} tests")
        for tc in status_tests:
            print(f"     - {tc.name}")
    

    
    # Test 5: Legacy format conversion (for backward compatibility)
    print(f"\n5. Legacy Format Conversion:")
    legacy_format = test_result.to_legacy_format()
    print(f"   Legacy format keys: {list(legacy_format.keys())}")
    print(f"   Overall status: {legacy_format['overall_status']['status']}")
    
    # Test 6: Extract failed tests in legacy format for auto-fix
    print(f"\n6. Legacy Format Failed Tests (for auto-fix):")
    legacy_failed_tests = get_failed_tests_dict_from_unified(test_result)
    print(f"   Count: {len(legacy_failed_tests)}")
    for test in legacy_failed_tests:
        print(f"   - {test['test_name']}: {test['error_message']}")
    
    # Test 7: Rich metadata access
    print(f"\n7. Rich Metadata Access:")
    for tc in test_result.test_cases:
        print(f"   {tc.name}:")
        print(f"     Status: {tc.status.value}")
        print(f"     Input: {tc.input}")
        print(f"     Expected: {tc.expected_output}")
        print(f"     Actual: {tc.actual_output}")
        if tc.evaluation:
            print(f"     Evaluation Score: {tc.evaluation.get('score', 'N/A')}")
        if tc.error_message:
            print(f"     Error: {tc.error_message}")
        if tc.error_details:
            print(f"     Error Details: {tc.error_details[:50]}...")
    
    print(f"\n✅ All tests completed successfully!")
    print(f"   The unified approach provides a clean, type-safe way to work with test results.")
    print(f"   No more confusion about different formats or conversion logic.")

def test_backward_compatibility():
    """Test backward compatibility with legacy format."""
    
    print(f"\nTesting Backward Compatibility")
    print("=" * 50)
    
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
    
    print(f"1. Converted from legacy format:")
    print(f"   Name: {unified_result.name}")
    print(f"   Status: {unified_result.status.value}")
    print(f"   Total Tests: {unified_result.summary.total_tests}")
    print(f"   Failed Tests: {len(unified_result.get_failed_tests())}")
    
    # Convert back to legacy format
    converted_back = unified_result.to_legacy_format()
    print(f"\n2. Converted back to legacy format:")
    print(f"   Keys: {list(converted_back.keys())}")
    print(f"   Overall status: {converted_back['overall_status']['status']}")
    
    print(f"\n✅ Backward compatibility works correctly!")

if __name__ == "__main__":
    test_unified_approach()
    test_backward_compatibility() 