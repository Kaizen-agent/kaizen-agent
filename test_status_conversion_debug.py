#!/usr/bin/env python3
"""Test to debug status conversion issue where passed results become failed."""

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

def create_mock_test_execution_result(attempt_number: int, passed_tests: int, total_tests: int = 3) -> TestExecutionResult:
    """Create a mock TestExecutionResult with specified pass/fail counts."""
    from kaizen.cli.commands.models.test_execution_result import TestExecutionSummary
    
    # Create test cases with mixed pass/fail status
    test_cases = []
    for i in range(total_tests):
        status = TestStatus.PASSED if i < passed_tests else TestStatus.FAILED
        test_case = TestCaseResult(
            name=f"test_{i+1}",
            status=status,
            input=f"input_{i+1}",
            expected_output=f"expected_{i+1}",
            actual_output=f"actual_{i+1}",
            error_message=None if status == TestStatus.PASSED else f"Test {i+1} failed",
            evaluation={"score": 1.0 if status == TestStatus.PASSED else 0.0}
        )
        test_cases.append(test_case)
    
    # Create summary
    summary = TestExecutionSummary(
        total_tests=total_tests,
        passed_tests=passed_tests,
        failed_tests=total_tests - passed_tests,
        error_tests=0,
        skipped_tests=0
    )
    
    # Create TestExecutionResult
    result = TestExecutionResult(
        name=f"attempt_{attempt_number}",
        file_path="test_file.py",
        config_path="config.yaml",
        test_cases=test_cases,
        status=TestStatus.PASSED if passed_tests == total_tests else TestStatus.FAILED,
        summary=summary
    )
    
    return result

def test_status_conversion_debug():
    """Test to debug status conversion issues."""
    console = Console()
    console.print("[bold]Testing Status Conversion Debug[/bold]")
    
    # Create memory with passed attempts
    memory = ExecutionMemory()
    memory.start_execution("test_status_conversion_debug", config=None)
    
    # Create LLM interaction
    llm_interaction = LLMInteraction(
        interaction_type="code_fixing",
        prompt="Fix the code",
        response="Here's the fixed code",
        reasoning="The code had syntax errors"
    )
    
    # Create test execution results with passed tests
    attempt1_result = create_mock_test_execution_result(1, 2, 3)  # 2 passed, 1 failed
    attempt2_result = create_mock_test_execution_result(2, 3, 3)  # 3 passed, 0 failed
    
    console.print(f"Attempt 1: {attempt1_result.status.value} ({attempt1_result.summary.passed_tests}/{attempt1_result.summary.total_tests} passed)")
    console.print(f"Attempt 2: {attempt2_result.status.value} ({attempt2_result.summary.passed_tests}/{attempt2_result.summary.total_tests} passed)")
    
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
        llm_interaction=llm_interaction
    )
    
    memory.log_fix_attempt(
        file_path="test_file.py",
        attempt_number=2,
        original_code="def test_function():\n    return 1",
        fixed_code="def test_function():\n    return 1",
        success=True,  # All tests passed
        test_results_before={},
        test_results_after=attempt2_result.to_legacy_format(),
        approach_description="Second attempt to fix syntax",
        code_changes="Fixed all issues",
        llm_interaction=llm_interaction
    )
    
    # Create test result with memory-based attempts
    test_result = TestResult(
        name="Test Status Conversion",
        file_path="test_file.py",
        config_path="config.yaml",
        start_time=datetime.now(),
        end_time=datetime.now(),
        status=TestStatus.PASSED,
        results={},
        test_attempts=memory.current_execution.get('fix_attempts', []),
        baseline_result=None,
        unified_result=None
    )
    
    # Create config
    config = SimpleNamespace()
    config.save_logs = True
    
    # Save summary report
    console.print("\n[bold]Generating Summary Report...[/bold]")
    report_path = _save_summary_report(console, test_result, config)
    
    if report_path and report_path.exists():
        console.print(f"\n[green]✓ Report generated: {report_path}[/green]")
        
        # Read and analyze the report
        with open(report_path, 'r') as f:
            report_content = f.read()
        
        console.print("\n[bold]Analyzing Report Content:[/bold]")
        
        # Check for status values in the table
        status_patterns = {
            'passed': len(re.findall(r'\bpassed\b', report_content, re.IGNORECASE)),
            'failed': len(re.findall(r'\bfailed\b', report_content, re.IGNORECASE)),
            'error': len(re.findall(r'\berror\b', report_content, re.IGNORECASE)),
            'N/A': len(re.findall(r'\bN/A\b', report_content)),
            'unknown': len(re.findall(r'\bunknown\b', report_content, re.IGNORECASE))
        }
        
        console.print(f"Status counts in report:")
        for status, count in status_patterns.items():
            console.print(f"  {status}: {count}")
        
        # Look for the table specifically
        table_match = re.search(r'\|.*Test Case.*\|.*Baseline.*\|.*Attempt.*\|', report_content, re.DOTALL)
        if table_match:
            table_section = table_match.group(0)
            console.print(f"\n[bold]Table Section Found:[/bold]")
            console.print(table_section[:500] + "..." if len(table_section) > 500 else table_section)
            
            # Check what statuses are in the table
            table_statuses = re.findall(r'\b(passed|failed|error|N/A|unknown)\b', table_section, re.IGNORECASE)
            console.print(f"\nStatuses found in table: {table_statuses}")
            
            # Check if passed tests are being converted to failed
            passed_in_table = len([s for s in table_statuses if s.lower() == 'passed'])
            failed_in_table = len([s for s in table_statuses if s.lower() == 'failed'])
            
            console.print(f"\n[bold]Table Analysis:[/bold]")
            console.print(f"  Passed statuses in table: {passed_in_table}")
            console.print(f"  Failed statuses in table: {failed_in_table}")
            
            if passed_in_table == 0 and failed_in_table > 0:
                console.print(f"[red]❌ ISSUE CONFIRMED: Passed tests are being converted to failed![/red]")
                return False
            elif passed_in_table > 0:
                console.print(f"[green]✅ Status conversion appears to be working correctly[/green]")
                return True
        else:
            console.print(f"[yellow]⚠️  No table found in report[/yellow]")
            return False
    else:
        console.print(f"[red]❌ Failed to generate report[/red]")
        return False

if __name__ == "__main__":
    success = test_status_conversion_debug()
    sys.exit(0 if success else 1) 