"""Test script for enhanced memory logging.

This script tests that the enhanced memory logging captures all valuable
information from TestExecutionResult including individual test cases,
detailed summaries, timing information, and metadata.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent))

from memory import ExecutionMemory


def create_mock_test_results() -> Dict[str, Any]:
    """Create mock test results in the comprehensive memory format."""
    
    test_cases = [
        {
            'name': 'test_valid_input',
            'status': 'passed',
            'input': 'hello',
            'expected_output': 'HELLO',
            'actual_output': 'HELLO',
            'error_message': None,
            'error_details': None,
            'evaluation': {'score': 1.0, 'reason': 'Exact match'},
            'evaluation_score': 1.0,
            'execution_time': 0.1,
            'timestamp': datetime.now().isoformat(),
            'metadata': {'test_type': 'unit', 'category': 'string_processing'},
            'is_failed': False,
            'is_passed': True,
            'error_summary': None
        },
        {
            'name': 'test_invalid_input',
            'status': 'failed',
            'input': 123,
            'expected_output': 'HELLO',
            'actual_output': None,
            'error_message': 'TypeError: Input must be a string',
            'error_details': 'Function expects string but received int',
            'evaluation': {'score': 0.0, 'reason': 'Type error'},
            'evaluation_score': 0.0,
            'execution_time': 0.05,
            'timestamp': datetime.now().isoformat(),
            'metadata': {'test_type': 'unit', 'category': 'error_handling'},
            'is_failed': True,
            'is_passed': False,
            'error_summary': 'TypeError: Input must be a string'
        },
        {
            'name': 'test_empty_string',
            'status': 'error',
            'input': '',
            'expected_output': '',
            'actual_output': None,
            'error_message': 'ValueError: Empty string not allowed',
            'error_details': 'Function should handle empty strings gracefully',
            'evaluation': {'score': 0.0, 'reason': 'Value error'},
            'evaluation_score': 0.0,
            'execution_time': 0.02,
            'timestamp': datetime.now().isoformat(),
            'metadata': {'test_type': 'unit', 'category': 'edge_cases'},
            'is_failed': True,
            'is_passed': False,
            'error_summary': 'ValueError: Empty string not allowed'
        }
    ]
    
    summary = {
        'total_tests': 3,
        'passed_tests': 1,
        'failed_tests': 1,
        'error_tests': 1,
        'skipped_tests': 0,
        'success_rate': 33.33,
        'is_successful': False,
        'start_time': datetime.now().isoformat(),
        'end_time': datetime.now().isoformat(),
        'total_execution_time': 0.17
    }
    
    result = {
        'name': 'test_string_processor',
        'file_path': 'example.py',
        'config_path': 'config.yaml',
        'status': 'failed',
        'error_message': '2 out of 3 tests failed',
        'error_details': 'Type and value errors in string processing',
        'start_time': datetime.now().isoformat(),
        'end_time': datetime.now().isoformat(),
        'metadata': {'framework': 'pytest', 'language': 'python'},
        'is_successful': False,
        'get_failure_count': 2,
        'get_failed_tests_count': 2,
        'get_passed_tests_count': 1
    }
    
    failed_test_cases = [tc for tc in test_cases if tc['is_failed']]
    passed_test_cases = [tc for tc in test_cases if tc['is_passed']]
    error_test_cases = [tc for tc in test_cases if tc['status'] in ['error', 'failed']]
    
    timing_analysis = {
        'total_execution_time': 0.17,
        'average_test_time': 0.17 / 3,
        'start_time': summary['start_time'],
        'end_time': summary['end_time']
    }
    
    error_analysis = {
        'total_errors': 2,
        'unique_error_types': ['TypeError: Input must be a string', 'ValueError: Empty string not allowed'],
        'most_common_error': 'TypeError: Input must be a string'
    }
    
    return {
        'test_cases': test_cases,
        'summary': summary,
        'result': result,
        'inputs': [],
        'outputs': [],
        'llm_logs': {},
        'evaluation_results': None,
        'code_fix_attempt': None,
        'attempt_outcome': {
            'success': False,
            'total_tests': 3,
            'passed_tests': 1,
            'failed_tests': 1,
            'error_tests': 1,
            'skipped_tests': 0,
            'success_rate': 33.33,
            'failure_count': 2
        },
        'failed_test_cases': failed_test_cases,
        'passed_test_cases': passed_test_cases,
        'error_test_cases': error_test_cases,
        'timing_analysis': timing_analysis,
        'error_analysis': error_analysis
    }


def test_enhanced_memory_logging():
    """Test that enhanced memory logging captures all valuable information."""
    
    print("🧪 Testing Enhanced Memory Logging")
    print("=" * 50)
    
    # Initialize memory
    memory = ExecutionMemory()
    execution_id = "enhanced_test_001"
    
    # Start execution
    config = {'name': 'enhanced_test', 'auto_fix': True}
    memory.start_execution(execution_id, config)
    print("✅ Started execution tracking")
    
    # Create mock test results in comprehensive format
    test_results = create_mock_test_results()
    print(f"✅ Created mock test results with {len(test_results['test_cases'])} test cases")
    
    # Log to memory
    test_metadata = {
        'start_time': datetime.now(),
        'config': config,
        'environment': 'test environment'
    }
    
    memory.log_test_run(
        file_path="example.py",
        test_results=test_results,
        run_metadata=test_metadata
    )
    print("✅ Logged test run to memory")
    
    # Verify comprehensive data was captured
    current_execution = memory.current_execution
    test_runs = current_execution['test_runs']
    
    if not test_runs:
        print("❌ No test runs found in memory")
        return False
    
    latest_run = test_runs[0]
    
    # Check that comprehensive data was captured
    checks = [
        ("test_cases", len(latest_run.test_cases) == 3),
        ("summary", latest_run.summary is not None),
        ("result", latest_run.result is not None),
        ("failed_test_cases", len(latest_run.failed_test_cases) == 2),
        ("passed_test_cases", len(latest_run.passed_test_cases) == 1),
        ("error_test_cases", len(latest_run.error_test_cases) == 2),
        ("timing_analysis", latest_run.timing_analysis is not None),
        ("error_analysis", latest_run.error_analysis is not None)
    ]
    
    print("\n📊 Verification Results:")
    print("-" * 30)
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            all_passed = False
    
    # Test comprehensive analysis
    analysis = memory.get_comprehensive_test_analysis()
    if analysis:
        print(f"\n📈 Comprehensive Analysis:")
        print(f"  - Total runs: {analysis.get('total_runs', 0)}")
        print(f"  - Overall statistics: {analysis.get('overall_statistics', {})}")
        print(f"  - Error patterns: {analysis.get('error_patterns', {})}")
        print(f"  - Timing patterns: {analysis.get('timing_patterns', {})}")
        print("✅ Comprehensive analysis generated")
    else:
        print("❌ Failed to generate comprehensive analysis")
        all_passed = False
    
    # Test failed cases extraction
    failed_cases = memory.get_failed_cases_latest_run()
    if len(failed_cases) == 2:  # 1 failed + 1 error
        print(f"✅ Extracted {len(failed_cases)} failed cases")
    else:
        print(f"❌ Expected 2 failed cases, got {len(failed_cases)}")
        all_passed = False
    
    # Test best attempt finding
    best_attempt = memory.find_best_attempt()
    if best_attempt:
        print(f"✅ Found best attempt with success rate: {best_attempt.get('success_rate', 0):.2%}")
    else:
        print("❌ Failed to find best attempt")
        all_passed = False
    
    print(f"\n🎯 Overall Test Result: {'PASSED' if all_passed else 'FAILED'}")
    return all_passed


if __name__ == "__main__":
    success = test_enhanced_memory_logging()
    sys.exit(0 if success else 1) 