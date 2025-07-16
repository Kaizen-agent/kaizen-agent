#!/usr/bin/env python3
"""Test to check if generated markdown report contains attempts information in tables and content."""

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
    
    return TestExecutionResult(
        name=f"test_attempt_{attempt_number}",
        file_path="test_file.py",
        config_path="test_config.yaml",
        test_cases=test_cases,
        status=TestStatus.PASSED if passed_tests == total_tests else TestStatus.FAILED,
        start_time=datetime.now(),
        end_time=datetime.now(),
        summary={"total_tests": total_tests, "passed_tests": passed_tests, "failed_tests": total_tests - passed_tests}
    )

def test_summary_report_attempts_content():
    """Test if the generated markdown report contains attempts information."""
    console = Console()
    
    # Create memory instance
    memory = ExecutionMemory()
    
    # Start execution
    memory.start_execution("test_123", config=None)
    
    # Create test attempts in memory
    llm_interaction = LLMInteraction(
        interaction_type="code_fixing",
        prompt="Fix the code",
        response="Here's the fixed code",
        reasoning="The code had syntax errors that needed fixing"
    )
    
    # Create mock attempts
    attempt1 = FixAttempt(
        attempt_number=1,
        file_path="test_file.py",
        approach_description="First attempt to fix syntax",
        code_changes_made="Added missing newline",
        original_code="def test_function():\n    return 1",
        modified_code="def test_function():\n    return 1\n",
        test_results_before={},
        test_results_after={"overall_status": "failed", "test_cases": [{"status": "failed"}]},
        success=False,
        llm_interaction=llm_interaction,
        lessons_learned="Need to check for proper line endings",
        why_approach_failed="Still has syntax issues",
        what_worked_partially="Basic structure is correct",
        timestamp=datetime.now()
    )
    
    attempt2 = FixAttempt(
        attempt_number=2,
        file_path="test_file.py",
        approach_description="Second attempt with proper formatting",
        code_changes_made="Added proper spacing and newlines",
        original_code="def test_function():\n    return 1",
        modified_code="def test_function():\n    return 1\n\n",
        test_results_before={},
        test_results_after={"overall_status": "passed", "test_cases": [{"status": "passed"}]},
        success=True,
        llm_interaction=llm_interaction,
        lessons_learned="Proper formatting is essential",
        why_approach_failed=None,
        what_worked_partially="Complete fix achieved",
        timestamp=datetime.now()
    )
    
    # Add attempts to memory
    memory.current_execution['fix_attempts'] = [attempt1, attempt2]
    
    # Create mock test execution result
    summary = TestExecutionSummary(
        total_tests=3,
        passed_tests=2,
        failed_tests=1,
        error_tests=0,
        skipped_tests=0,
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_execution_time=None
    )
    test_execution_result = TestExecutionResult(
        name=f"test_attempt_{1}",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        test_cases=[
            TestCaseResult(
                name="test_case_0",
                status=TestStatus.PASSED,
                input="input_0",
                expected_output="expected_0",
                actual_output="actual_0",
                error_message=None,
                evaluation={"score": 1.0}
            ),
            TestCaseResult(
                name="test_case_1",
                status=TestStatus.PASSED,
                input="input_1",
                expected_output="expected_1",
                actual_output="actual_1",
                error_message=None,
                evaluation={"score": 1.0}
            ),
            TestCaseResult(
                name="test_case_2",
                status=TestStatus.FAILED,
                input="input_2",
                expected_output="expected_2",
                actual_output="actual_2",
                error_message="Error in test 2",
                evaluation={"score": 0.0}
            )
        ],
        summary=summary,
        status=TestStatus.FAILED,
        start_time=summary.start_time,
        end_time=summary.end_time
    )
    
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
    
    # Create TestResult with attempts
    test_result = TestResult(
        name="test_result",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        start_time=summary.start_time,
        end_time=summary.end_time,
        status=TestStatus.FAILED.value,
        results={},
        unified_result=test_execution_result,
        test_attempts=[
            {
                'attempt_number': 1,
                'status': 'failed',
                'changes': {
                    'type': 'llm_fix',
                    'approach_description': 'First attempt to fix syntax',
                    'code_changes_made': 'Added missing newline',
                    'lessons_learned': 'Need to check for proper line endings',
                    'why_approach_failed': 'Still has syntax issues',
                    'what_worked_partially': 'Basic structure is correct'
                },
                'test_results': {"overall_status": "failed", "test_cases": [{"status": "failed"}]},
                'test_execution_result': None,
                'error': 'Still has syntax issues',
                'original_code': {"test_file.py": "def test_function():\n    return 1"},
                'timestamp': datetime.now().isoformat()
            },
            {
                'attempt_number': 2,
                'status': 'success',
                'changes': {
                    'type': 'llm_fix',
                    'approach_description': 'Second attempt with proper formatting',
                    'code_changes_made': 'Added proper spacing and newlines',
                    'lessons_learned': 'Proper formatting is essential',
                    'why_approach_failed': None,
                    'what_worked_partially': 'Complete fix achieved'
                },
                'test_results': {"overall_status": "passed", "test_cases": [{"status": "passed"}]},
                'test_execution_result': None,
                'error': None,
                'original_code': {"test_file.py": "def test_function():\n    return 1"},
                'timestamp': datetime.now().isoformat()
            }
        ]
    )
    
    # Create test-logs directory if it doesn't exist
    test_logs_dir = Path("test-logs")
    test_logs_dir.mkdir(exist_ok=True)
    
    # Generate summary report
    console.print("🔍 Generating summary report with attempts...")
    report_path = _save_summary_report(console, test_result, mock_config)
    
    # Read the generated report
    with open(report_path, 'r') as f:
        report_content = f.read()
    
    console.print(f"📄 Generated report: {report_path}")
    console.print(f"📊 Report length: {len(report_content)} characters")
    
    # Check for attempts information in the report
    console.print("\n🔍 Analyzing report content for attempts information...")
    
    # Check for attempts table
    has_attempts_table = "| Attempt" in report_content and "| Status" in report_content
    console.print(f"✅ Attempts table found: {has_attempts_table}")
    
    # Check for specific attempt details
    has_attempt_1 = "First attempt to fix syntax" in report_content
    has_attempt_2 = "Second attempt with proper formatting" in report_content
    console.print(f"✅ Attempt 1 details found: {has_attempt_1}")
    console.print(f"✅ Attempt 2 details found: {has_attempt_2}")
    
    # Check for attempt numbers
    has_attempt_numbers = "Attempt 1" in report_content and "Attempt 2" in report_content
    console.print(f"✅ Attempt numbers found: {has_attempt_numbers}")
    
    # Check for status information
    has_failed_status = "failed" in report_content.lower()
    has_success_status = "success" in report_content.lower()
    console.print(f"✅ Failed status found: {has_failed_status}")
    console.print(f"✅ Success status found: {has_success_status}")
    
    # Check for lessons learned
    has_lessons_learned = "lessons learned" in report_content.lower() or "lessons_learned" in report_content
    console.print(f"✅ Lessons learned found: {has_lessons_learned}")
    
    # Check for approach descriptions
    has_approach_descriptions = "approach_description" in report_content or "Approach" in report_content
    console.print(f"✅ Approach descriptions found: {has_approach_descriptions}")
    
    # Extract and display the attempts table if it exists
    table_match = re.search(r'(\|.*Attempt.*\n\|.*\n\|.*\n.*)', report_content, re.MULTILINE)
    if table_match:
        console.print("\n📋 Attempts table found:")
        console.print(table_match.group(1))
    else:
        console.print("\n❌ No attempts table found in report")
    
    # Extract and display any section that mentions attempts
    attempts_section_match = re.search(r'(##.*[Aa]ttempt.*\n.*)', report_content, re.MULTILINE)
    if attempts_section_match:
        console.print("\n📋 Attempts section found:")
        console.print(attempts_section_match.group(1)[:500] + "..." if len(attempts_section_match.group(1)) > 500 else attempts_section_match.group(1))
    else:
        console.print("\n❌ No attempts section found in report")
    
    # Show a sample of the report content
    console.print(f"\n📄 Sample of report content (first 1000 characters):")
    console.print(report_content[:1000] + "..." if len(report_content) > 1000 else report_content)
    
    # Clean up
    try:
        os.remove(report_path)
        console.print(f"\n🧹 Cleaned up: {report_path}")
    except Exception as e:
        console.print(f"\n⚠️ Failed to clean up {report_path}: {e}")
    
    # Summary
    console.print(f"\n📊 Summary:")
    console.print(f"   - Report generated: ✅")
    console.print(f"   - Attempts table: {'✅' if has_attempts_table else '❌'}")
    console.print(f"   - Attempt details: {'✅' if has_attempt_1 and has_attempt_2 else '❌'}")
    console.print(f"   - Status information: {'✅' if has_failed_status and has_success_status else '❌'}")
    console.print(f"   - Lessons learned: {'✅' if has_lessons_learned else '❌'}")
    console.print(f"   - Approach descriptions: {'✅' if has_approach_descriptions else '❌'}")

if __name__ == "__main__":
    test_summary_report_attempts_content() 