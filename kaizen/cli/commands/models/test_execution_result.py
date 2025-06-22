"""Unified test execution result model.

This module provides a comprehensive class to store all test execution results
in a unified format, making it easier to work with test results throughout
the codebase.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

class TestStatus(Enum):
    """Test status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"

@dataclass
class TestCaseResult:
    """Result of a single test case execution."""
    
    # Basic information
    name: str
    status: TestStatus
    region: str
    
    # Input and output
    input: Optional[Any] = None
    expected_output: Optional[Any] = None
    actual_output: Optional[Any] = None
    
    # Error information
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    
    # Evaluation results
    evaluation: Optional[Dict[str, Any]] = None
    evaluation_score: Optional[float] = None
    
    # Metadata
    execution_time: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_failed(self) -> bool:
        """Check if the test case failed."""
        return self.status in [TestStatus.FAILED, TestStatus.ERROR]
    
    def is_passed(self) -> bool:
        """Check if the test case passed."""
        return self.status == TestStatus.PASSED
    
    def get_error_summary(self) -> str:
        """Get a summary of the error if any."""
        if self.error_message:
            return self.error_message
        elif self.error_details:
            return self.error_details
        return "No error details available"

@dataclass
class TestExecutionSummary:
    """Summary statistics for test execution."""
    
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    skipped_tests: int = 0
    
    # Timing information
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_execution_time: Optional[float] = None
    
    # Region breakdown
    regions: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def update_from_test_cases(self, test_cases: List[TestCaseResult]) -> None:
        """Update summary from test cases."""
        self.total_tests = len(test_cases)
        self.passed_tests = sum(1 for tc in test_cases if tc.is_passed())
        self.failed_tests = sum(1 for tc in test_cases if tc.status == TestStatus.FAILED)
        self.error_tests = sum(1 for tc in test_cases if tc.status == TestStatus.ERROR)
        self.skipped_tests = sum(1 for tc in test_cases if tc.status == TestStatus.SKIPPED)
        
        # Update region breakdown
        self.regions.clear()
        for tc in test_cases:
            if tc.region not in self.regions:
                self.regions[tc.region] = {
                    'total': 0, 'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0
                }
            
            self.regions[tc.region]['total'] += 1
            if tc.is_passed():
                self.regions[tc.region]['passed'] += 1
            elif tc.status == TestStatus.FAILED:
                self.regions[tc.region]['failed'] += 1
            elif tc.status == TestStatus.ERROR:
                self.regions[tc.region]['error'] += 1
            elif tc.status == TestStatus.SKIPPED:
                self.regions[tc.region]['skipped'] += 1
    
    def is_successful(self) -> bool:
        """Check if all tests passed."""
        return self.failed_tests == 0 and self.error_tests == 0 and self.total_tests > 0
    
    def get_success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'error_tests': self.error_tests,
            'skipped_tests': self.skipped_tests,
            'success_rate': self.get_success_rate(),
            'is_successful': self.is_successful(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_execution_time': self.total_execution_time,
            'regions': self.regions
        }

