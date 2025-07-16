#!/usr/bin/env python3
"""
Test the flow from memory best attempt to PRManager PR description generation.
This simulates lines 1705-1718 in kaizen/autofix/main.py.
"""
import sys
from pathlib import Path
from datetime import datetime
import json

from kaizen.cli.commands.memory import ExecutionMemory, LLMInteraction
from kaizen.autofix.main import AutoFix
from kaizen.autofix.pr.manager import PRManager, AgentInfo
from kaizen.cli.commands.models import TestExecutionResult, TestStatus, TestCaseResult, TestExecutionHistory

def create_mock_test_execution_result(attempt_number: int, passed_tests: int, total_tests: int = 3) -> TestExecutionResult:
    test_cases = []
    for i in range(total_tests):
        status = TestStatus.PASSED if i < passed_tests else TestStatus.FAILED
        test_case = TestCaseResult(
            name=f"test_case_{i+1}",
            status=status,
            input=f"input_{i+1}",
            expected_output=f"expected_{i+1}",
            actual_output=f"actual_{i+1}" if status == TestStatus.PASSED else f"error_{i+1}",
            evaluation={"score": 1.0 if status == TestStatus.PASSED else 0.0},
            error_message=None if status == TestStatus.PASSED else f"Test {i+1} failed"
        )
        test_cases.append(test_case)
    result = TestExecutionResult(
        name=f"test_execution_{attempt_number}",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml")
    )
    result.add_test_cases(test_cases)
    if passed_tests == total_tests:
        result.status = TestStatus.PASSED
    else:
        result.status = TestStatus.FAILED
    return result

def create_mock_llm_interaction(attempt_number: int) -> LLMInteraction:
    return LLMInteraction(
        interaction_type="code_fixing",
        prompt=f"Fix the code for attempt {attempt_number}",
        response=f"Here's the fixed code for attempt {attempt_number}",
        reasoning=f"Applied fixes based on error analysis for attempt {attempt_number}",
        metadata={"model": "gemini-2.0-flash", "tokens_used": 1500, "temperature": 0.1}
    )

def create_unified_format_test_results(test_execution_result: TestExecutionResult) -> dict:
    """Create test results in the unified format that find_best_attempt expects."""
    return {
        'summary': {
            'total_tests': test_execution_result.summary.total_tests,
            'passed_tests': test_execution_result.summary.passed_tests,
            'failed_tests': test_execution_result.summary.failed_tests,
            'error_tests': test_execution_result.summary.error_tests,
            'success_rate': test_execution_result.summary.get_success_rate()
        },
        'test_cases': [
            {
                'name': tc.name,
                'status': tc.status.value,
                'input': tc.input,
                'expected_output': tc.expected_output,
                'actual_output': tc.actual_output,
                'evaluation': tc.evaluation,
                'error_message': tc.error_message
            }
            for tc in test_execution_result.test_cases
        ]
    }

