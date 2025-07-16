#!/usr/bin/env python3
"""Test to check if _save_summary_report properly uses attempts data."""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kaizen.cli.commands.memory import ExecutionMemory, FixAttempt, LLMInteraction
from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus, TestResult
from kaizen.cli.commands.test import _save_summary_report
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

def test_summary_report_with_attempts():
    """Test if _save_summary_report properly includes attempts in the markdown report."""
    
    print("🧪 Testing _save_summary_report with attempts data...")
    
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
    
    # Create fix attempts in memory (like what AutoFix does)
    fix_attempt1 = FixAttempt(
        attempt_number=1,
        file_path="test_file.py",
        approach_description="Fix syntax errors",
        code_changes_made="Added missing colons after function definitions",
        original_code="def test()\n    pass\ndef another()\n    return None",
        modified_code="def test():\n    pass\ndef another():\n    return None",
        test_results_before=baseline_result.to_legacy_format(),
        test_results_after=attempt1_result.to_legacy_format(),
        success=False,
        llm_interaction=llm_interaction1,
        lessons_learned="Need to add colons after function definitions",
        why_approach_failed="Still have logic errors in the code",
        what_worked_partially="Fixed syntax errors, but logic still needs work"
    )
    
    fix_attempt2 = FixAttempt(
        attempt_number=2,
        file_path="test_file.py",
        approach_description="Fix logic errors",
        code_changes_made="Improved error handling and edge case coverage",
        original_code="def test():\n    pass\ndef another():\n    return None",
        modified_code="def test():\n    try:\n        return True\n    except:\n        return False\ndef another():\n    return None",
        test_results_before=attempt1_result.to_legacy_format(),
        test_results_after=attempt2_result.to_legacy_format(),
        success=True,
        llm_interaction=llm_interaction2,
        lessons_learned="Error handling is crucial for robust code",
        why_approach_failed=None,
        what_worked_partially="Successfully fixed all logic errors"
    )
    
    # Add attempts to memory
    memory.current_execution['fix_attempts'].append(fix_attempt1)
    memory.current_execution['fix_attempts'].append(fix_attempt2)
    
    print(f"   ✓ Added {len(memory.current_execution['fix_attempts'])} fix attempts to memory")
    
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
    
    # Ensure test-logs directory exists and is empty
    logs_dir = Path("test-logs")
    logs_dir.mkdir(exist_ok=True)
    for f in logs_dir.glob("*"):
        f.unlink()
    
    # Call _save_summary_report
    console = Console(record=True)
    _save_summary_report(console, test_result, mock_config)
    
    # Check that markdown report was created
    summary_reports = list(logs_dir.glob("test_report_*.md"))
    
    if summary_reports:
        print(f"   ✓ Markdown summary report created: {summary_reports[0]}")
        
        # Read the markdown report to check for attempts data
        with open(summary_reports[0], 'r') as f:
            report_content = f.read()
        
        print(f"   ✓ Report size: {len(report_content)} characters")
        
        # Check for attempts-related content
        attempts_found = []
        
        # Look for attempt-related patterns in the markdown
        if "Attempt" in report_content:
            attempts_found.append("'Attempt' keyword found")
        
        if "Auto-fix" in report_content:
            attempts_found.append("'Auto-fix' keyword found")
        
        if "attempts" in report_content.lower():
            attempts_found.append("'attempts' keyword found")
        
        if "fix" in report_content.lower():
            attempts_found.append("'fix' keyword found")
        
        # Look for specific attempt numbers
        if "Attempt 1" in report_content or "attempt 1" in report_content:
            attempts_found.append("Attempt 1 found")
        
        if "Attempt 2" in report_content or "attempt 2" in report_content:
            attempts_found.append("Attempt 2 found")
        
        # Look for approach descriptions
        if "Fix syntax errors" in report_content:
            attempts_found.append("'Fix syntax errors' approach found")
        
        if "Fix logic errors" in report_content:
            attempts_found.append("'Fix logic errors' approach found")
        
        # Look for lessons learned
        if "Need to add colons" in report_content:
            attempts_found.append("'Need to add colons' lesson found")
        
        if "Error handling is crucial" in report_content:
            attempts_found.append("'Error handling is crucial' lesson found")
        
        # Print what was found
        if attempts_found:
            print(f"   ✅ Found attempts data in report:")
            for item in attempts_found:
                print(f"      - {item}")
        else:
            print(f"   ❌ No attempts data found in report!")
        
        # Show a snippet of the report content
        print(f"\n   📄 Report content snippet (first 500 chars):")
        print(f"   {report_content[:500]}...")
        
        # Clean up
        summary_reports[0].unlink()
        print(f"   ✓ Cleaned up report file")
        
    else:
        print(f"   ❌ No markdown summary report found!")
    
    print("\n🎉 Summary report attempts test completed!")

def test_summary_report_without_attempts():
    """Test if _save_summary_report handles cases without attempts properly."""
    
    print("\n🧪 Testing _save_summary_report without attempts data...")
    
    # Create a test result without attempts
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
        test_attempts=None,  # No attempts
        baseline_result=create_mock_test_execution_result(0, 0, 3)
    )
    
    print(f"   ✓ Created TestResult with test_attempts: {test_result.test_attempts}")
    
    # Create mock config
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
    
    # Call _save_summary_report
    console = Console(record=True)
    _save_summary_report(console, test_result, mock_config)
    
    # Check that markdown report was created
    logs_dir = Path("test-logs")
    summary_reports = list(logs_dir.glob("test_report_*.md"))
    
    if summary_reports:
        print(f"   ✓ Markdown summary report created: {summary_reports[0]}")
        
        # Read the markdown report
        with open(summary_reports[0], 'r') as f:
            report_content = f.read()
        
        # Check that it doesn't mention attempts
        if "Attempt" in report_content or "attempt" in report_content:
            print(f"   ⚠️ Report mentions attempts when there should be none")
        else:
            print(f"   ✅ Correctly no attempts mentioned in report")
        
        # Clean up
        summary_reports[0].unlink()
        print(f"   ✓ Cleaned up report file")
        
    else:
        print(f"   ❌ No markdown summary report found!")
    
    print("\n🎉 Summary report without attempts test completed!")

if __name__ == "__main__":
    test_summary_report_with_attempts()
    test_summary_report_without_attempts() 