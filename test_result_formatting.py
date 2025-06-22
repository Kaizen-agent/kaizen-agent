#!/usr/bin/env python3
"""
Test file for result formatting, test results, best attempt logic, and PR description table generation.
This test focuses on the data processing and formatting logic without using any LLM components.
"""

import unittest
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto
import tempfile
import shutil

# Add the kaizen package to the path
sys.path.insert(0, str(Path(__file__).parent / "kaizen"))

from kaizen.autofix.main import (
    TestResultAnalyzer, 
    FixAttemptTracker, 
    FixAttempt, 
    FixStatus,
    LearningManager,
    AutoFix
)
from kaizen.autofix.pr.manager import (
    PRManager, 
    TestCase, 
    Attempt, 
    AgentInfo, 
    TestResults, 
    CodeChange
)


class MockTestRunner:
    """Mock test runner that returns predefined test results."""
    
    def __init__(self, test_results_map: Dict[str, Dict]):
        self.test_results_map = test_results_map
    
    def run_tests(self, path: Path) -> Dict:
        """Return predefined test results based on the path."""
        # Use the path as a key to get the appropriate test results
        key = str(path)
        return self.test_results_map.get(key, self._get_default_results())
    
    def _get_default_results(self) -> Dict:
        """Get default test results."""
        return {
            'overall_status': {
                'status': 'failed',
                'summary': {
                    'total_regions': 3,
                    'passed_regions': 0,
                    'failed_regions': 3,
                    'error_regions': 0
                }
            },
            'test_region_1': {
                'test_cases': [{
                    'name': 'test_basic_functionality',
                    'status': 'failed',
                    'input': 'test_input_1',
                    'expected_output': 'expected_1',
                    'output': 'actual_1',
                    'evaluation': 'failed_evaluation_1',
                    'error': 'Test failed'
                }]
            },
            'test_region_2': {
                'test_cases': [{
                    'name': 'test_edge_cases',
                    'status': 'failed',
                    'input': 'test_input_2',
                    'expected_output': 'expected_2',
                    'output': 'actual_2',
                    'evaluation': 'failed_evaluation_2',
                    'error': 'Test failed'
                }]
            },
            'test_region_3': {
                'test_cases': [{
                    'name': 'test_error_handling',
                    'status': 'error',
                    'input': 'test_input_3',
                    'expected_output': 'expected_3',
                    'output': 'actual_3',
                    'evaluation': 'error_evaluation_3',
                    'error': 'Test error'
                }]
            }
        }


