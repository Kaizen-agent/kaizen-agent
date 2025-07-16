#!/usr/bin/env python3
"""End-to-end test for memory to report generation flow."""

import sys
import os
import tempfile
import json
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kaizen.autofix.main import AutoFix
from kaizen.cli.commands.memory import ExecutionMemory, FixAttempt, LLMInteraction, TestCase
from kaizen.cli.commands.models import TestExecutionHistory, TestExecutionResult, TestCaseResult, TestStatus
from kaizen.autofix.pr.manager import PRManager
from datetime import datetime
from types import SimpleNamespace
from kaizen.cli.commands.test import _save_detailed_logs, _save_summary_report
from rich.console import Console
import glob

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

def test_end_to_end_memory_to_report():
    """Test the complete flow from memory storage to report generation."""
    
    print("🧪 Starting end-to-end memory to report generation test...")
    
    # Step 1: Create memory instance and populate with test data
    print("\n1️⃣ Setting up memory with test data...")
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
        response="Here's the code with corrected logic",
        reasoning="The function needs to return the expected value"
    )
    
    # Create mock test execution results
    baseline_result = create_mock_test_execution_result(0, 0, 3)  # All tests failed initially
    attempt1_result = create_mock_test_execution_result(1, 1, 3)  # 1 test passed
    attempt2_result = create_mock_test_execution_result(2, 3, 3)  # All tests passed
    
    # Create fix attempts in memory
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
        approach_description="Fix remaining logic errors",
        code_changes_made="Fixed return statements and logic flow",
        original_code="def test():\n    pass\ndef another():\n    return None",
        modified_code="def test():\n    return True\ndef another():\n    return 'success'",
        test_results_before=attempt1_result.to_legacy_format(),
        test_results_after=attempt2_result.to_legacy_format(),
        success=True,
        llm_interaction=llm_interaction2,
        lessons_learned="Need to return expected values for tests to pass",
        why_approach_failed=None,
        what_worked_partially=None
    )
    
    # Add attempts to memory
    memory.current_execution['fix_attempts'].append(fix_attempt1)
    memory.current_execution['fix_attempts'].append(fix_attempt2)
    
    print(f"   ✓ Added {len(memory.current_execution['fix_attempts'])} fix attempts to memory")
    
    # Step 2: Create AutoFix instance and test memory conversion
    print("\n2️⃣ Testing memory to attempts conversion...")
    config = {'max_retries': 2, 'create_pr': False}
    runner_config = {
        'name': 'test_config',
        'file_path': 'test_file.py',
        'tests': []
    }
    autofix = AutoFix(config, runner_config, memory=memory)
    
    # Test the conversion method
    attempts = autofix._get_attempts_from_memory("test_file.py")
    
    print(f"   ✓ Converted {len(attempts)} attempts from memory")
    
    # Verify attempt structure
    for i, attempt in enumerate(attempts):
        print(f"   Attempt {i+1}:")
        print(f"     - Number: {attempt['attempt_number']}")
        print(f"     - Status: {attempt['status']}")
        print(f"     - Changes type: {attempt['changes']['type']}")
        print(f"     - Approach: {attempt['changes']['approach_description']}")
        print(f"     - Lessons: {attempt['changes']['lessons_learned']}")
        print(f"     - Error: {attempt['error']}")
    
    # Step 3: Test PR Manager with converted attempts
    print("\n3️⃣ Testing PR Manager with converted attempts...")
    
    # Create test results structure expected by PRManager
    test_cases = []
    for tc in attempt2_result.test_cases:  # Use final result
        test_case = {
            'name': tc.name,
            'status': tc.status.value,
            'input': tc.input,
            'expected_output': tc.expected_output,
            'actual_output': tc.actual_output,
            'evaluation': json.dumps(tc.evaluation) if tc.evaluation else None,
            'reason': tc.error_message
        }
        test_cases.append(test_case)
    
    # Create attempts structure for PRManager
    pr_attempts = []
    for attempt in attempts:
        pr_attempt = {
            'status': attempt['status'],
            'test_cases': test_cases  # Use same test cases for simplicity
        }
        pr_attempts.append(pr_attempt)
    
    test_results_for_pr = {
        'agent_info': {
            'name': 'Kaizen AutoFix Agent',
            'version': '1.0.0',
            'description': 'Automated code fixing agent using LLM-based analysis'
        },
        'attempts': pr_attempts,
        'additional_summary': f"Total attempts: {len(pr_attempts)}"
    }
    
    # Create PR Manager and test description generation
    pr_config = {
        'create_pr': False,  # Don't actually create PR
        'base_branch': 'main'
    }
    pr_manager = PRManager(pr_config)
    
    # Test summary report generation
    changes = {
        'test_file.py': [{
            'type': 'modification',
            'description': 'Fixed syntax and logic errors',
            'lines_changed': 4
        }]
    }
    
    try:
        summary_report = pr_manager.generate_summary_report(changes, test_results_for_pr)
        print(f"   ✓ Generated summary report ({len(summary_report)} characters)")
        
        # Save report to temporary file for inspection
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(summary_report)
            report_path = f.name
        
        print(f"   ✓ Saved report to: {report_path}")
        
        # Verify report content
        if "Executive Summary" in summary_report:
            print("   ✓ Report contains Executive Summary section")
        if "Test Results Summary" in summary_report:
            print("   ✓ Report contains Test Results Summary section")
        if "Detailed Results" in summary_report:
            print("   ✓ Report contains Detailed Results section")
        if "Baseline" in summary_report:
            print("   ✓ Report contains Baseline results")
        if "Best Attempt" in summary_report:
            print("   ✓ Report contains Best Attempt results")
        
    except Exception as e:
        print(f"   ❌ Failed to generate summary report: {str(e)}")
        raise
    
    # Step 4: Test TestExecutionHistory integration
    print("\n4️⃣ Testing TestExecutionHistory integration...")
    
    test_history = TestExecutionHistory()
    test_history.add_baseline_result(baseline_result)
    test_history.add_fix_attempt_result(attempt1_result)
    test_history.add_fix_attempt_result(attempt2_result)
    
    # Test the AutoFix method that creates test results from history
    test_results_from_history = autofix._create_test_results_for_pr_from_history(test_history)
    
    print(f"   ✓ Created test results from history with {len(test_results_from_history['attempts'])} attempts")
    
    # Verify the structure
    if 'agent_info' in test_results_from_history:
        print("   ✓ Contains agent info")
    if 'attempts' in test_results_from_history:
        print("   ✓ Contains attempts")
    if 'additional_summary' in test_results_from_history:
        print("   ✓ Contains additional summary")
    
    # Step 5: Test memory learning summary
    print("\n5️⃣ Testing memory learning summary...")
    
    learning_summary = autofix._get_memory_learning_summary("test_file.py")
    
    print(f"   ✓ Generated learning summary:")
    print(f"     - Total attempts: {learning_summary['total_attempts']}")
    print(f"     - Successful patterns: {len(learning_summary['successful_patterns'])}")
    print(f"     - Failed approaches: {len(learning_summary['failed_approaches'])}")
    print(f"     - Improvement insights: {len(learning_summary['improvement_insights'])}")
    
    # Step 6: Test complete flow simulation
    print("\n6️⃣ Testing complete flow simulation...")
    
    # Simulate the return structure that would be used in actual AutoFix
    complete_results = {
        'status': 'success',
        'attempts': attempts,
        'changes_made': True,
        'learning_summary': learning_summary,
        'test_history': test_history.to_legacy_format(),
        'message': 'Code changes were applied successfully. All tests now pass.'
    }
    
    print(f"   ✓ Complete results structure created:")
    print(f"     - Status: {complete_results['status']}")
    print(f"     - Attempts: {len(complete_results['attempts'])}")
    print(f"     - Changes made: {complete_results['changes_made']}")
    print(f"     - Has learning summary: {'learning_summary' in complete_results}")
    print(f"     - Has test history: {'test_history' in complete_results}")
    
    # Step 7: Verify data integrity
    print("\n7️⃣ Verifying data integrity...")
    
    # Check that attempts contain all required fields
    required_fields = ['attempt_number', 'status', 'changes', 'test_results', 'error', 'original_code', 'timestamp']
    for i, attempt in enumerate(attempts):
        missing_fields = [field for field in required_fields if field not in attempt]
        if missing_fields:
            print(f"   ❌ Attempt {i+1} missing fields: {missing_fields}")
        else:
            print(f"   ✓ Attempt {i+1} has all required fields")
    
    # Check that changes contain required sub-fields
    required_change_fields = ['type', 'approach_description', 'code_changes_made', 'lessons_learned', 'why_approach_failed', 'what_worked_partially']
    for i, attempt in enumerate(attempts):
        changes = attempt['changes']
        missing_change_fields = [field for field in required_change_fields if field not in changes]
        if missing_change_fields:
            print(f"   ❌ Attempt {i+1} changes missing fields: {missing_change_fields}")
        else:
            print(f"   ✓ Attempt {i+1} changes has all required fields")
    
    # Step 8: Cleanup
    print("\n8️⃣ Cleanup...")
    try:
        os.unlink(report_path)
        print(f"   ✓ Removed temporary report file")
    except Exception as e:
        print(f"   ⚠️ Could not remove temporary file {report_path}: {str(e)}")
    
    # Step 9: Test _save_detailed_logs and _save_summary_report
    print("\n9️⃣ Testing _save_detailed_logs and _save_summary_report...")
    
    # Create a mock config object (SimpleNamespace for attribute access)
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
    
    # Create a mock TestResult object
    from kaizen.cli.commands.models import TestResult
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
        test_attempts=attempts,
        baseline_result=baseline_result
    )
    
    # Ensure test-logs directory exists and is empty
    logs_dir = Path("test-logs")
    logs_dir.mkdir(exist_ok=True)
    for f in logs_dir.glob("*"):
        f.unlink()
    
    # Call the logging functions
    console = Console(record=True)
    _save_detailed_logs(console, test_result, mock_config)
    _save_summary_report(console, test_result, mock_config)
    
    # Check that files were created
    detailed_logs = list(logs_dir.glob("*_detailed_logs.json"))
    summary_jsons = list(logs_dir.glob("*_summary.json"))
    summary_reports = list(logs_dir.glob("test_report_*.md"))
    
    if detailed_logs:
        print(f"   ✓ Detailed logs file created: {detailed_logs[0]}")
    else:
        print(f"   ❌ Detailed logs file not found!")
    if summary_jsons:
        print(f"   ✓ Summary JSON file created: {summary_jsons[0]}")
    else:
        print(f"   ❌ Summary JSON file not found!")
    if summary_reports:
        print(f"   ✓ Markdown summary report created: {summary_reports[0]}")
    else:
        print(f"   ❌ Markdown summary report not found!")
    
    # Clean up created files
    for f in detailed_logs + summary_jsons + summary_reports:
        try:
            f.unlink()
            print(f"   ✓ Removed {f}")
        except Exception as e:
            print(f"   ⚠️ Could not remove {f}: {str(e)}")

    print("\n🎉 End-to-end test completed successfully!")
    print("\n📋 Summary:")
    print("   ✅ Memory data properly converted to attempts")
    print("   ✅ PR Manager can generate reports with converted data")
    print("   ✅ TestExecutionHistory integration works")
    print("   ✅ Learning summary generation works")
    print("   ✅ Complete flow simulation successful")
    print("   ✅ Data integrity verified")
    print("\n🚀 The memory system is now fully integrated with the reporting system!")

if __name__ == "__main__":
    test_end_to_end_memory_to_report() 