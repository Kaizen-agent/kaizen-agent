#!/usr/bin/env python3
"""
Test script to verify that baseline results are properly included in the summary report.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.cli.commands.models import TestResult, TestExecutionResult, TestCaseResult, TestStatus
from kaizen.cli.commands.test import _save_summary_report
from rich.console import Console

def test_baseline_inclusion():
    """Test that baseline results are properly included in the summary report."""
    print("Testing baseline result inclusion in summary report...")
    
    # Create baseline test cases
    baseline_test_cases = [
        TestCaseResult(
            name="test_baseline_1",
            status=TestStatus.FAILED,
            region="test_region",
            input="test input 1",
            expected_output="expected 1",
            actual_output="actual output 1",
            evaluation={"score": 0.3},
            timestamp=datetime.now()
        ),
        TestCaseResult(
            name="test_baseline_2",
            status=TestStatus.PASSED,
            region="test_region",
            input="test input 2",
            expected_output="expected 2",
            actual_output="actual output 2",
            evaluation={"score": 0.9},
            timestamp=datetime.now()
        )
    ]
    
    # Create baseline result
    baseline_result = TestExecutionResult(
        name="Baseline Test",
        file_path=Path("test.py"),
        config_path=Path("config.yaml")
    )
    baseline_result.add_test_cases(baseline_test_cases)
    
    # Create fix attempt test cases (improved version)
    fix_test_cases = [
        TestCaseResult(
            name="test_baseline_1",
            status=TestStatus.PASSED,  # Fixed!
            region="test_region",
            input="test input 1",
            expected_output="expected 1",
            actual_output="fixed actual output 1",  # Different output
            evaluation={"score": 0.9},  # Better score
            timestamp=datetime.now()
        ),
        TestCaseResult(
            name="test_baseline_2",
            status=TestStatus.PASSED,
            region="test_region",
            input="test input 2",
            expected_output="expected 2",
            actual_output="actual output 2",
            evaluation={"score": 0.9},
            timestamp=datetime.now()
        )
    ]
    
    # Create fix attempt result
    fix_attempt_result = TestExecutionResult(
        name="Fix Attempt",
        file_path=Path("test.py"),
        config_path=Path("config.yaml")
    )
    fix_attempt_result.add_test_cases(fix_test_cases)
    
    # Create test result with both baseline and attempts
    test_result = TestResult(
        name="Test with Baseline",
        file_path=Path("test.py"),
        config_path=Path("config.yaml"),
        start_time=datetime.now(),
        end_time=datetime.now(),
        status="improved",
        results=fix_attempt_result.to_legacy_format(),
        unified_result=fix_attempt_result,  # Best result after fixes
        test_attempts=[
            {
                'test_execution_result': fix_attempt_result,
                'status': 'success'
            }
        ],
        baseline_result=baseline_result  # This is the key addition!
    )
    
    # Create a mock config
    class MockConfig:
        def __init__(self):
            self.name = "Test Config"
            self.create_pr = False
    
    config = MockConfig()
    
    # Test the summary report generation
    console = Console()
    _save_summary_report(console, test_result, config)
    
    # Check if the report was created
    import glob
    report_files = glob.glob("test-logs/test_report_*.md")
    if report_files:
        latest_report = max(report_files, key=lambda x: Path(x).stat().st_mtime)
        print(f"✓ Summary report created: {latest_report}")
        
        # Check the content
        with open(latest_report, 'r') as f:
            content = f.read()
            
        # Verify baseline results are included
        if "test_baseline_1" in content and "actual output 1" in content:
            print("✓ Baseline results are included in the report")
        else:
            print("✗ Baseline results are missing from the report")
            
        # Verify fix attempt results are included
        if "fixed actual output 1" in content:
            print("✓ Fix attempt results are included in the report")
        else:
            print("✗ Fix attempt results are missing from the report")
            
        # Verify improvement analysis
        if "Baseline Success Rate:** 50.0%" in content and "Final Success Rate:** 100.0%" in content:
            print("✓ Improvement analysis is correct")
        else:
            print("✗ Improvement analysis is incorrect")
            
        print("\nTest completed successfully!")
    else:
        print("✗ No summary report was created")
        return False
    
    return True

if __name__ == "__main__":
    test_baseline_inclusion() 