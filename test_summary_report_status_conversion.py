#!/usr/bin/env python3
"""Test to verify status conversion issue in _save_summary_report."""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kaizen.cli.commands.memory import ExecutionMemory, FixAttempt, LLMInteraction
from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus, TestResult
from kaizen.cli.commands.test import _save_summary_report
from rich.console import Console
from kaizen.cli.commands.models.test_execution_result import TestExecutionSummary

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
    
    # Create TestExecutionSummary
    summary = TestExecutionSummary(
        total_tests=total_tests,
        passed_tests=passed_tests,
        failed_tests=total_tests - passed_tests,
        error_tests=0,
        skipped_tests=0
    )
    
    return TestExecutionResult(
        name=f"test_attempt_{attempt_number}",
        file_path="test_file.py",
        config_path="test_config.yaml",
        test_cases=test_cases,
        status=TestStatus.PASSED if passed_tests == total_tests else TestStatus.FAILED,
        start_time=datetime.now(),
        end_time=datetime.now(),
        summary=summary
    )

def test_summary_report_status_conversion():
    """Test if _save_summary_report properly converts status values from memory-based attempts."""
    
    print("🧪 Testing _save_summary_report status conversion...")
    
    # Create memory with attempts (like what happens in AutoFix)
    memory = ExecutionMemory()
    memory.start_execution("test_123", config=None)
    
    # Create mock LLM interactions
    llm_interaction1 = LLMInteraction(
        interaction_type="code_fixing",
        prompt="Fix the syntax errors in the code",
        response="Here's the fixed code with proper syntax",
        reasoning="The code was missing colons after function definitions"
    )
    
    llm_interaction2 = LLMInteraction(
        interaction_type="code_fixing",
        prompt="Fix the remaining logic errors",
        response="Here's the improved code with better logic",
        reasoning="The function needed better error handling and edge case coverage"
    )
    
    # Create mock test execution results
    baseline_result = create_mock_test_execution_result(0, 0, 3)  # All tests failed initially
    attempt1_result = create_mock_test_execution_result(1, 1, 3)  # 1 test passed
    attempt2_result = create_mock_test_execution_result(2, 2, 3)  # 2 tests passed
    
    # Log attempts to memory (like AutoFix does)
    memory.log_fix_attempt(
        file_path="test_file.py",
        attempt_number=1,
        original_code="def test_function():\n    return 1",
        fixed_code="def test_function():\n    return 1",
        success=False,  # Not all tests passed
        test_results_before={},
        test_results_after=attempt1_result.to_legacy_format(),
        approach_description="First attempt to fix syntax",
        code_changes="Added missing colons",
        llm_interaction=llm_interaction1
    )
    
    memory.log_fix_attempt(
        file_path="test_file.py",
        attempt_number=2,
        original_code="def test_function():\n    return 1",
        fixed_code="def test_function():\n    return 1",
        success=True,  # All tests passed
        test_results_before={},
        test_results_after=attempt2_result.to_legacy_format(),
        approach_description="Second attempt with proper formatting",
        code_changes="Added proper spacing and newlines",
        llm_interaction=llm_interaction2
    )
    
    print(f"   ✓ Logged {len(memory.current_execution['fix_attempts'])} attempts to memory")
    
    # Convert attempts from memory (like what AutoFix does)
    from kaizen.autofix.main import AutoFix
    config = {'max_retries': 2, 'create_pr': False}
    runner_config = {
        'name': 'test_config',
        'file_path': 'test_file.py',
        'tests': []
    }
    autofix = AutoFix(config, runner_config, memory=memory)
    
    # Convert attempts from memory
    attempts = autofix._get_attempts_from_memory("test_file.py")
    print(f"   ✓ Converted {len(attempts)} attempts from memory")
    
    # Print the converted attempts to see the structure
    for i, attempt in enumerate(attempts):
        print(f"   Attempt {i+1}:")
        print(f"     - status: {attempt.get('status')}")
        print(f"     - test_results: {type(attempt.get('test_results'))}")
        if attempt.get('test_results'):
            print(f"     - test_results keys: {list(attempt['test_results'].keys())}")
            if 'test_cases' in attempt['test_results']:
                print(f"     - test_cases count: {len(attempt['test_results']['test_cases'])}")
                for j, tc in enumerate(attempt['test_results']['test_cases']):
                    print(f"       Test case {j+1}: status = {tc.get('status')}")
    
    # Create TestResult with attempts
    now = datetime.now()
    test_result = TestResult(
        name="test_config",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        start_time=now,
        end_time=now,
        status="success",
        results=attempt2_result.to_legacy_format(),
        error=None,
        steps=[],
        unified_result=attempt2_result,
        test_attempts=attempts,  # This is the key - using converted attempts
        baseline_result=baseline_result
    )
    
    print(f"   ✓ Created TestResult with test_attempts: {len(test_result.test_attempts) if test_result.test_attempts else 0} attempts")
    
    # Create mock config
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
    
    # Create test-logs directory if it doesn't exist
    test_logs_dir = Path("test-logs")
    test_logs_dir.mkdir(exist_ok=True)
    
    # Generate summary report
    console = Console(record=True)
    report_path = _save_summary_report(console, test_result, mock_config)
    
    # Read the generated report
    with open(report_path, 'r') as f:
        report_content = f.read()
    
    print(f"📄 Generated report: {report_path}")
    print(f"📊 Report length: {len(report_content)} characters")
    
    # Check for attempts information in the report
    print("\n🔍 Analyzing report content for status conversion...")
    
    # Check for attempts table
    has_attempts_table = "| Attempt" in report_content and "| Status" in report_content
    print(f"✅ Attempts table found: {has_attempts_table}")
    
    # Check for specific status values in the table
    # Look for the test results table section
    table_section = re.search(r'## Test Results Summary.*?(?=##|$)', report_content, re.DOTALL)
    if table_section:
        table_content = table_section.group(0)
        print(f"📋 Found table section ({len(table_content)} characters)")
        
        # Check for specific status values
        has_passed_status = "passed" in table_content.lower()
        has_failed_status = "failed" in table_content.lower()
        has_na_status = "N/A" in table_content
        has_unknown_status = "unknown" in table_content.lower()
        
        print(f"   - Contains 'passed': {has_passed_status}")
        print(f"   - Contains 'failed': {has_failed_status}")
        print(f"   - Contains 'N/A': {has_na_status}")
        print(f"   - Contains 'unknown': {has_unknown_status}")
        
        # Extract table rows to see what's actually in the table
        table_rows = re.findall(r'\|.*?\|', table_content)
        print(f"   - Found {len(table_rows)} table rows")
        
        for i, row in enumerate(table_rows[:5]):  # Show first 5 rows
            print(f"     Row {i+1}: {row.strip()}")
        
        # Check if the issue is present
        if has_na_status or has_unknown_status:
            print("❌ ISSUE FOUND: Table contains N/A or unknown status values!")
            print("   This indicates the status conversion from memory-based attempts is not working properly.")
        else:
            print("✅ No N/A or unknown status values found in table")
    else:
        print("❌ Could not find test results table section")
    
    # Check for specific attempt details
    has_attempt_1 = "First attempt to fix syntax" in report_content
    has_attempt_2 = "Second attempt with proper formatting" in report_content
    
    print(f"✅ Attempt 1 details found: {has_attempt_1}")
    print(f"✅ Attempt 2 details found: {has_attempt_2}")
    
    # Check for improvement analysis
    has_improvement = "Improvement" in report_content
    print(f"✅ Improvement analysis found: {has_improvement}")
    
    # Clean up
    try:
        report_path.unlink()
        print(f"   ✓ Cleaned up test report: {report_path}")
    except Exception as e:
        print(f"   ⚠️ Could not clean up {report_path}: {str(e)}")
    
    print("\n🎉 Status conversion test completed!")
    
    return {
        'has_attempts_table': has_attempts_table,
        'has_passed_status': has_passed_status if 'has_passed_status' in locals() else False,
        'has_failed_status': has_failed_status if 'has_failed_status' in locals() else False,
        'has_na_status': has_na_status if 'has_na_status' in locals() else False,
        'has_unknown_status': has_unknown_status if 'has_unknown_status' in locals() else False,
        'has_attempt_1': has_attempt_1,
        'has_attempt_2': has_attempt_2,
        'has_improvement': has_improvement
    }

if __name__ == "__main__":
    test_summary_report_status_conversion() 