def test_pr_flow_from_memory():
    print("\n🧪 Testing PR flow from memory to PRManager...")
    
    # Step 1: Setup memory with several attempts
    memory = ExecutionMemory()
    memory.start_execution("test_execution_456", config={
        'name': 'test_config',
        'file_path': 'test_file.py',
        'max_retries': 3,
        'create_pr': True,
        'language': 'python'
    })
    
    # Create test results
    baseline_result = create_mock_test_execution_result(0, 0, 3)  # 0/3 passed
    attempt1_result = create_mock_test_execution_result(1, 1, 3)  # 1/3 passed
    attempt2_result = create_mock_test_execution_result(2, 2, 3)  # 2/3 passed
    attempt3_result = create_mock_test_execution_result(3, 3, 3)  # 3/3 passed
    
    print(f"   Created test results:")
    print(f"     - Baseline: {baseline_result.summary.passed_tests}/{baseline_result.summary.total_tests} passed")
    print(f"     - Attempt 1: {attempt1_result.summary.passed_tests}/{attempt1_result.summary.total_tests} passed")
    print(f"     - Attempt 2: {attempt2_result.summary.passed_tests}/{attempt2_result.summary.total_tests} passed")
    print(f"     - Attempt 3: {attempt3_result.summary.passed_tests}/{attempt3_result.summary.total_tests} passed")
    
    # Log attempts to memory with unified format
    memory.log_fix_attempt(
        file_path="test_file.py", 
        attempt_number=0, 
        original_code="def test_function():\n    return 1",
        fixed_code="def test_function():\n    return 1", 
        success=False, 
        test_results_before={},
        test_results_after=create_unified_format_test_results(baseline_result),  # Use unified format
        approach_description="Baseline test run",
        code_changes="No changes made", 
        llm_interaction=create_mock_llm_interaction(0)
    )
    
    memory.log_fix_attempt(
        file_path="test_file.py", 
        attempt_number=1, 
        original_code="def test_function():\n    return 1",
        fixed_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True", 
        success=False,
        test_results_before=create_unified_format_test_results(baseline_result),
        test_results_after=create_unified_format_test_results(attempt1_result),  # Use unified format
        approach_description="First attempt with basic fixes", 
        code_changes="Added test_case_1 function",
        llm_interaction=create_mock_llm_interaction(1)
    )
    
    memory.log_fix_attempt(
        file_path="test_file.py", 
        attempt_number=2, 
        original_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True",
        fixed_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True\n\ndef test_case_2():\n    return True", 
        success=False,
        test_results_before=create_unified_format_test_results(attempt1_result),
        test_results_after=create_unified_format_test_results(attempt2_result),  # Use unified format
        approach_description="Second attempt with additional fixes", 
        code_changes="Added test_case_2 function",
        llm_interaction=create_mock_llm_interaction(2)
    )
    
    memory.log_fix_attempt(
        file_path="test_file.py", 
        attempt_number=3, 
        original_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True\n\ndef test_case_2():\n    return True",
        fixed_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True\n\ndef test_case_2():\n    return True\n\ndef test_case_3():\n    return True", 
        success=True,
        test_results_before=create_unified_format_test_results(attempt2_result),
        test_results_after=create_unified_format_test_results(attempt3_result),  # Use unified format
        approach_description="Final attempt with complete fixes", 
        code_changes="Added test_case_3 function",
        llm_interaction=create_mock_llm_interaction(3)
    )
    
    print(f"   ✓ Logged {len(memory.current_execution['fix_attempts'])} attempts to memory")
    
    # Debug: Check the structure of test_results_after in the first attempt
    first_attempt = memory.current_execution['fix_attempts'][0]
    print(f"\n   Debug: First attempt test_results_after structure:")
    print(f"     Keys: {list(first_attempt.test_results_after.keys())}")
    if 'summary' in first_attempt.test_results_after:
        print(f"     Summary: {first_attempt.test_results_after['summary']}")
    else:
        print(f"     No 'summary' key found!")
    
    # Step 2: Setup TestExecutionHistory
    test_history = TestExecutionHistory()
    test_history.add_baseline_result(baseline_result)
    test_history.add_fix_attempt_result(attempt1_result)
    test_history.add_fix_attempt_result(attempt2_result)
    test_history.add_fix_attempt_result(attempt3_result)
    
    # Step 3: Simulate main.py flow (lines 1705-1718)
    best_attempt = memory.find_best_attempt("test_file.py")
    print(f"\n   Best attempt from memory: {best_attempt}")
    
    if best_attempt:
        print(f"   ✓ Best attempt found with success rate: {best_attempt.get('success_rate', 0)}")
        
        improvement_summary = test_history.get_improvement_summary()
        print(f"   Improvement summary: {improvement_summary}")
        
        autofix = AutoFix(
            {'max_retries': 3, 'create_pr': True}, 
            {'name': 'test_config', 'file_path': 'test_file.py', 'tests': []}, 
            memory=memory
        )
        
        test_results_for_pr = autofix._create_test_results_for_pr_from_history(test_history)
        print(f"   ✓ Created test results for PR with {len(test_results_for_pr.get('attempts', []))} attempts")
        
        pr_manager = PRManager({'create_pr': True, 'base_branch': 'main'})
        pr_data = pr_manager.create_pr(
            {'test_file.py': [{'description': 'Fixed test function', 'reason': 'Test'}]}, 
            test_results_for_pr
        )
        
        print("\n--- PR Data ---")
        print(json.dumps(pr_data, indent=2))
        
        print("\n--- PR Description ---")
        description = pr_data.get('description', 'No description')
        print(description)
        
        # Check table and details
        print("\n--- Validation Results ---")
        
        if "| Test Case | Baseline | Attempt 1 | Attempt 2 | Attempt 3 | Final Status | Improvement |" in description:
            print("   ✓ Table header found in PR description")
        else:
            print("   ❌ Table header missing in PR description")
            
        if "test_case_1" in description and "test_case_2" in description and "test_case_3" in description:
            print("   ✓ All test case names found in PR description")
        else:
            print("   ❌ Some test case names missing in PR description")
            
        if "Yes" in description:
            print("   ✓ Improvement indicator 'Yes' found in PR description")
        else:
            print("   ❌ Improvement indicator 'Yes' missing in PR description")
            
        if "## Detailed Results" in description:
            print("   ✓ Detailed Results section found")
        else:
            print("   ❌ Detailed Results section missing")
            
        # Check for specific improvement data
        if "test_case_1 | failed | passed | passed | passed | passed | Yes" in description:
            print("   ✓ test_case_1 improvement data found")
        else:
            print("   ❌ test_case_1 improvement data missing")
            
        if "test_case_2 | failed | failed | passed | passed | passed | Yes" in description:
            print("   ✓ test_case_2 improvement data found")
        else:
            print("   ❌ test_case_2 improvement data missing")
            
        if "test_case_3 | failed | failed | failed | passed | passed | Yes" in description:
            print("   ✓ test_case_3 improvement data found")
        else:
            print("   ❌ test_case_3 improvement data missing")
            
    else:
        print("   ❌ No best attempt found in memory!")
        print("   Debug: Check if test_results_after has the expected structure")
        
        # Debug: Show all attempts and their test_results_after structure
        for i, attempt in enumerate(memory.current_execution['fix_attempts']):
            print(f"     Attempt {i}:")
            print(f"       - test_results_after keys: {list(attempt.test_results_after.keys())}")
            if 'summary' in attempt.test_results_after:
                print(f"       - summary: {attempt.test_results_after['summary']}")
            else:
                print(f"       - No 'summary' key found!")

if __name__ == "__main__":
    test_pr_flow_from_memory() 