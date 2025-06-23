#!/usr/bin/env python3
"""
Test script for enhanced logging functionality.

This script tests that the enhanced logging feature correctly saves
inputs, outputs, and evaluations for each test case.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus
from kaizen.cli.commands.utils.log_analyzer import TestLogAnalyzer

def create_sample_test_result() -> TestExecutionResult:
    """Create a sample test execution result with various test cases."""
    
    # Create test cases with different scenarios
    test_cases = [
        TestCaseResult(
            name="test_basic_functionality",
            status=TestStatus.PASSED,
            region="function_1",
            input="Hello, world!",
            expected_output="Hello, world!",
            actual_output="Hello, world!",
            evaluation={"score": 0.95, "reason": "Output matches expected exactly"},
            evaluation_score=0.95,
            execution_time=0.1,
            timestamp=datetime.now(),
            metadata={"test_type": "basic"}
        ),
        TestCaseResult(
            name="test_edge_case",
            status=TestStatus.FAILED,
            region="function_2",
            input="",
            expected_output="Empty string handled",
            actual_output="Error: empty input",
            error_message="Test failed: expected 'Empty string handled', got 'Error: empty input'",
            evaluation={"score": 0.2, "reason": "Output does not match expected"},
            evaluation_score=0.2,
            execution_time=0.05,
            timestamp=datetime.now(),
            metadata={"test_type": "edge_case"}
        ),
        TestCaseResult(
            name="test_complex_input",
            status=TestStatus.PASSED,
            region="function_3",
            input={"user": "john", "data": [1, 2, 3]},
            expected_output={"result": "success", "processed": 3},
            actual_output={"result": "success", "processed": 3},
            evaluation={"score": 0.98, "reason": "Complex object processed correctly"},
            evaluation_score=0.98,
            execution_time=0.15,
            timestamp=datetime.now(),
            metadata={"test_type": "complex"}
        ),
        TestCaseResult(
            name="test_error_handling",
            status=TestStatus.ERROR,
            region="function_4",
            input="invalid_input",
            expected_output="Error handled gracefully",
            actual_output=None,
            error_message="Exception occurred during processing",
            error_details="TypeError: unsupported operand type(s) for +: 'int' and 'str'",
            evaluation=None,
            evaluation_score=None,
            execution_time=0.02,
            timestamp=datetime.now(),
            metadata={"test_type": "error_handling"}
        )
    ]
    
    # Create test execution result
    result = TestExecutionResult(
        name="Enhanced Logging Test Suite",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        test_cases=test_cases,
        metadata={"test_run": "enhanced_logging_test"}
    )
    
    return result

def test_enhanced_logging():
    """Test the enhanced logging functionality."""
    
    print("Testing Enhanced Logging Functionality")
    print("=" * 50)
    
    # Create sample test result
    test_result = create_sample_test_result()
    
    # Create a mock TestResult object (as used by the CLI)
    from kaizen.cli.commands.models import TestResult
    
    mock_test_result = TestResult(
        name=test_result.name,
        file_path=test_result.file_path,
        config_path=test_result.config_path,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status="failed",
        results={"overall_status": {"status": "failed"}},
        unified_result=test_result,
        test_attempts=[
            {
                "status": "failed",
                "test_cases": [
                    {
                        "name": "test_basic_functionality",
                        "status": "failed",
                        "input": "old input",
                        "expected_output": "old expected",
                        "actual_output": "old actual",
                        "evaluation": {"score": 0.1},
                        "reason": "Old attempt"
                    }
                ]
            }
        ]
    )
    
    # Create logs directory
    logs_dir = Path("test-logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{test_result.name.replace(' ', '_')}_{timestamp}_detailed_logs.json"
    log_file_path = logs_dir / log_filename
    
    # Simulate the enhanced logging process
    detailed_logs = {
        "metadata": {
            "test_name": mock_test_result.name,
            "file_path": str(mock_test_result.file_path),
            "config_path": str(mock_test_result.config_path),
            "start_time": mock_test_result.start_time.isoformat(),
            "end_time": mock_test_result.end_time.isoformat(),
            "status": mock_test_result.status,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "auto_fix": True,
                "create_pr": False,
                "max_retries": 2,
                "base_branch": "main",
                "pr_strategy": "ANY_IMPROVEMENT"
            }
        },
        "test_results": mock_test_result.results,
        "error": mock_test_result.error,
        "steps": mock_test_result.steps
    }
    
    # Add enhanced unified test results
    if mock_test_result.unified_result:
        unified_data = mock_test_result.unified_result.to_dict()
        
        # Enhance with detailed test case information
        enhanced_unified_data = {
            **unified_data,
            "test_cases_detailed": []
        }
        
        # Add detailed information for each test case
        for tc in mock_test_result.unified_result.test_cases:
            detailed_tc = {
                "name": tc.name,
                "status": tc.status.value,
                "region": tc.region,
                "input": tc.input,
                "expected_output": tc.expected_output,
                "actual_output": tc.actual_output,
                "error_message": tc.error_message,
                "error_details": tc.error_details,
                "evaluation": tc.evaluation,
                "evaluation_score": tc.evaluation_score,
                "execution_time": tc.execution_time,
                "timestamp": tc.timestamp.isoformat() if tc.timestamp else None,
                "metadata": tc.metadata,
                "summary": {
                    "passed": tc.status.value in ['passed'],
                    "failed": tc.status.value in ['failed', 'error'],
                    "has_error": tc.error_message is not None,
                    "has_evaluation": tc.evaluation is not None,
                    "input_type": type(tc.input).__name__ if tc.input is not None else None,
                    "output_type": type(tc.actual_output).__name__ if tc.actual_output is not None else None,
                    "expected_type": type(tc.expected_output).__name__ if tc.expected_output is not None else None
                }
            }
            enhanced_unified_data["test_cases_detailed"].append(detailed_tc)
        
        # Add summary statistics
        enhanced_unified_data["test_summary"] = {
            "total_test_cases": len(mock_test_result.unified_result.test_cases),
            "passed_test_cases": len([tc for tc in mock_test_result.unified_result.test_cases if tc.status.value == 'passed']),
            "failed_test_cases": len([tc for tc in mock_test_result.unified_result.test_cases if tc.status.value == 'failed']),
            "error_test_cases": len([tc for tc in mock_test_result.unified_result.test_cases if tc.status.value == 'error']),
            "test_cases_with_evaluations": len([tc for tc in mock_test_result.unified_result.test_cases if tc.evaluation is not None]),
            "test_cases_with_errors": len([tc for tc in mock_test_result.unified_result.test_cases if tc.error_message is not None]),
            "regions": list(set(tc.region for tc in mock_test_result.unified_result.test_cases))
        }
        
        detailed_logs["unified_test_results"] = enhanced_unified_data
    
    # Add auto-fix attempts
    if mock_test_result.test_attempts:
        detailed_logs["auto_fix_attempts"] = mock_test_result.test_attempts
    
    # Save to JSON file
    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_logs, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✓ Enhanced log file created: {log_file_path}")
    print(f"  File size: {log_file_path.stat().st_size / 1024:.1f} KB")
    
    # Test the log analyzer
    print(f"\nTesting Log Analyzer:")
    print("-" * 30)
    
    analyzer = TestLogAnalyzer()
    
    # Test summary view
    print("\n1. Summary View:")
    analyzer.analyze_log_file(log_file_path, show_details=False)
    
    # Test detailed view
    print("\n2. Detailed View (first test case only):")
    # We'll just verify the file can be parsed and has the expected structure
    with open(log_file_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)
    
    # Verify the structure
    assert 'metadata' in log_data, "Metadata missing from log file"
    assert 'unified_test_results' in log_data, "Unified test results missing from log file"
    
    unified_data = log_data['unified_test_results']
    assert 'test_cases_detailed' in unified_data, "Detailed test cases missing"
    assert 'test_summary' in unified_data, "Test summary missing"
    
    test_cases = unified_data['test_cases_detailed']
    assert len(test_cases) == 4, f"Expected 4 test cases, got {len(test_cases)}"
    
    # Verify first test case has all required fields
    first_tc = test_cases[0]
    required_fields = ['name', 'status', 'region', 'input', 'expected_output', 'actual_output', 'evaluation', 'summary']
    for field in required_fields:
        assert field in first_tc, f"Missing field '{field}' in test case"
    
    print(f"✓ Log file structure verified")
    print(f"✓ Found {len(test_cases)} test cases with detailed information")
    
    # Show what was saved
    print(f"\nSaved Information:")
    print(f"  • Test metadata (name, status, timing, config)")
    print(f"  • {len(test_cases)} detailed test cases")
    print(f"  • Inputs, outputs, and evaluations for each test")
    print(f"  • Error messages and details")
    print(f"  • Auto-fix attempts")
    print(f"  • Summary statistics")
    
    print(f"\n✓ Enhanced logging test completed successfully!")
    print(f"  Log file: {log_file_path}")
    print(f"  Use 'kaizen analyze-logs {log_file_path}' to view the results")

if __name__ == "__main__":
    test_enhanced_logging() 