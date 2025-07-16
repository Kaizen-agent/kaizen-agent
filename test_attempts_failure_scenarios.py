#!/usr/bin/env python3
"""Test to reproduce the real-world failure scenarios where attempts are not saved."""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kaizen.cli.commands.memory import ExecutionMemory, FixAttempt, LLMInteraction
from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus, TestResult
from kaizen.cli.commands.test import _save_detailed_logs, _save_summary_report
from rich.console import Console

def create_mock_test_execution_result(attempt_number: int, passed_tests: int, total_tests: int = 3) -> TestExecutionResult:
    """Create a mock test execution result for testing."""
    test_cases = []
    
    for i in range(total_tests):
        status = TestStatus.PASSED if i < passed_tests else TestStatus.FAILED
        test_case = TestCaseResult(
            name=f"test_case_{i}",
            status=status,
            input=f"input_{i}",
            expected_output=f"expected_{i}",
            actual_output=f"actual_{i}",
            error_message=None if status == TestStatus.PASSED else f"Error in test {i}",
            evaluation={"score": 1.0 if status == TestStatus.PASSED else 0.0}
        )
        test_cases.append(test_case)
    
    # Create TestExecutionResult with required parameters
    result = TestExecutionResult(
        name=f"test_attempt_{attempt_number}",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml")
    )
    
    # Add test cases
    result.add_test_cases(test_cases)
    
    return result

def test_scenario_1_auto_fix_disabled():
    """Test Scenario 1: Auto-fix is disabled in config."""
    print("\n🧪 Scenario 1: Auto-fix disabled")
    
    # Create a test result where auto-fix was never run
    now = datetime.now()
    test_result = TestResult(
        name="test_config",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        start_time=now,
        end_time=now,
        status="failed",
        results={},
        error="Some tests failed",
        steps=[],
        unified_result=create_mock_test_execution_result(0, 0, 3),  # All tests failed
        test_attempts=None,  # This is the key - no attempts because auto-fix was disabled
        baseline_result=create_mock_test_execution_result(0, 0, 3)
    )
    
    print(f"   ✓ Created TestResult with test_attempts: {test_result.test_attempts}")
    
    # Save logs
    mock_config = SimpleNamespace(
        name="test_config",
        file_path="test_file.py",
        config_path="test_config.yaml",
        auto_fix=False,  # Auto-fix disabled
        create_pr=False,
        max_retries=2,
        base_branch="main",
        pr_strategy="ANY_IMPROVEMENT"
    )
    
    console = Console(record=True)
    _save_detailed_logs(console, test_result, mock_config)
    _save_summary_report(console, test_result, mock_config)
    
    # Check if attempts were saved
    logs_dir = Path("test-logs")
    detailed_logs = list(logs_dir.glob("*_detailed_logs.json"))
    
    if detailed_logs:
        with open(detailed_logs[0], 'r') as f:
            logs_data = json.load(f)
        
        if 'auto_fix_attempts' in logs_data:
            print(f"   ❌ Found attempts in logs when auto-fix was disabled!")
        else:
            print(f"   ✅ Correctly no attempts in logs (auto-fix disabled)")
        
        # Clean up
        detailed_logs[0].unlink()
    else:
        print(f"   ❌ No detailed logs file found!")

def test_scenario_2_tests_pass_initially():
    """Test Scenario 2: Tests pass initially, so auto-fix never runs."""
    print("\n🧪 Scenario 2: Tests pass initially")
    
    # Create a test result where all tests passed initially
    now = datetime.now()
    test_result = TestResult(
        name="test_config",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        start_time=now,
        end_time=now,
        status="passed",
        results={},
        error=None,
        steps=[],
        unified_result=create_mock_test_execution_result(0, 3, 3),  # All tests passed
        test_attempts=None,  # No attempts because tests passed initially
        baseline_result=create_mock_test_execution_result(0, 3, 3)
    )
    
    print(f"   ✓ Created TestResult with test_attempts: {test_result.test_attempts}")
    
    # Save logs
    mock_config = SimpleNamespace(
        name="test_config",
        file_path="test_file.py",
        config_path="test_config.yaml",
        auto_fix=True,  # Auto-fix enabled but never used
        create_pr=False,
        max_retries=2,
        base_branch="main",
        pr_strategy="ANY_IMPROVEMENT"
    )
    
    console = Console(record=True)
    _save_detailed_logs(console, test_result, mock_config)
    _save_summary_report(console, test_result, mock_config)
    
    # Check if attempts were saved
    logs_dir = Path("test-logs")
    detailed_logs = list(logs_dir.glob("*_detailed_logs.json"))
    
    if detailed_logs:
        with open(detailed_logs[0], 'r') as f:
            logs_data = json.load(f)
        
        if 'auto_fix_attempts' in logs_data:
            print(f"   ❌ Found attempts in logs when tests passed initially!")
        else:
            print(f"   ✅ Correctly no attempts in logs (tests passed initially)")
        
        # Clean up
        detailed_logs[0].unlink()
    else:
        print(f"   ❌ No detailed logs file found!")

