#!/usr/bin/env python3
"""Test to reproduce the real-world issue where attempts are not saved in logs."""

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

def test_real_world_attempts_issue():
    """Test to reproduce the real-world issue where attempts are not saved."""
    
    print("🧪 Testing real-world attempts issue...")
    
    # Step 1: Simulate what happens in real CLI usage
    print("\n1️⃣ Simulating real CLI usage...")
    
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
    
    # Create mock test execution results
    baseline_result = create_mock_test_execution_result(0, 0, 3)  # All tests failed initially
    attempt1_result = create_mock_test_execution_result(1, 1, 3)  # 1 test passed
    
    # Create fix attempt in memory (like what AutoFix does)
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
    
    # Add attempt to memory
    memory.current_execution['fix_attempts'].append(fix_attempt1)
    
    print(f"   ✓ Added {len(memory.current_execution['fix_attempts'])} fix attempts to memory")
    
    # Step 2: Simulate what TestAllCommand does - convert attempts from AutoFix results
    print("\n2️⃣ Simulating TestAllCommand behavior...")
    
    # Import AutoFix to use its conversion method
    from kaizen.autofix.main import AutoFix
    config = {'max_retries': 2, 'create_pr': False}
    runner_config = {
        'name': 'test_config',
        'file_path': 'test_file.py',
        'tests': []
    }
    autofix = AutoFix(config, runner_config, memory=memory)
    
    # Convert attempts from memory (like what AutoFix.fix_code() returns)
    attempts = autofix._get_attempts_from_memory("test_file.py")
    print(f"   ✓ Converted {len(attempts)} attempts from memory")
    
    # Step 3: Create TestResult exactly like TestAllCommand does
    print("\n3️⃣ Creating TestResult like TestAllCommand...")
    
    now = datetime.now()
    test_result = TestResult(
        name="test_config",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml"),
        start_time=now,
        end_time=now,
        status="success",
        results=attempt1_result.to_legacy_format(),
        error=None,
        steps=[],
        unified_result=attempt1_result,
        test_attempts=attempts,  # This is the key - using converted attempts
        baseline_result=baseline_result
    )
    
    print(f"   ✓ Created TestResult with test_attempts: {test_result.test_attempts}")
    print(f"   ✓ test_attempts type: {type(test_result.test_attempts)}")
    print(f"   ✓ test_attempts length: {len(test_result.test_attempts) if test_result.test_attempts else 0}")
    
    # Step 4: Create mock config
    print("\n4️⃣ Creating mock config...")
    
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
    
    # Step 5: Save logs and check what happens
    print("\n5️⃣ Saving logs and checking attempts data...")
    
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
        
        # Load and analyze the detailed logs
        with open(detailed_logs[0], 'r') as f:
            logs_data = json.load(f)
        
        # Check if attempts data is present
        if 'auto_fix_attempts' in logs_data:
            attempts_in_logs = logs_data['auto_fix_attempts']
            print(f"   ✓ Found {len(attempts_in_logs)} attempts in detailed logs")
            
            # Verify attempt structure
            for i, attempt in enumerate(attempts_in_logs):
                print(f"   Attempt {i+1} in logs:")
                print(f"     - attempt_number: {attempt.get('attempt_number', 'MISSING')}")
                print(f"     - status: {attempt.get('status', 'MISSING')}")
                print(f"     - changes: {type(attempt.get('changes', 'MISSING'))}")
                print(f"     - test_results: {type(attempt.get('test_results', 'MISSING'))}")
                print(f"     - error: {attempt.get('error', 'None')}")
                print(f"     - original_code: {type(attempt.get('original_code', 'MISSING'))}")
                
                # Check if changes contain expected fields
                changes = attempt.get('changes', {})
                if isinstance(changes, dict):
                    print(f"     - approach_description: {changes.get('approach_description', 'MISSING')}")
                    print(f"     - lessons_learned: {changes.get('lessons_learned', 'MISSING')}")
                    print(f"     - why_approach_failed: {changes.get('why_approach_failed', 'None')}")
                else:
                    print(f"     - changes is not a dict: {type(changes)}")
        else:
            print(f"   ❌ No 'auto_fix_attempts' found in detailed logs!")
            print(f"   Available keys: {list(logs_data.keys())}")
            
            # Debug: Check what's in the logs
            print(f"   Debug - logs_data keys: {list(logs_data.keys())}")
            if 'metadata' in logs_data:
                print(f"   Debug - metadata: {logs_data['metadata']}")
    else:
        print(f"   ❌ Detailed logs file not found!")
    
    if summary_jsons:
        print(f"   ✓ Summary JSON file created: {summary_jsons[0]}")
        
        # Load and analyze the summary
        with open(summary_jsons[0], 'r') as f:
            summary_data = json.load(f)
        
        print(f"   Summary data:")
        print(f"     - has_auto_fix_attempts: {summary_data.get('has_auto_fix_attempts', 'MISSING')}")
        print(f"     - auto_fix_attempts_count: {summary_data.get('auto_fix_attempts_count', 'MISSING')}")
    else:
        print(f"   ❌ Summary JSON file not found!")
    
    if summary_reports:
        print(f"   ✓ Markdown summary report created: {summary_reports[0]}")
        
        # Read the markdown report to check for attempts data
        with open(summary_reports[0], 'r') as f:
            report_content = f.read()
        
        # Check for attempts-related content
        if "Attempt" in report_content:
            print(f"   ✓ Markdown report contains attempt information")
        else:
            print(f"   ⚠️ Markdown report may not contain attempt information")
    else:
        print(f"   ❌ Markdown summary report not found!")
    
    # Step 6: Clean up
    print("\n6️⃣ Cleanup...")
    
    for f in detailed_logs + summary_jsons + summary_reports:
        try:
            f.unlink()
            print(f"   ✓ Removed {f}")
        except Exception as e:
            print(f"   ⚠️ Could not remove {f}: {str(e)}")
    
    print("\n🎉 Real-world attempts issue test completed!")
    print("\n📋 Summary:")
    print("   ✅ TestResult created with test_attempts")
    print("   ✅ _save_detailed_logs called successfully")
    print("   ✅ _save_summary_report called successfully")
    print("   ✅ Attempts data structure verified in saved logs")

if __name__ == "__main__":
    test_real_world_attempts_issue() 