@dataclass
class TestExecutionResult:
    """Unified test execution result containing all test data."""
    
    # Basic information
    name: str
    file_path: Path
    config_path: Path
    
    # Test cases and results
    test_cases: List[TestCaseResult] = field(default_factory=list)
    summary: TestExecutionSummary = field(default_factory=TestExecutionSummary)
    
    # Overall status
    status: TestStatus = TestStatus.PENDING
    
    # Error information
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Legacy format compatibility (for backward compatibility)
    raw_results: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize the result after creation."""
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.summary.start_time is None:
            self.summary.start_time = self.start_time
        if self.test_cases:
            self._update_summary()
    
    def add_test_case(self, test_case: TestCaseResult) -> None:
        """Add a test case to the result."""
        self.test_cases.append(test_case)
        self._update_summary()
    
    def add_test_cases(self, test_cases: List[TestCaseResult]) -> None:
        """Add multiple test cases to the result."""
        self.test_cases.extend(test_cases)
        self._update_summary()
    
    def _update_summary(self) -> None:
        """Update the summary based on current test cases."""
        self.summary.update_from_test_cases(self.test_cases)
        
        # Update overall status
        if self.summary.is_successful():
            self.status = TestStatus.PASSED
        elif self.summary.error_tests > 0:
            self.status = TestStatus.ERROR
        elif self.summary.failed_tests > 0:
            self.status = TestStatus.FAILED
        
        # Update timing
        if self.test_cases:
            timestamps = [tc.timestamp for tc in self.test_cases if tc.timestamp]
            if timestamps:
                self.start_time = min(timestamps)
                self.end_time = max(timestamps)
                if self.start_time and self.end_time:
                    self.summary.total_execution_time = (self.end_time - self.start_time).total_seconds()
    
    def get_failed_tests(self) -> List[TestCaseResult]:
        """Get all failed test cases."""
        return [tc for tc in self.test_cases if tc.is_failed()]
    
    def get_passed_tests(self) -> List[TestCaseResult]:
        """Get all passed test cases."""
        return [tc for tc in self.test_cases if tc.is_passed()]
    
    def get_tests_by_region(self, region: str) -> List[TestCaseResult]:
        """Get all test cases for a specific region."""
        return [tc for tc in self.test_cases if tc.region == region]
    
    def get_tests_by_status(self, status: TestStatus) -> List[TestCaseResult]:
        """Get all test cases with a specific status."""
        return [tc for tc in self.test_cases if tc.status == status]
    
    def is_successful(self) -> bool:
        """Check if all tests passed."""
        return self.summary.is_successful()
    
    def get_failure_count(self) -> int:
        """Get the total number of failed tests."""
        return self.summary.failed_tests + self.summary.error_tests
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to the legacy format for backward compatibility."""
        if self.raw_results:
            return self.raw_results
        
        # Create legacy format
        result = {
            'overall_status': {
                'status': self.status.value,
                'summary': self.summary.to_dict()
            }
        }
        
        # Group test cases by region
        regions = {}
        for tc in self.test_cases:
            if tc.region not in regions:
                regions[tc.region] = {'test_cases': []}
            
            test_case_dict = {
                'name': tc.name,
                'status': tc.status.value,
                'input': tc.input,
                'expected_output': tc.expected_output,
                'output': tc.actual_output,
                'evaluation': tc.evaluation,
                'error': tc.error_message
            }
            regions[tc.region]['test_cases'].append(test_case_dict)
        
        result.update(regions)
        return result
    
    @classmethod
    def from_legacy_format(cls, name: str, file_path: Path, config_path: Path, 
                          legacy_results: Dict[str, Any]) -> 'TestExecutionResult':
        """Create from legacy format for backward compatibility."""
        result = cls(
            name=name,
            file_path=file_path,
            config_path=config_path,
            raw_results=legacy_results
        )
        
        # Parse overall status
        overall_status = legacy_results.get('overall_status', {})
        status_str = overall_status.get('status', 'unknown')
        try:
            result.status = TestStatus(status_str)
        except ValueError:
            result.status = TestStatus.ERROR
        
        # Parse test cases
        test_cases = []
        for region_name, region_data in legacy_results.items():
            if region_name == 'overall_status':
                continue
            
            if isinstance(region_data, dict):
                region_test_cases = region_data.get('test_cases', [])
                for tc_data in region_test_cases:
                    if isinstance(tc_data, dict):
                        try:
                            status = TestStatus(tc_data.get('status', 'unknown'))
                        except ValueError:
                            status = TestStatus.ERROR
                        
                        test_case = TestCaseResult(
                            name=tc_data.get('name', 'Unknown'),
                            status=status,
                            region=region_name,
                            input=tc_data.get('input'),
                            expected_output=tc_data.get('expected_output'),
                            actual_output=tc_data.get('output'),
                            error_message=tc_data.get('error'),
                            evaluation=tc_data.get('evaluation')
                        )
                        test_cases.append(test_case)
        
        result.add_test_cases(test_cases)
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'name': self.name,
            'file_path': str(self.file_path),
            'config_path': str(self.config_path),
            'status': self.status.value,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'summary': self.summary.to_dict(),
            'test_cases': [
                {
                    'name': tc.name,
                    'status': tc.status.value,
                    'region': tc.region,
                    'input': tc.input,
                    'expected_output': tc.expected_output,
                    'actual_output': tc.actual_output,
                    'error_message': tc.error_message,
                    'error_details': tc.error_details,
                    'evaluation': tc.evaluation,
                    'evaluation_score': tc.evaluation_score,
                    'execution_time': tc.execution_time,
                    'timestamp': tc.timestamp.isoformat() if tc.timestamp else None,
                    'metadata': tc.metadata
                }
                for tc in self.test_cases
            ],
            'metadata': self.metadata
        }