class TestResultFormatting(unittest.TestCase):
    """Test class for result formatting and data processing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample test results for different scenarios
        self.baseline_results = {
            'overall_status': {
                'status': 'failed',
                'summary': {
                    'total_regions': 3,
                    'passed_regions': 0,
                    'failed_regions': 2,
                    'error_regions': 1
                }
            },
            'test_region_1': {
                'test_cases': [{
                    'name': 'test_basic_functionality',
                    'status': 'failed',
                    'input': 'test_input_1',
                    'expected_output': 'expected_1',
                    'output': 'actual_1',
                    'evaluation': 'failed_evaluation_1',
                    'error': 'Test failed'
                }]
            },
            'test_region_2': {
                'test_cases': [{
                    'name': 'test_edge_cases',
                    'status': 'failed',
                    'input': 'test_input_2',
                    'expected_output': 'expected_2',
                    'output': 'actual_2',
                    'evaluation': 'failed_evaluation_2',
                    'error': 'Test failed'
                }]
            },
            'test_region_3': {
                'test_cases': [{
                    'name': 'test_error_handling',
                    'status': 'error',
                    'input': 'test_input_3',
                    'expected_output': 'expected_3',
                    'output': 'actual_3',
                    'evaluation': 'error_evaluation_3',
                    'error': 'Test error'
                }]
            }
        }
        
        self.improved_results = {
            'overall_status': {
                'status': 'failed',
                'summary': {
                    'total_regions': 3,
                    'passed_regions': 1,
                    'failed_regions': 1,
                    'error_regions': 1
                }
            },
            'test_region_1': {
                'test_cases': [{
                    'name': 'test_basic_functionality',
                    'status': 'passed',
                    'input': 'test_input_1',
                    'expected_output': 'expected_1',
                    'output': 'expected_1',
                    'evaluation': 'passed_evaluation_1'
                }]
            },
            'test_region_2': {
                'test_cases': [{
                    'name': 'test_edge_cases',
                    'status': 'failed',
                    'input': 'test_input_2',
                    'expected_output': 'expected_2',
                    'output': 'actual_2',
                    'evaluation': 'failed_evaluation_2',
                    'error': 'Test failed'
                }]
            },
            'test_region_3': {
                'test_cases': [{
                    'name': 'test_error_handling',
                    'status': 'error',
                    'input': 'test_input_3',
                    'expected_output': 'expected_3',
                    'output': 'actual_3',
                    'evaluation': 'error_evaluation_3',
                    'error': 'Test error'
                }]
            }
        }
        
        self.successful_results = {
            'overall_status': {
                'status': 'passed',
                'summary': {
                    'total_regions': 3,
                    'passed_regions': 3,
                    'failed_regions': 0,
                    'error_regions': 0
                }
            },
            'test_region_1': {
                'test_cases': [{
                    'name': 'test_basic_functionality',
                    'status': 'passed',
                    'input': 'test_input_1',
                    'expected_output': 'expected_1',
                    'output': 'expected_1',
                    'evaluation': 'passed_evaluation_1'
                }]
            },
            'test_region_2': {
                'test_cases': [{
                    'name': 'test_edge_cases',
                    'status': 'passed',
                    'input': 'test_input_2',
                    'expected_output': 'expected_2',
                    'output': 'expected_2',
                    'evaluation': 'passed_evaluation_2'
                }]
            },
            'test_region_3': {
                'test_cases': [{
                    'name': 'test_error_handling',
                    'status': 'passed',
                    'input': 'test_input_3',
                    'expected_output': 'expected_3',
                    'output': 'expected_3',
                    'evaluation': 'passed_evaluation_3'
                }]
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_test_result_analyzer_count_passed_tests(self):
        """Test counting passed tests in test results."""
        # Test baseline results (0 passed)
        passed_count = TestResultAnalyzer.count_passed_tests(self.baseline_results)
        self.assertEqual(passed_count, 0)
        
        # Test improved results (1 passed)
        passed_count = TestResultAnalyzer.count_passed_tests(self.improved_results)
        self.assertEqual(passed_count, 1)
        
        # Test successful results (3 passed)
        passed_count = TestResultAnalyzer.count_passed_tests(self.successful_results)
        self.assertEqual(passed_count, 3)
        
        # Test empty results
        passed_count = TestResultAnalyzer.count_passed_tests({})
        self.assertEqual(passed_count, 0)
        
        # Test None results
        passed_count = TestResultAnalyzer.count_passed_tests(None)
        self.assertEqual(passed_count, 0)
    
    def test_test_result_analyzer_is_successful(self):
        """Test determining if all tests passed."""
        # Test baseline results (not successful)
        is_successful = TestResultAnalyzer.is_successful(self.baseline_results)
        self.assertFalse(is_successful)
        
        # Test improved results (not successful)
        is_successful = TestResultAnalyzer.is_successful(self.improved_results)
        self.assertFalse(is_successful)
        
        # Test successful results (successful)
        is_successful = TestResultAnalyzer.is_successful(self.successful_results)
        self.assertTrue(is_successful)
        
        # Test empty results
        is_successful = TestResultAnalyzer.is_successful({})
        self.assertFalse(is_successful)
    
    def test_test_result_analyzer_has_improvements(self):
        """Test determining if there are any test improvements."""
        # Test baseline results (no improvements)
        has_improvements = TestResultAnalyzer.has_improvements(self.baseline_results)
        self.assertFalse(has_improvements)
        
        # Test improved results (has improvements)
        has_improvements = TestResultAnalyzer.has_improvements(self.improved_results)
        self.assertTrue(has_improvements)
        
        # Test successful results (has improvements)
        has_improvements = TestResultAnalyzer.has_improvements(self.successful_results)
        self.assertTrue(has_improvements)
    
    def test_test_result_analyzer_get_improvement_summary(self):
        """Test getting improvement summary."""
        # Test baseline results
        summary = TestResultAnalyzer.get_improvement_summary(self.baseline_results)
        self.assertEqual(summary['total'], 3)
        self.assertEqual(summary['passed'], 0)
        self.assertFalse(summary['improved'])
        
        # Test improved results
        summary = TestResultAnalyzer.get_improvement_summary(self.improved_results)
        self.assertEqual(summary['total'], 3)
        self.assertEqual(summary['passed'], 1)
        self.assertTrue(summary['improved'])
        
        # Test successful results
        summary = TestResultAnalyzer.get_improvement_summary(self.successful_results)
        self.assertEqual(summary['total'], 3)
        self.assertEqual(summary['passed'], 3)
        self.assertTrue(summary['improved'])
        
        # Test empty results
        summary = TestResultAnalyzer.get_improvement_summary({})
        self.assertEqual(summary['total'], 0)
        self.assertEqual(summary['passed'], 0)
        self.assertFalse(summary['improved'])
    
    def test_fix_attempt_tracker(self):
        """Test fix attempt tracking functionality."""
        tracker = FixAttemptTracker(max_retries=3)
        
        # Test initial state
        self.assertTrue(tracker.should_continue())
        self.assertEqual(len(tracker.attempts), 0)
        self.assertIsNone(tracker.get_successful_attempt())
        self.assertIsNone(tracker.get_best_attempt())
        
        # Test first attempt
        attempt1 = tracker.start_attempt()
        self.assertEqual(attempt1.attempt_number, 1)
        self.assertEqual(attempt1.status, FixStatus.PENDING)
        self.assertEqual(len(tracker.attempts), 1)
        
        # Update first attempt with failed results
        tracker.update_attempt(attempt1, FixStatus.FAILED, {}, self.baseline_results)
        self.assertEqual(attempt1.status, FixStatus.FAILED)
        self.assertIsNone(tracker.get_successful_attempt())
        
        # Test second attempt with improvements
        attempt2 = tracker.start_attempt()
        self.assertEqual(attempt2.attempt_number, 2)
        tracker.update_attempt(attempt2, FixStatus.FAILED, {}, self.improved_results)
        
        # Test third attempt with success
        attempt3 = tracker.start_attempt()
        self.assertEqual(attempt3.attempt_number, 3)
        tracker.update_attempt(attempt3, FixStatus.SUCCESS, {}, self.successful_results)
        
        # Test final state
        self.assertFalse(tracker.should_continue())
        self.assertEqual(len(tracker.attempts), 3)
        
        # Test getting successful attempt
        successful = tracker.get_successful_attempt()
        self.assertIsNotNone(successful)
        self.assertEqual(successful.attempt_number, 3)
        self.assertEqual(successful.status, FixStatus.SUCCESS)
        
        # Test getting best attempt (should be successful one)
        best = tracker.get_best_attempt()
        self.assertIsNotNone(best)
        self.assertEqual(best.attempt_number, 3)
    
    def test_fix_attempt_tracker_best_attempt_logic(self):
        """Test the best attempt selection logic."""
        tracker = FixAttemptTracker(max_retries=3)
        
        # Create attempts with different results
        attempt1 = tracker.start_attempt()
        tracker.update_attempt(attempt1, FixStatus.FAILED, {}, self.baseline_results)
        
        attempt2 = tracker.start_attempt()
        tracker.update_attempt(attempt2, FixStatus.FAILED, {}, self.improved_results)
        
        attempt3 = tracker.start_attempt()
        tracker.update_attempt(attempt3, FixStatus.FAILED, {}, self.baseline_results)
        
        # Best attempt should be attempt2 (has improvements)
        best = tracker.get_best_attempt()
        self.assertIsNotNone(best)
        self.assertEqual(best.attempt_number, 2)
        
        # Test with no improvements
        tracker_no_improvements = FixAttemptTracker(max_retries=2)
        attempt1 = tracker_no_improvements.start_attempt()
        tracker_no_improvements.update_attempt(attempt1, FixStatus.FAILED, {}, self.baseline_results)
        
        attempt2 = tracker_no_improvements.start_attempt()
        tracker_no_improvements.update_attempt(attempt2, FixStatus.FAILED, {}, self.baseline_results)
        
        # Should return None when no improvements
        best = tracker_no_improvements.get_best_attempt()
        self.assertIsNone(best)
    
    def test_learning_manager(self):
        """Test learning manager functionality."""
        manager = LearningManager()
        
        # Test initial state
        self.assertEqual(len(manager.attempt_history), 0)
        self.assertEqual(len(manager.learned_patterns['successful_fixes']), 0)
        
        # Set baseline failures
        failure_data = {'test_failures': ['error1', 'error2']}
        manager.set_baseline_failures(failure_data)
        self.assertEqual(manager.baseline_failures, failure_data)
        
        # Record failed attempt
        manager.record_attempt(1, {}, self.baseline_results, FixStatus.FAILED)
        self.assertEqual(len(manager.attempt_history), 1)
        
        # Record improved attempt
        manager.record_attempt(2, {'file1': {'fixed_code': 'try:\n    pass\nexcept:\n    pass'}}, 
                             self.improved_results, FixStatus.FAILED)
        self.assertEqual(len(manager.attempt_history), 2)
        
        # Record successful attempt
        manager.record_attempt(3, {'file1': {'fixed_code': 'def test():\n    return True'}}, 
                             self.successful_results, FixStatus.SUCCESS)
        self.assertEqual(len(manager.attempt_history), 3)
        
        # Test learning patterns
        self.assertGreater(len(manager.learned_patterns['successful_fixes']), 0)
        self.assertGreater(len(manager.learned_patterns['improvement_insights']), 0)
        
        # Test enhanced failure data
        enhanced_data = manager.get_enhanced_failure_data(3)
        self.assertIn('original_failures', enhanced_data)
        self.assertIn('learning_context', enhanced_data)
        self.assertIn('previous_attempt_analysis', enhanced_data)
        
        # Test learning summary
        summary = manager.get_learning_summary()
        self.assertEqual(summary['total_attempts'], 3)
        self.assertIn('successful_patterns', summary)
        self.assertIn('learning_progress', summary)
    
    def test_create_test_results_for_pr(self):
        """Test creating test results for PR from attempts."""
        # Create a mock AutoFix instance
        config = {
            'name': 'TestConfig',
            'file_path': 'test_file.py',
            'max_retries': 3,
            'create_pr': True,
            'pr_strategy': 'ALL_PASSING',
            'base_branch': 'main',
            'auto_fix': True,
            'tests': []
        }
        
        # Create mock test runner
        test_results_map = {
            'test_file.py': self.baseline_results
        }
        mock_runner = MockTestRunner(test_results_map)
        
        # Create AutoFix instance with mock runner
        autofix = AutoFix(config, config)
        autofix.test_runner = mock_runner
        
        # Create test attempts
        attempts = []
        
        attempt1 = FixAttempt(attempt_number=1)
        attempt1.status = FixStatus.FAILED
        attempt1.test_results = self.baseline_results
        attempts.append(attempt1)
        
        attempt2 = FixAttempt(attempt_number=2)
        attempt2.status = FixStatus.FAILED
        attempt2.test_results = self.improved_results
        attempts.append(attempt2)
        
        attempt3 = FixAttempt(attempt_number=3)
        attempt3.status = FixStatus.SUCCESS
        attempt3.test_results = self.successful_results
        attempts.append(attempt3)
        
        # Test creating test results for PR
        test_results_for_pr = autofix._create_test_results_for_pr(self.baseline_results, attempts)
        
        # Verify structure
        self.assertIn('agent_info', test_results_for_pr)
        self.assertIn('attempts', test_results_for_pr)
        self.assertIn('additional_summary', test_results_for_pr)
        
        # Verify agent info
        agent_info = test_results_for_pr['agent_info']
        self.assertEqual(agent_info['name'], 'Kaizen AutoFix Agent')
        self.assertEqual(agent_info['version'], '1.0.0')
        
        # Verify attempts
        attempts_data = test_results_for_pr['attempts']
        self.assertEqual(len(attempts_data), 4)  # 1 baseline + 3 attempts
        
        # Verify baseline attempt
        baseline_attempt = attempts_data[0]
        self.assertEqual(baseline_attempt['status'], 'failed')
        self.assertEqual(len(baseline_attempt['test_cases']), 3)
        
        # Verify fix attempts
        for i, attempt_data in enumerate(attempts_data[1:], 1):
            self.assertIn('status', attempt_data)
            self.assertIn('test_cases', attempt_data)
            self.assertGreater(len(attempt_data['test_cases']), 0)
    
    def test_pr_manager_test_results_table_generation(self):
        """Test PR manager test results table generation."""
        # Create PR manager
        config = {
            'github_token': 'dummy_token',
            'base_branch': 'main'
        }
        pr_manager = PRManager(config)
        
        # Create test results structure
        test_results: TestResults = {
            'agent_info': {
                'name': 'Test Agent',
                'version': '1.0.0',
                'description': 'Test agent for formatting'
            },
            'attempts': [
                # Baseline attempt
                {
                    'status': 'failed',
                    'test_cases': [
                        {
                            'name': 'test_basic_functionality',
                            'status': 'failed',
                            'input': 'test_input_1',
                            'expected_output': 'expected_1',
                            'actual_output': 'actual_1',
                            'evaluation': 'failed_evaluation_1',
                            'reason': 'Test failed'
                        },
                        {
                            'name': 'test_edge_cases',
                            'status': 'failed',
                            'input': 'test_input_2',
                            'expected_output': 'expected_2',
                            'actual_output': 'actual_2',
                            'evaluation': 'failed_evaluation_2',
                            'reason': 'Test failed'
                        },
                        {
                            'name': 'test_error_handling',
                            'status': 'error',
                            'input': 'test_input_3',
                            'expected_output': 'expected_3',
                            'actual_output': 'actual_3',
                            'evaluation': 'error_evaluation_3',
                            'reason': 'Test error'
                        }
                    ]
                },
                # First attempt
                {
                    'status': 'failed',
                    'test_cases': [
                        {
                            'name': 'test_basic_functionality',
                            'status': 'passed',
                            'input': 'test_input_1',
                            'expected_output': 'expected_1',
                            'actual_output': 'expected_1',
                            'evaluation': 'passed_evaluation_1'
                        },
                        {
                            'name': 'test_edge_cases',
                            'status': 'failed',
                            'input': 'test_input_2',
                            'expected_output': 'expected_2',
                            'actual_output': 'actual_2',
                            'evaluation': 'failed_evaluation_2',
                            'reason': 'Test failed'
                        },
                        {
                            'name': 'test_error_handling',
                            'status': 'error',
                            'input': 'test_input_3',
                            'expected_output': 'expected_3',
                            'actual_output': 'actual_3',
                            'evaluation': 'error_evaluation_3',
                            'reason': 'Test error'
                        }
                    ]
                },
                # Second attempt (successful)
                {
                    'status': 'passed',
                    'test_cases': [
                        {
                            'name': 'test_basic_functionality',
                            'status': 'passed',
                            'input': 'test_input_1',
                            'expected_output': 'expected_1',
                            'actual_output': 'expected_1',
                            'evaluation': 'passed_evaluation_1'
                        },
                        {
                            'name': 'test_edge_cases',
                            'status': 'passed',
                            'input': 'test_input_2',
                            'expected_output': 'expected_2',
                            'actual_output': 'expected_2',
                            'evaluation': 'passed_evaluation_2'
                        },
                        {
                            'name': 'test_error_handling',
                            'status': 'passed',
                            'input': 'test_input_3',
                            'expected_output': 'expected_3',
                            'actual_output': 'expected_3',
                            'evaluation': 'passed_evaluation_3'
                        }
                    ]
                }
            ],
            'additional_summary': 'Total attempts: 3 (1 baseline + 2 fixes)'
        }
        
        # Test test results table generation
        table = pr_manager._generate_test_results_table(test_results)
        
        # Verify table structure
        self.assertIn('Test Case', table)
        self.assertIn('Baseline', table)
        self.assertIn('Attempt 1', table)
        self.assertIn('Attempt 2', table)
        self.assertIn('Final Status', table)
        self.assertIn('Improvement', table)
        
        # Verify table content
        self.assertIn('test_basic_functionality', table)
        self.assertIn('test_edge_cases', table)
        self.assertIn('test_error_handling', table)
        
        # Verify improvement detection
        self.assertIn('Yes', table)  # Should show improvement for test_basic_functionality
        
        # Test fallback description generation
        changes = {
            'test_file.py': [
                {
                    'description': 'Fixed basic functionality',
                    'reason': 'Added proper error handling'
                }
            ]
        }
        
        description = pr_manager._generate_fallback_description(changes, test_results)
        
        # Verify description sections
        self.assertIn('Agent Summary', description)
        self.assertIn('Test Results Summary', description)
        self.assertIn('Detailed Results', description)
        self.assertIn('Code Changes', description)
        
        # Verify table is in description
        self.assertIn('| Test Case | Baseline | Attempt 1 | Attempt 2 | Final Status | Improvement |', description)
    
    def test_pr_manager_find_best_attempt(self):
        """Test finding the best attempt based on passed tests."""
        config = {
            'github_token': 'dummy_token',
            'base_branch': 'main'
        }
        pr_manager = PRManager(config)
        
        # Create attempts with different pass rates
        attempts = [
            # Baseline - 0 passed
            {
                'status': 'failed',
                'test_cases': [
                    {'name': 'test1', 'status': 'failed'},
                    {'name': 'test2', 'status': 'failed'},
                    {'name': 'test3', 'status': 'error'}
                ]
            },
            # Attempt 1 - 1 passed
            {
                'status': 'failed',
                'test_cases': [
                    {'name': 'test1', 'status': 'passed'},
                    {'name': 'test2', 'status': 'failed'},
                    {'name': 'test3', 'status': 'error'}
                ]
            },
            # Attempt 2 - 2 passed
            {
                'status': 'failed',
                'test_cases': [
                    {'name': 'test1', 'status': 'passed'},
                    {'name': 'test2', 'status': 'passed'},
                    {'name': 'test3', 'status': 'error'}
                ]
            },
            # Attempt 3 - 3 passed (best)
            {
                'status': 'passed',
                'test_cases': [
                    {'name': 'test1', 'status': 'passed'},
                    {'name': 'test2', 'status': 'passed'},
                    {'name': 'test3', 'status': 'passed'}
                ]
            }
        ]
        
        # Test finding best attempt
        best_index = pr_manager._find_best_attempt(attempts)
        self.assertEqual(best_index, 3)  # Should be the last attempt with 3 passed tests
        
        # Test with empty attempts
        best_index = pr_manager._find_best_attempt([])
        self.assertEqual(best_index, 0)
    
    def test_pr_manager_detailed_results_generation(self):
        """Test detailed results generation for baseline and best attempt."""
        config = {
            'github_token': 'dummy_token',
            'base_branch': 'main'
        }
        pr_manager = PRManager(config)
        
        # Create test results with detailed test cases
        test_results: TestResults = {
            'agent_info': {
                'name': 'Test Agent',
                'version': '1.0.0',
                'description': 'Test agent for detailed results'
            },
            'attempts': [
                # Baseline attempt
                {
                    'status': 'failed',
                    'test_cases': [
                        {
                            'name': 'test_basic_functionality',
                            'status': 'failed',
                            'input': 'test_input_1',
                            'expected_output': 'expected_1',
                            'actual_output': 'actual_1',
                            'evaluation': 'failed_evaluation_1',
                            'reason': 'Test failed'
                        }
                    ]
                },
                # Best attempt
                {
                    'status': 'passed',
                    'test_cases': [
                        {
                            'name': 'test_basic_functionality',
                            'status': 'passed',
                            'input': 'test_input_1',
                            'expected_output': 'expected_1',
                            'actual_output': 'expected_1',
                            'evaluation': 'passed_evaluation_1'
                        }
                    ]
                }
            ],
            'additional_summary': 'Test detailed results'
        }
        
        # Generate detailed results
        detailed_results = pr_manager._generate_detailed_results(test_results)
        
        # Verify baseline section
        baseline_section = '\n'.join(detailed_results)
        self.assertIn('Baseline (Before Fixes)', baseline_section)
        self.assertIn('Status: failed', baseline_section)
        self.assertIn('test_basic_functionality', baseline_section)
        self.assertIn('Input: test_input_1', baseline_section)
        self.assertIn('Expected Output: expected_1', baseline_section)
        self.assertIn('Actual Output: actual_1', baseline_section)
        self.assertIn('Result: failed', baseline_section)
        
        # Verify best attempt section
        self.assertIn('Best Attempt (Attempt 1)', baseline_section)
        self.assertIn('Status: passed', baseline_section)
        self.assertIn('Result: passed', baseline_section)
    
    def test_complete_result_flow(self):
        """Test the complete result flow from test results to PR description."""
        # Create mock AutoFix instance
        config = {
            'name': 'TestConfig',
            'file_path': 'test_file.py',
            'max_retries': 2,
            'create_pr': True,
            'pr_strategy': 'ANY_IMPROVEMENT',
            'base_branch': 'main',
            'auto_fix': True,
            'tests': []
        }
        
        # Create mock test runner
        test_results_map = {
            'test_file.py': self.baseline_results
        }
        mock_runner = MockTestRunner(test_results_map)
        
        # Create AutoFix instance with mock runner
        autofix = AutoFix(config, config)
        autofix.test_runner = mock_runner
        
        # Create PR manager
        pr_config = {
            'github_token': 'dummy_token',
            'base_branch': 'main'
        }
        autofix.pr_manager = PRManager(pr_config)
        
        # Create test attempts
        attempts = []
        
        attempt1 = FixAttempt(attempt_number=1)
        attempt1.status = FixStatus.FAILED
        attempt1.test_results = self.improved_results
        attempt1.changes = {'test_file.py': {'fixed_code': 'def test():\n    return True'}}
        attempts.append(attempt1)
        
        attempt2 = FixAttempt(attempt_number=2)
        attempt2.status = FixStatus.SUCCESS
        attempt2.test_results = self.successful_results
        attempt2.changes = {'test_file.py': {'fixed_code': 'def test():\n    return True\ndef main():\n    pass'}}
        attempts.append(attempt2)
        
        # Test creating test results for PR
        test_results_for_pr = autofix._create_test_results_for_pr(self.baseline_results, attempts)
        
        # Test PR description generation
        changes = {
            'test_file.py': [
                {
                    'description': 'Fixed test functionality',
                    'reason': 'Added proper implementation'
                }
            ]
        }
        
        description = autofix.pr_manager._generate_fallback_description(changes, test_results_for_pr)
        
        # Verify the complete flow works
        self.assertIn('Agent Summary', description)
        self.assertIn('Test Results Summary', description)
        self.assertIn('Detailed Results', description)
        self.assertIn('Code Changes', description)
        
        # Verify table formatting
        self.assertIn('| Test Case | Baseline | Attempt 1 | Attempt 2 | Final Status | Improvement |', description)
        self.assertIn('test_region_1', description)
        self.assertIn('test_region_2', description)
        self.assertIn('test_region_3', description)
        
        # Verify improvement detection
        self.assertIn('Yes', description)  # Should show improvements
        
        print("\n" + "="*80)
        print("COMPLETE PR DESCRIPTION GENERATED:")
        print("="*80)
        print(description)
        print("="*80)


def run_tests():
    """Run all tests and display results."""
    print("Starting Result Formatting Tests...")
    print("="*80)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestResultFormatting)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY:")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    print("="*80)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 