#!/usr/bin/env python3
"""Test script to verify PR structure fix."""

import sys
import os
from pathlib import Path

# Add the kaizen directory to the path
sys.path.insert(0, str(Path(__file__).parent / "kaizen"))

from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus, TestExecutionHistory
from kaizen.autofix.main import AutoFix
from kaizen.autofix.pr.manager import PRManager, TestResults, Attempt, TestCase, AgentInfo

def create_test_data():
    """Create test data to verify the fix."""
    
    # Create test cases with various evaluation types
    test_case_1 = TestCaseResult(
        name="test_basic_functionality",
        status=TestStatus.FAILED,
        region="test_region_1",
        input="test_input_1",
        expected_output="expected_1",
        actual_output="actual_1",
        evaluation={"score": 0.3, "reason": "Output mismatch"},
        error_message="Test failed"
    )
    
    test_case_2 = TestCaseResult(
        name="test_edge_cases",
        status=TestStatus.PASSED,
        region="test_region_2",
        input="test_input_2",
        expected_output="expected_2",
        actual_output="expected_2",
        evaluation={"score": 1.0, "reason": "Exact match"}
    )
    
    # Create test execution results
    baseline_result = TestExecutionResult(
        name="Test Suite",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml")
    )
    baseline_result.add_test_cases([test_case_1, test_case_2])
    
    # Create improved result
    improved_test_case_1 = TestCaseResult(
        name="test_basic_functionality",
        status=TestStatus.PASSED,
        region="test_region_1",
        input="test_input_1",
        expected_output="expected_1",
        actual_output="expected_1",
        evaluation={"score": 1.0, "reason": "Fixed"}
    )
    
    improved_result = TestExecutionResult(
        name="Test Suite",
        file_path=Path("test_file.py"),
        config_path=Path("test_config.yaml")
    )
    improved_result.add_test_cases([improved_test_case_1, test_case_2])
    
    # Create test execution history
    history = TestExecutionHistory()
    history.add_baseline_result(baseline_result)
    history.add_fix_attempt_result(improved_result)
    # Do not call set_final_result, so only two attempts are present
    
    return history

def test_pr_structure():
    """Test that the PR structure is created correctly."""
    print("Testing PR structure creation...")
    
    # Create test data
    history = create_test_data()
    
    # Create AutoFix instance (with minimal config)
    config = {
        'name': 'test_config',
        'max_retries': 1,
        'create_pr': False,
        'pr_strategy': 'ALL_PASSING',
        'base_branch': 'main',
        'auto_fix': True
    }
    runner_config = {
        'name': 'test_runner',
        'file_path': 'test_file.py',
        'tests': []
    }
    
    autofix = AutoFix(config, runner_config)
    
    # Test the method that was fixed
    test_results_for_pr = autofix._create_test_results_for_pr_from_history(history)
    
    # Verify structure
    print(f"Test results keys: {list(test_results_for_pr.keys())}")
    
    assert 'agent_info' in test_results_for_pr
    assert 'attempts' in test_results_for_pr
    assert 'additional_summary' in test_results_for_pr
    
    agent_info = test_results_for_pr['agent_info']
    assert agent_info['name'] == 'Kaizen AutoFix Agent'
    assert agent_info['version'] == '1.0.0'
    
    attempts = test_results_for_pr['attempts']
    assert len(attempts) == 2  # baseline + fix attempt
    
    # Verify first attempt (baseline)
    baseline_attempt = attempts[0]
    assert baseline_attempt['status'] == 'failed'
    assert len(baseline_attempt['test_cases']) == 2
    
    # Verify test cases
    test_case = baseline_attempt['test_cases'][0]
    assert test_case['name'] == 'test_basic_functionality'
    assert test_case['status'] == 'failed'
    assert test_case['input'] == 'test_input_1'
    assert test_case['expected_output'] == 'expected_1'
    assert test_case['actual_output'] == 'actual_1'
    assert test_case['reason'] == 'Test failed'
    
    # Verify evaluation is serialized as string
    assert isinstance(test_case['evaluation'], str)
    print(f"Evaluation (type: {type(test_case['evaluation'])}): {test_case['evaluation']}")
    
    print("✅ PR structure creation test passed!")

def test_json_serialization():
    """Test that the test results can be serialized to JSON."""
    print("\nTesting JSON serialization...")
    
    # Create test data
    history = create_test_data()
    
    # Create AutoFix instance
    config = {
        'name': 'test_config',
        'max_retries': 1,
        'create_pr': False,
        'pr_strategy': 'ALL_PASSING',
        'base_branch': 'main',
        'auto_fix': True
    }
    runner_config = {
        'name': 'test_runner',
        'file_path': 'test_file.py',
        'tests': []
    }
    
    autofix = AutoFix(config, runner_config)
    
    # Create test results
    test_results_for_pr = autofix._create_test_results_for_pr_from_history(history)
    
    # Test JSON serialization
    import json
    try:
        json_str = json.dumps(test_results_for_pr, indent=2, default=str)
        print(f"JSON serialization successful! Length: {len(json_str)}")
        print("✅ JSON serialization test passed!")
        return True
    except Exception as e:
        print(f"❌ JSON serialization failed: {str(e)}")
        return False

def test_pr_manager_integration():
    """Test integration with PR manager."""
    print("\nTesting PR manager integration...")
    
    # Create test data
    history = create_test_data()
    
    # Create AutoFix instance
    config = {
        'name': 'test_config',
        'max_retries': 1,
        'create_pr': False,
        'pr_strategy': 'ALL_PASSING',
        'base_branch': 'main',
        'auto_fix': True
    }
    runner_config = {
        'name': 'test_runner',
        'file_path': 'test_file.py',
        'tests': []
    }
    
    autofix = AutoFix(config, runner_config)
    
    # Create test results
    test_results_for_pr = autofix._create_test_results_for_pr_from_history(history)
    
    # Create PR manager
    pr_config = {
        'base_branch': 'main',
        'auto_commit_changes': False
    }
    
    # Mock GitHub token for testing
    os.environ['GITHUB_TOKEN'] = 'test_token'
    
    try:
        pr_manager = PRManager(pr_config)
        
        # Test description generation
        changes = {
            'test_file.py': [
                {
                    'description': 'Fixed test functionality',
                    'reason': 'Test was failing'
                }
            ]
        }
        
        # Test that description generation doesn't fail
        description = pr_manager._generate_pr_description(changes, test_results_for_pr)
        print(f"Description generation successful! Length: {len(description)}")
        print("✅ PR manager integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ PR manager integration failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing PR structure fix...")
    
    try:
        test_pr_structure()
        json_success = test_json_serialization()
        pr_success = test_pr_manager_integration()
        
        if json_success and pr_success:
            print("\n🎉 All tests passed! The PR structure fix is working correctly.")
        else:
            print("\n❌ Some tests failed. Please check the implementation.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 