@dataclass
class TestExecutionHistory:
    """Container for storing all test execution results from multiple runs.
    This class provides a unified way to store and analyze test results from
    baseline tests, fix attempts, and final results. It maintains the complete
    history of test executions and provides methods for analysis and comparison.
    """
    baseline_result: Optional[TestExecutionResult] = None
    fix_attempts: List[TestExecutionResult] = None
    final_result: Optional[TestExecutionResult] = None

    def __post_init__(self):
        if self.fix_attempts is None:
            self.fix_attempts = []

    def add_baseline_result(self, result: TestExecutionResult) -> None:
        self.baseline_result = result

    def add_fix_attempt_result(self, result: TestExecutionResult) -> None:
        self.fix_attempts.append(result)

    def set_final_result(self, result: TestExecutionResult) -> None:
        self.final_result = result

    def get_latest_result(self) -> Optional[TestExecutionResult]:
        if self.final_result:
            return self.final_result
        elif self.fix_attempts:
            return self.fix_attempts[-1]
        else:
            return self.baseline_result

    def get_all_results(self) -> List[TestExecutionResult]:
        results = []
        if self.baseline_result:
            results.append(self.baseline_result)
        results.extend(self.fix_attempts)
        if self.final_result:
            results.append(self.final_result)
        return results

    def get_improvement_summary(self) -> Dict[str, Any]:
        if not self.baseline_result:
            return {"error": "No baseline result available"}
        latest = self.get_latest_result()
        if not latest:
            return {"error": "No test results available"}
        baseline_failed = len(self.baseline_result.get_failed_tests())
        current_failed = len(latest.get_failed_tests())
        return {
            'baseline_failed': baseline_failed,
            'current_failed': current_failed,
            'improvement': baseline_failed - current_failed,
            'has_improvement': current_failed < baseline_failed,
            'all_passed': latest.is_successful(),
            'total_attempts': len(self.fix_attempts),
            'baseline_status': getattr(self.baseline_result, 'status', None).value if self.baseline_result else None,
            'current_status': getattr(latest, 'status', None).value if latest else None
        }

    def get_failed_tests_progression(self) -> List[Dict[str, Any]]:
        progression = []
        if self.baseline_result:
            baseline_failed = self.baseline_result.get_failed_tests()
            progression.append({
                'run_type': 'baseline',
                'failed_count': len(baseline_failed),
                'failed_tests': [tc.name for tc in baseline_failed]
            })
        for i, attempt in enumerate(self.fix_attempts):
            attempt_failed = attempt.get_failed_tests()
            progression.append({
                'run_type': f'fix_attempt_{i+1}',
                'failed_count': len(attempt_failed),
                'failed_tests': [tc.name for tc in attempt_failed]
            })
        if self.final_result:
            final_failed = self.final_result.get_failed_tests()
            progression.append({
                'run_type': 'final',
                'failed_count': len(final_failed),
                'failed_tests': [tc.name for tc in final_failed]
            })
        return progression

    def to_legacy_format(self) -> Dict[str, Any]:
        return {
            'baseline': self.baseline_result.to_legacy_format() if self.baseline_result else None,
            'fix_attempts': [attempt.to_legacy_format() for attempt in self.fix_attempts],
            'final': self.final_result.to_legacy_format() if self.final_result else None,
            'improvement_summary': self.get_improvement_summary()
        }

    def __len__(self) -> int:
        count = 0
        if self.baseline_result:
            count += 1
        count += len(self.fix_attempts)
        if self.final_result:
            count += 1
        return count

    def __repr__(self) -> str:
        baseline_status = getattr(self.baseline_result, 'status', None).value if self.baseline_result else "None"
        latest_status = getattr(self.get_latest_result(), 'status', None).value if self.get_latest_result() else "None"
        return f"TestExecutionHistory(baseline={baseline_status}, attempts={len(self.fix_attempts)}, latest={latest_status})" 