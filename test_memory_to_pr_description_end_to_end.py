#!/usr/bin/env python3
"""
Comprehensive test for memory-to-PR-description flow.

This test verifies that:
1. Memory system stores attempts in the new format
2. AutoFix converts memory attempts to legacy format correctly
3. PRManager generates proper test results table from converted data
4. PR description contains the expected table structure and content
5. All data flows correctly through the entire pipeline
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.cli.commands.memory import ExecutionMemory, FixAttempt, LLMInteraction, TestCase
from kaizen.autofix.main import AutoFix
from kaizen.autofix.pr.manager import PRManager, TestResults, Attempt, TestCase as PRTestCase, AgentInfo
from kaizen.cli.commands.models import TestExecutionResult, TestStatus, TestCaseResult
from kaizen.utils.test_utils import create_test_execution_result

def create_mock_test_execution_result(attempt_number: int, passed_tests: int, total_tests: int = 3) -> TestExecutionResult:
    """Create a mock TestExecutionResult for testing."""
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
    
    # Create TestExecutionResult with required parameters
    result = TestExecutionResult(
        name=f"test_execution_{attempt_number}",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml")
    )
    
    # Add test cases
    result.add_test_cases(test_cases)
    
    # Set status based on passed tests
    if passed_tests == total_tests:
        result.status = TestStatus.PASSED
    else:
        result.status = TestStatus.FAILED
    
    return result

def create_mock_llm_interaction(attempt_number: int) -> LLMInteraction:
    """Create a mock LLM interaction."""
    return LLMInteraction(
        interaction_type="code_fixing",
        prompt=f"Fix the code for attempt {attempt_number}",
        response=f"Here's the fixed code for attempt {attempt_number}",
        reasoning=f"Applied fixes based on error analysis for attempt {attempt_number}",
        metadata={
            "model": "gemini-2.0-flash",
            "tokens_used": 1500,
            "temperature": 0.1
        }
    )

def test_memory_to_pr_description_end_to_end():
    """Test the complete flow from memory to PR description."""
    print("🧪 Testing Memory-to-PR-Description End-to-End Flow")
    print("=" * 60)
    
    # Step 1: Initialize memory system
    print("\n1️⃣ Initializing memory system...")
    memory = ExecutionMemory()
    memory.start_execution("test_execution_123", config={
        'name': 'test_config',
        'file_path': 'test_file.py',
        'max_retries': 3,
        'create_pr': True,
        'language': 'python'
    })
    
    print(f"   ✓ Memory system initialized with execution ID: {memory.current_execution['execution_id']}")
    
    # Step 2: Create mock test results for different attempts
    print("\n2️⃣ Creating mock test results...")
    
    # Baseline: 0/3 tests passed
    baseline_result = create_mock_test_execution_result(1, 0, 3)
    
    # Attempt 1: 1/3 tests passed (improvement)
    attempt1_result = create_mock_test_execution_result(1, 1, 3)
    
    # Attempt 2: 2/3 tests passed (further improvement)
    attempt2_result = create_mock_test_execution_result(2, 2, 3)
    
    # Attempt 3: 3/3 tests passed (complete success)
    attempt3_result = create_mock_test_execution_result(3, 3, 3)
    
    print(f"   ✓ Created test results:")
    print(f"     - Baseline: 0/3 passed")
    print(f"     - Attempt 1: 1/3 passed")
    print(f"     - Attempt 2: 2/3 passed")
    print(f"     - Attempt 3: 3/3 passed")
    
    # Step 3: Log attempts to memory system
    print("\n3️⃣ Logging attempts to memory system...")
    
    # Log baseline attempt
    llm_interaction_baseline = create_mock_llm_interaction(0)
    memory.log_fix_attempt(
        file_path="test_file.py",
        attempt_number=0,  # Baseline
        original_code="def test_function():\n    return 1",
        fixed_code="def test_function():\n    return 1",
        success=False,  # No tests passed
        test_results_before={},
        test_results_after=baseline_result.to_legacy_format(),
        approach_description="Baseline test run",
        code_changes="No changes made",
        llm_interaction=llm_interaction_baseline
    )
    
    # Log attempt 1
    llm_interaction1 = create_mock_llm_interaction(1)
    memory.log_fix_attempt(
        file_path="test_file.py",
        attempt_number=1,
        original_code="def test_function():\n    return 1",
        fixed_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True",
        success=False,  # Some tests passed
        test_results_before=baseline_result.to_legacy_format(),
        test_results_after=attempt1_result.to_legacy_format(),
        approach_description="First attempt with basic fixes",
        code_changes="Added test_case_1 function",
        llm_interaction=llm_interaction1
    )
    
    # Log attempt 2
    llm_interaction2 = create_mock_llm_interaction(2)
    memory.log_fix_attempt(
        file_path="test_file.py",
        attempt_number=2,
        original_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True",
        fixed_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True\n\ndef test_case_2():\n    return True",
        success=False,  # Most tests passed
        test_results_before=attempt1_result.to_legacy_format(),
        test_results_after=attempt2_result.to_legacy_format(),
        approach_description="Second attempt with additional fixes",
        code_changes="Added test_case_2 function",
        llm_interaction=llm_interaction2
    )
    
    # Log attempt 3
    llm_interaction3 = create_mock_llm_interaction(3)
    memory.log_fix_attempt(
        file_path="test_file.py",
        attempt_number=3,
        original_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True\n\ndef test_case_2():\n    return True",
        fixed_code="def test_function():\n    return 1\n\ndef test_case_1():\n    return True\n\ndef test_case_2():\n    return True\n\ndef test_case_3():\n    return True",
        success=True,  # All tests passed
        test_results_before=attempt2_result.to_legacy_format(),
        test_results_after=attempt3_result.to_legacy_format(),
        approach_description="Final attempt with complete fixes",
        code_changes="Added test_case_3 function",
        llm_interaction=llm_interaction3
    )
    
    print(f"   ✓ Logged {len(memory.current_execution['fix_attempts'])} attempts to memory")
    
    # Step 4: Convert attempts from memory (like AutoFix does)
    print("\n4️⃣ Converting attempts from memory to legacy format...")
    
    config = {'max_retries': 3, 'create_pr': True}
    runner_config = {
        'name': 'test_config',
        'file_path': 'test_file.py',
        'tests': []
    }
    autofix = AutoFix(config, runner_config, memory=memory)
    
    # Convert attempts from memory
    attempts = autofix._get_attempts_from_memory("test_file.py")
    print(f"   ✓ Converted {len(attempts)} attempts from memory")
    
    # Verify attempt structure
    for i, attempt in enumerate(attempts):
        print(f"   Attempt {i}:")
        print(f"     - Number: {attempt['attempt_number']}")
        print(f"     - Status: {attempt['status']}")
        print(f"     - Changes type: {attempt['changes']['type']}")
        print(f"     - Approach: {attempt['changes']['approach_description']}")
        print(f"     - Test results type: {type(attempt['test_results'])}")
        if attempt['test_results']:
            print(f"     - Test results keys: {list(attempt['test_results'].keys())}")
    
    # Step 5: Create TestResults structure for PRManager
    print("\n5️⃣ Creating TestResults structure for PRManager...")
    
    # Create agent info
    agent_info: AgentInfo = {
        'name': 'Kaizen AutoFix Agent',
        'version': '1.0.0',
        'description': 'Automated code fixing agent using LLM-based analysis'
    }
    
    # Convert attempts to PRManager format
    pr_attempts = []
    for i, attempt in enumerate(attempts):
        # Debug: Print the structure of test_results
        print(f"   Debug attempt {i} test_results structure:")
        if attempt['test_results']:
            print(f"     Keys: {list(attempt['test_results'].keys())}")
            if 'tests' in attempt['test_results']:
                print(f"     Tests keys: {list(attempt['test_results']['tests'].keys())}")
                if 'test_cases' in attempt['test_results']['tests']:
                    print(f"     Test cases count: {len(attempt['test_results']['tests']['test_cases'])}")
                    for j, tc in enumerate(attempt['test_results']['tests']['test_cases']):
                        print(f"       Test case {j}: {tc.get('name', 'Unknown')} - {tc.get('status', 'Unknown')}")
        
        # Extract test cases from the attempt's test results
        test_cases = []
        if attempt['test_results'] and 'tests' in attempt['test_results']:
            tests_data = attempt['test_results']['tests']
            if 'test_cases' in tests_data:
                for tc in tests_data['test_cases']:
                    pr_test_case: PRTestCase = {
                        'name': tc['name'],
                        'status': tc['status'],
                        'input': tc.get('input', 'N/A'),
                        'expected_output': tc.get('expected_output', 'N/A'),
                        'actual_output': tc.get('output', 'N/A'),  # Note: legacy format uses 'output' not 'actual_output'
                        'evaluation': json.dumps(tc.get('evaluation', {})) if tc.get('evaluation') else None,
                        'reason': tc.get('error')
                    }
                    test_cases.append(pr_test_case)
        
        pr_attempt: Attempt = {
            'status': attempt['status'],
            'test_cases': test_cases
        }
        pr_attempts.append(pr_attempt)
    
    # Create TestResults structure
    test_results: TestResults = {
        'agent_info': agent_info,
        'attempts': pr_attempts,
        'additional_summary': f"Total attempts: {len(pr_attempts)}"
    }
    
    print(f"   ✓ Created TestResults with {len(pr_attempts)} attempts")
    print(f"   ✓ Each attempt has {len(pr_attempts[0]['test_cases']) if pr_attempts else 0} test cases")
    
    # Step 6: Test PRManager table generation
    print("\n6️⃣ Testing PRManager table generation...")
    
    pr_manager = PRManager({'create_pr': True, 'base_branch': 'main'})
    
    # Generate test results table
    test_results_table = pr_manager._generate_test_results_table(test_results)
    print(f"   ✓ Generated test results table:")
    print(f"   Table length: {len(test_results_table)} characters")
    
    # Print the table for inspection
    print("\n   Generated Table:")
    print("   " + "-" * 50)
    for line in test_results_table.split('\n'):
        print(f"   {line}")
    print("   " + "-" * 50)
    
    # Step 7: Test complete PR description generation
    print("\n7️⃣ Testing complete PR description generation...")
    
    # Create mock changes
    changes = {
        'test_file.py': [{
            'description': 'Fixed test function implementation',
            'reason': 'Addressing test failures'
        }]
    }
    
    # Generate PR description
    pr_description = pr_manager.generate_summary_report(changes, test_results)
    print(f"   ✓ Generated PR description:")
    print(f"   Description length: {len(pr_description)} characters")
    
    # Verify table is present in description
    if "Test Results Summary" in pr_description:
        print("   ✓ Test Results Summary section found")
    else:
        print("   ❌ Test Results Summary section missing")
        return False
    
    if "| Test Case | Baseline | Attempt 1 | Attempt 2 | Attempt 3 | Final Status | Improvement |" in pr_description:
        print("   ✓ Test results table header found")
    else:
        print("   ❌ Test results table header missing")
        return False
    
    # Verify specific test case data is present
    if "test_case_1" in pr_description and "test_case_2" in pr_description and "test_case_3" in pr_description:
        print("   ✓ All test case names found in description")
    else:
        print("   ❌ Some test case names missing from description")
        return False
    
    # Verify improvement data is present
    if "Yes" in pr_description and "No" in pr_description:
        print("   ✓ Improvement indicators found in description")
    else:
        print("   ❌ Improvement indicators missing from description")
        return False
    
    # Step 8: Verify table structure and content
    print("\n8️⃣ Verifying table structure and content...")
    
    # Extract table from description
    lines = pr_description.split('\n')
    table_start = -1
    table_end = -1
    
    for i, line in enumerate(lines):
        if "| Test Case | Baseline |" in line:
            table_start = i
        elif table_start != -1 and line.strip() == "":
            table_end = i
            break
    
    if table_start != -1 and table_end != -1:
        table_lines = lines[table_start:table_end]
        print(f"   ✓ Extracted table with {len(table_lines)} lines")
        
        # Verify table structure
        if len(table_lines) >= 5:  # Header + separator + 3 test cases
            print("   ✓ Table has expected number of lines")
        else:
            print(f"   ❌ Table has unexpected number of lines: {len(table_lines)}")
            return False
        
        # Verify each test case row
        test_case_rows = [line for line in table_lines if "test_case_" in line]
        if len(test_case_rows) == 3:
            print("   ✓ All 3 test cases found in table")
            
            # Verify improvement logic
            for row in test_case_rows:
                if "test_case_1" in row and "Yes" in row:
                    print("   ✓ test_case_1 shows improvement (Yes)")
                elif "test_case_2" in row and "Yes" in row:
                    print("   ✓ test_case_2 shows improvement (Yes)")
                elif "test_case_3" in row and "Yes" in row:
                    print("   ✓ test_case_3 shows improvement (Yes)")
        else:
            print(f"   ❌ Expected 3 test case rows, found {len(test_case_rows)}")
            return False
    else:
        print("   ❌ Could not extract table from description")
        return False
    
    # Step 9: Test detailed results section
    print("\n9️⃣ Testing detailed results section...")
    
    if "## Detailed Results" in pr_description:
        print("   ✓ Detailed Results section found")
    else:
        print("   ❌ Detailed Results section missing")
        return False
    
    if "### Baseline (Before Fixes)" in pr_description:
        print("   ✓ Baseline section found")
    else:
        print("   ❌ Baseline section missing")
        return False
    
    if "### Best Attempt (Attempt 3)" in pr_description:
        print("   ✓ Best Attempt section found")
    else:
        print("   ❌ Best Attempt section missing")
        return False
    
    # Verify test case details in detailed results
    for test_case_name in ["test_case_1", "test_case_2", "test_case_3"]:
        if test_case_name in pr_description:
            print(f"   ✓ {test_case_name} found in detailed results")
        else:
            print(f"   ❌ {test_case_name} missing from detailed results")
            return False
    
    # Step 10: Final validation
    print("\n🔟 Final validation...")
    
    # Check that the description is well-formed
    if len(pr_description) > 1000:  # Should be substantial
        print("   ✓ PR description has substantial content")
    else:
        print(f"   ❌ PR description too short: {len(pr_description)} characters")
        return False
    
    # Check for proper markdown formatting
    if "## " in pr_description and "### " in pr_description:
        print("   ✓ PR description has proper markdown headers")
    else:
        print("   ❌ PR description missing proper markdown headers")
        return False
    
    # Check for agent information
    if "Kaizen AutoFix Agent" in pr_description:
        print("   ✓ Agent information included in description")
    else:
        print("   ❌ Agent information missing from description")
        return False
    
    print("\n✅ All tests passed! Memory-to-PR-description flow works correctly.")
    print("\n📋 Summary:")
    print(f"   - Memory system stored {len(attempts)} attempts")
    print(f"   - AutoFix converted attempts successfully")
    print(f"   - PRManager generated {len(test_results_table)} character table")
    print(f"   - Complete PR description: {len(pr_description)} characters")
    print(f"   - Table structure: Valid")
    print(f"   - Content accuracy: Valid")
    
    return True

def test_table_generation_edge_cases():
    """Test edge cases in table generation."""
    print("\n🧪 Testing Table Generation Edge Cases")
    print("=" * 50)
    
    pr_manager = PRManager({'create_pr': True, 'base_branch': 'main'})
    
    # Test 1: Empty attempts
    print("\n1️⃣ Testing empty attempts...")
    empty_test_results: TestResults = {
        'agent_info': None,
        'attempts': [],
        'additional_summary': None
    }
    
    empty_table = pr_manager._generate_test_results_table(empty_test_results)
    if empty_table == "No test results available":
        print("   ✓ Empty attempts handled correctly")
    else:
        print(f"   ❌ Empty attempts not handled correctly: {empty_table}")
        return False
    
    # Test 2: Single attempt
    print("\n2️⃣ Testing single attempt...")
    single_attempt: Attempt = {
        'status': 'failed',
        'test_cases': [
            {
                'name': 'test_1',
                'status': 'failed',
                'input': 'input_1',
                'expected_output': 'expected_1',
                'actual_output': 'actual_1',
                'evaluation': None,
                'reason': 'Test failed'
            }
        ]
    }
    
    single_test_results: TestResults = {
        'agent_info': None,
        'attempts': [single_attempt],
        'additional_summary': None
    }
    
    single_table = pr_manager._generate_test_results_table(single_test_results)
    if "| Test Case | Baseline | Final Status | Improvement |" in single_table:
        print("   ✓ Single attempt table generated correctly")
    else:
        print(f"   ❌ Single attempt table incorrect: {single_table}")
        return False
    
    # Test 3: Mixed status values
    print("\n3️⃣ Testing mixed status values...")
    mixed_attempt: Attempt = {
        'status': 'failed',
        'test_cases': [
            {
                'name': 'test_1',
                'status': 'passed',
                'input': 'input_1',
                'expected_output': 'expected_1',
                'actual_output': 'actual_1',
                'evaluation': None,
                'reason': None
            },
            {
                'name': 'test_2',
                'status': 'error',
                'input': 'input_2',
                'expected_output': 'expected_2',
                'actual_output': 'error_2',
                'evaluation': None,
                'reason': 'Test error'
            }
        ]
    }
    
    mixed_test_results: TestResults = {
        'agent_info': None,
        'attempts': [mixed_attempt],
        'additional_summary': None
    }
    
    mixed_table = pr_manager._generate_test_results_table(mixed_test_results)
    if "passed" in mixed_table and "error" in mixed_table:
        print("   ✓ Mixed status values handled correctly")
    else:
        print(f"   ❌ Mixed status values not handled correctly: {mixed_table}")
        return False
    
    print("\n✅ All edge case tests passed!")
    return True

if __name__ == "__main__":
    print("🚀 Starting Memory-to-PR-Description End-to-End Tests")
    print("=" * 70)
    
    try:
        # Run main test
        main_success = test_memory_to_pr_description_end_to_end()
        
        # Run edge case tests
        edge_success = test_table_generation_edge_cases()
        
        if main_success and edge_success:
            print("\n🎉 All tests passed successfully!")
            print("The memory-to-PR-description flow is working correctly.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 