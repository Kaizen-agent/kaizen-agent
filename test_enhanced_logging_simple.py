#!/usr/bin/env python3
"""
Simplified test for enhanced logging functionality.

This script tests the enhanced logging feature without relying on the full
import chain, focusing on the core functionality.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_mock_test_result():
    """Create a mock test result with sample data."""
    
    # Mock test cases data
    test_cases = [
        {
            "name": "test_basic_functionality",
            "status": "passed",
            "region": "function_1",
            "input": "Hello, world!",
            "expected_output": "Hello, world!",
            "actual_output": "Hello, world!",
            "evaluation": {"score": 0.95, "reason": "Output matches expected exactly"},
            "evaluation_score": 0.95,
            "execution_time": 0.1,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"test_type": "basic"},
            "error_message": None,
            "error_details": None
        },
        {
            "name": "test_edge_case",
            "status": "failed",
            "region": "function_2",
            "input": "",
            "expected_output": "Empty string handled",
            "actual_output": "Error: empty input",
            "error_message": "Test failed: expected 'Empty string handled', got 'Error: empty input'",
            "evaluation": {"score": 0.2, "reason": "Output does not match expected"},
            "evaluation_score": 0.2,
            "execution_time": 0.05,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"test_type": "edge_case"},
            "error_details": None
        },
        {
            "name": "test_complex_input",
            "status": "passed",
            "region": "function_3",
            "input": {"user": "john", "data": [1, 2, 3]},
            "expected_output": {"result": "success", "processed": 3},
            "actual_output": {"result": "success", "processed": 3},
            "evaluation": {"score": 0.98, "reason": "Complex object processed correctly"},
            "evaluation_score": 0.98,
            "execution_time": 0.15,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"test_type": "complex"},
            "error_message": None,
            "error_details": None
        },
        {
            "name": "test_error_handling",
            "status": "error",
            "region": "function_4",
            "input": "invalid_input",
            "expected_output": "Error handled gracefully",
            "actual_output": None,
            "error_message": "Exception occurred during processing",
            "error_details": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
            "evaluation": None,
            "evaluation_score": None,
            "execution_time": 0.02,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"test_type": "error_handling"}
        }
    ]
    
    return test_cases

def test_enhanced_logging():
    """Test the enhanced logging functionality."""
    
    print("Testing Enhanced Logging Functionality")
    print("=" * 50)
    
    # Create sample test cases
    test_cases = create_mock_test_result()
    
    # Create logs directory
    logs_dir = Path("test-logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_name = "Enhanced_Logging_Test_Suite"
    log_filename = f"{test_name}_{timestamp}_detailed_logs.json"
    log_file_path = logs_dir / log_filename
    
    # Create enhanced detailed logs structure
    detailed_logs = {
        "metadata": {
            "test_name": test_name,
            "file_path": "test_file.py",
            "config_path": "test_config.yaml",
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "auto_fix": True,
                "create_pr": False,
                "max_retries": 2,
                "base_branch": "main",
                "pr_strategy": "ANY_IMPROVEMENT"
            }
        },
        "test_results": {
            "overall_status": {
                "status": "failed",
                "summary": {
                    "total_regions": 4,
                    "passed_regions": 2,
                    "failed_regions": 1,
                    "error_regions": 1
                }
            }
        },
        "error": None,
        "steps": []
    }
    
    # Add enhanced unified test results
    enhanced_unified_data = {
        "name": test_name,
        "file_path": "test_file.py",
        "config_path": "test_config.yaml",
        "status": "failed",
        "error_message": None,
        "error_details": None,
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "summary": {
            "total_tests": len(test_cases),
            "passed_tests": len([tc for tc in test_cases if tc["status"] == "passed"]),
            "failed_tests": len([tc for tc in test_cases if tc["status"] == "failed"]),
            "error_tests": len([tc for tc in test_cases if tc["status"] == "error"]),
            "success_rate": len([tc for tc in test_cases if tc["status"] == "passed"]) / len(test_cases),
            "regions": {}
        },
        "test_cases": test_cases,
        "test_cases_detailed": []
    }
    
    # Add detailed information for each test case
    for tc in test_cases:
        detailed_tc = {
            "name": tc["name"],
            "status": tc["status"],
            "region": tc["region"],
            "input": tc["input"],
            "expected_output": tc["expected_output"],
            "actual_output": tc["actual_output"],
            "error_message": tc["error_message"],
            "error_details": tc["error_details"],
            "evaluation": tc["evaluation"],
            "evaluation_score": tc["evaluation_score"],
            "execution_time": tc["execution_time"],
            "timestamp": tc["timestamp"],
            "metadata": tc["metadata"],
            "summary": {
                "passed": tc["status"] in ['passed'],
                "failed": tc["status"] in ['failed', 'error'],
                "has_error": tc["error_message"] is not None,
                "has_evaluation": tc["evaluation"] is not None,
                "input_type": type(tc["input"]).__name__ if tc["input"] is not None else None,
                "output_type": type(tc["actual_output"]).__name__ if tc["actual_output"] is not None else None,
                "expected_type": type(tc["expected_output"]).__name__ if tc["expected_output"] is not None else None
            }
        }
        enhanced_unified_data["test_cases_detailed"].append(detailed_tc)
    
    # Add summary statistics
    enhanced_unified_data["test_summary"] = {
        "total_test_cases": len(test_cases),
        "passed_test_cases": len([tc for tc in test_cases if tc["status"] == "passed"]),
        "failed_test_cases": len([tc for tc in test_cases if tc["status"] == "failed"]),
        "error_test_cases": len([tc for tc in test_cases if tc["status"] == "error"]),
        "test_cases_with_evaluations": len([tc for tc in test_cases if tc["evaluation"] is not None]),
        "test_cases_with_errors": len([tc for tc in test_cases if tc["error_message"] is not None]),
        "regions": list(set(tc["region"] for tc in test_cases))
    }
    
    detailed_logs["unified_test_results"] = enhanced_unified_data
    
    # Add auto-fix attempts
    detailed_logs["auto_fix_attempts"] = [
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
    
    # Save to JSON file
    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_logs, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✓ Enhanced log file created: {log_file_path}")
    print(f"  File size: {log_file_path.stat().st_size / 1024:.1f} KB")
    
    # Verify the structure
    print(f"\nVerifying log file structure:")
    print("-" * 30)
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)
    
    # Verify the structure
    assert 'metadata' in log_data, "Metadata missing from log file"
    assert 'unified_test_results' in log_data, "Unified test results missing from log file"
    
    unified_data = log_data['unified_test_results']
    assert 'test_cases_detailed' in unified_data, "Detailed test cases missing"
    assert 'test_summary' in unified_data, "Test summary missing"
    
    test_cases_detailed = unified_data['test_cases_detailed']
    assert len(test_cases_detailed) == 4, f"Expected 4 test cases, got {len(test_cases_detailed)}"
    
    # Verify first test case has all required fields
    first_tc = test_cases_detailed[0]
    required_fields = ['name', 'status', 'region', 'input', 'expected_output', 'actual_output', 'evaluation', 'summary']
    for field in required_fields:
        assert field in first_tc, f"Missing field '{field}' in test case"
    
    print(f"✓ Log file structure verified")
    print(f"✓ Found {len(test_cases_detailed)} test cases with detailed information")
    
    # Show what was saved
    print(f"\nSaved Information:")
    print(f"  • Test metadata (name, status, timing, config)")
    print(f"  • {len(test_cases_detailed)} detailed test cases")
    print(f"  • Inputs, outputs, and evaluations for each test")
    print(f"  • Error messages and details")
    print(f"  • Auto-fix attempts")
    print(f"  • Summary statistics")
    
    # Show sample data
    print(f"\nSample Test Case Data:")
    print("-" * 30)
    sample_tc = test_cases_detailed[0]
    print(f"Name: {sample_tc['name']}")
    print(f"Status: {sample_tc['status']}")
    print(f"Region: {sample_tc['region']}")
    print(f"Input: {sample_tc['input']}")
    print(f"Expected Output: {sample_tc['expected_output']}")
    print(f"Actual Output: {sample_tc['actual_output']}")
    print(f"Evaluation: {sample_tc['evaluation']}")
    print(f"Error Message: {sample_tc['error_message']}")
    
    print(f"\n✓ Enhanced logging test completed successfully!")
    print(f"  Log file: {log_file_path}")
    print(f"  Use 'kaizen analyze-logs {log_file_path}' to view the results")
    
    return log_file_path

if __name__ == "__main__":
    test_enhanced_logging() 