def test_scenario_3_auto_fix_fails():
    """Test Scenario 3: Auto-fix fails and returns None or no attempts."""
    print("\n🧪 Scenario 3: Auto-fix fails")
    
    # Create a test result where auto-fix failed
    now = datetime.now()
    test_result = TestResult(
        name="test_config",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        start_time=now,
        end_time=now,
        status="failed",
        results={},
        error="Auto-fix failed",
        steps=[],
        unified_result=create_mock_test_execution_result(0, 0, 3),  # All tests failed
        test_attempts=None,  # No attempts because auto-fix failed
        baseline_result=create_mock_test_execution_result(0, 0, 3)
    )
    
    print(f"   ✓ Created TestResult with test_attempts: {test_result.test_attempts}")
    
    # Save logs
    mock_config = SimpleNamespace(
        name="test_config",
        file_path="test_file.py",
        config_path="test_config.yaml",
        auto_fix=True,  # Auto-fix enabled but failed
        create_pr=False,
        max_retries=2,
        base_branch="main",
        pr_strategy="ANY_IMPROVEMENT"
    )
    
    console = Console(record=True)
    _save_detailed_logs(console, test_result, mock_config)
    _save_summary_report(console, test_result, mock_config)
    
    # Check if attempts were saved
    logs_dir = Path("test-logs")
    detailed_logs = list(logs_dir.glob("*_detailed_logs.json"))
    
    if detailed_logs:
        with open(detailed_logs[0], 'r') as f:
            logs_data = json.load(f)
        
        if 'auto_fix_attempts' in logs_data:
            print(f"   ❌ Found attempts in logs when auto-fix failed!")
        else:
            print(f"   ✅ Correctly no attempts in logs (auto-fix failed)")
        
        # Clean up
        detailed_logs[0].unlink()
    else:
        print(f"   ❌ No detailed logs file found!")

def test_scenario_4_empty_attempts_list():
    """Test Scenario 4: Auto-fix runs but returns empty attempts list."""
    print("\n🧪 Scenario 4: Auto-fix returns empty attempts list")
    
    # Create a test result where auto-fix ran but returned empty attempts
    now = datetime.now()
    test_result = TestResult(
        name="test_config",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        start_time=now,
        end_time=now,
        status="failed",
        results={},
        error="Some tests failed",
        steps=[],
        unified_result=create_mock_test_execution_result(0, 0, 3),  # All tests failed
        test_attempts=[],  # Empty attempts list
        baseline_result=create_mock_test_execution_result(0, 0, 3)
    )
    
    print(f"   ✓ Created TestResult with test_attempts: {test_result.test_attempts}")
    print(f"   ✓ test_attempts length: {len(test_result.test_attempts) if test_result.test_attempts else 0}")
    
    # Save logs
    mock_config = SimpleNamespace(
        name="test_config",
        file_path="test_file.py",
        config_path="test_config.yaml",
        auto_fix=True,
        create_pr=False,
        max_retries=2,
        base_branch="main",
        pr_strategy="ANY_IMPROVEMENT"
    )
    
    console = Console(record=True)
    _save_detailed_logs(console, test_result, mock_config)
    _save_summary_report(console, test_result, mock_config)
    
    # Check if attempts were saved
    logs_dir = Path("test-logs")
    detailed_logs = list(logs_dir.glob("*_detailed_logs.json"))
    
    if detailed_logs:
        with open(detailed_logs[0], 'r') as f:
            logs_data = json.load(f)
        
        if 'auto_fix_attempts' in logs_data:
            attempts_in_logs = logs_data['auto_fix_attempts']
            if len(attempts_in_logs) == 0:
                print(f"   ✅ Correctly saved empty attempts list in logs")
            else:
                print(f"   ❌ Found {len(attempts_in_logs)} attempts in logs when should be empty!")
        else:
            print(f"   ❌ No auto_fix_attempts key in logs!")
        
        # Clean up
        detailed_logs[0].unlink()
    else:
        print(f"   ❌ No detailed logs file found!")

def test_all_failure_scenarios():
    """Test all the failure scenarios that could cause attempts to not be saved."""
    
    print("🧪 Testing real-world failure scenarios where attempts are not saved...")
    
    # Ensure test-logs directory exists and is empty
    logs_dir = Path("test-logs")
    logs_dir.mkdir(exist_ok=True)
    for f in logs_dir.glob("*"):
        f.unlink()
    
    # Test each scenario
    test_scenario_1_auto_fix_disabled()
    test_scenario_2_tests_pass_initially()
    test_scenario_3_auto_fix_fails()
    test_scenario_4_empty_attempts_list()
    
    print("\n🎉 All failure scenarios tested!")
    print("\n📋 Summary of scenarios where attempts might be missing:")
    print("   1. Auto-fix is disabled in config")
    print("   2. Tests pass initially (auto-fix never runs)")
    print("   3. Auto-fix fails and returns None")
    print("   4. Auto-fix runs but returns empty attempts list")
    print("   5. No files_to_fix specified in config")
    print("   6. Memory system not available or fails")

if __name__ == "__main__":
    test_all_failure_scenarios() 