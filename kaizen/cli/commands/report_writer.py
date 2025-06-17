"""Test report writing functionality."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .types import TestResultFormatter, ReportGenerationError
from .models import TestResult

class TestReportWriter:
    """Handles writing test reports to files with detailed formatting and error handling."""

    def __init__(self, result: TestResult, formatter: TestResultFormatter, logger: logging.Logger):
        """Initialize the report writer.
        
        Args:
            result: The test result to write
            formatter: Formatter for test results
            logger: Logger instance for reporting
        """
        self.result = result
        self.formatter = formatter
        self.logger = logger

    def write_report(self, file_path: Path) -> None:
        """Write test report to file.
        
        Args:
            file_path: Path where the report should be written
            
        Raises:
            ReportGenerationError: If report writing fails
        """
        try:
            self.logger.info(f"Writing test report to {file_path}")
            with open(file_path, 'w') as f:
                self._write_report_header(f)
                self._write_configuration_details(f)
                self._write_overall_status(f)
                self._write_detailed_results(f)
                self._write_failed_tests(f)
                if self.result.test_attempts:
                    self._write_autofix_attempts(f)
            self.logger.info("Test report written successfully")
        except Exception as e:
            self.logger.error(f"Failed to write report: {str(e)}")
            raise ReportGenerationError(f"Failed to write report: {str(e)}")

    def _write_report_header(self, f) -> None:
        """Write the report header section."""
        f.write("Test Results Report\n")
        f.write("=" * 50 + "\n\n")

    def _write_configuration_details(self, f) -> None:
        """Write the test configuration details section."""
        f.write("Test Configuration:\n")
        f.write(f"- Name: {self.result.name}\n")
        f.write(f"- File: {self.result.file_path}\n")
        f.write(f"- Config: {self.result.config_path}\n\n")

    def _write_overall_status(self, f) -> None:
        """Write the overall test status section."""
        try:
            overall_status = self.result.results.get('overall_status', 'unknown')
            status = overall_status.get('status', 'unknown') if isinstance(overall_status, dict) else overall_status
            formatted_status = self.formatter.format_status(status)
            f.write(f"Overall Status: {formatted_status}\n\n")
        except Exception as e:
            self.logger.warning(f"Error formatting overall status: {str(e)}")
            f.write("Overall Status: ❓ UNKNOWN\n\n")

    def _write_detailed_results(self, f) -> None:
        """Write the detailed test results section."""
        f.write("Detailed Test Results:\n")
        f.write("=" * 50 + "\n\n")
        
        for region, result in self.result.results.items():
            if region == 'overall_status':
                continue
                
            f.write(f"Region: {region}\n")
            f.write("-" * 30 + "\n")
            
            test_cases = result.get('test_cases', []) if isinstance(result, dict) else []
            for test_case in test_cases:
                self._write_test_case(f, test_case)

    def _write_test_case(self, f, test_case: Dict[str, Any]) -> None:
        """Write a single test case result.
        
        Args:
            f: File handle to write to
            test_case: Test case data to write
        """
        if not isinstance(test_case, dict):
            self.logger.warning(f"Invalid test case format: {test_case}")
            f.write(f"Invalid test case format: {test_case}\n")
            return

        f.write(f"\nTest: {test_case.get('name', 'Unknown')}\n")
        f.write(f"Status: {test_case.get('status', 'unknown')}\n")
        if test_case.get('details'):
            f.write(f"Details: {test_case.get('details')}\n")
        if test_case.get('output'):
            f.write(f"Output:\n{test_case.get('output')}\n")
        if test_case.get('evaluation'):
            f.write(f"Evaluation:\n{json.dumps(test_case.get('evaluation'), indent=2)}\n")
        f.write("-" * 30 + "\n")

    def _write_failed_tests(self, f) -> None:
        """Write the failed tests analysis section."""
        if not self.result.failed_tests:
            return
            
        f.write("\nFailed Tests Analysis:\n")
        f.write("=" * 50 + "\n\n")
        for test in self.result.failed_tests:
            if not isinstance(test, dict):
                self.logger.warning(f"Invalid failed test format: {test}")
                f.write(f"Invalid failed test format: {test}\n")
                continue

            f.write(f"Test: {test.get('test_name', 'Unknown')} ({test.get('region', 'Unknown')})\n")
            f.write(f"Error: {test.get('error_message', 'Unknown error')}\n")
            if test.get('output'):
                f.write(f"Output:\n{test.get('output')}\n")
            f.write("-" * 30 + "\n")

    def _write_autofix_attempts(self, f) -> None:
        """Write the auto-fix attempts section."""
        f.write("\nAuto-fix Attempts:\n")
        f.write("=" * 50 + "\n\n")
        for attempt in self.result.test_attempts:
            if not isinstance(attempt, dict):
                self.logger.warning(f"Invalid attempt format: {attempt}")
                f.write(f"Invalid attempt format: {attempt}\n")
                continue
            self._write_attempt_details(f, attempt)

    def _write_attempt_details(self, f, attempt: Dict[str, Any]) -> None:
        """Write details of a single auto-fix attempt.
        
        Args:
            f: File handle to write to
            attempt: Attempt data to write
        """
        f.write(f"Attempt {attempt.get('attempt', 'Unknown')}:\n")
        f.write("-" * 30 + "\n")
        
        fixed_tests = self._get_fixed_tests(attempt)
        if fixed_tests:
            f.write("Fixed Tests:\n")
            for fixed in fixed_tests:
                f.write(f"- {fixed.get('test_name', 'Unknown')} ({fixed.get('region', 'Unknown')})\n")
        else:
            f.write("No tests were fixed in this attempt\n")
        
        try:
            results = attempt.get('results', {})
            overall_status = results.get('overall_status', 'unknown')
            status = overall_status.get('status', 'unknown') if isinstance(overall_status, dict) else overall_status
            formatted_status = self.formatter.format_status(status)
            f.write(f"\nOverall Status: {formatted_status}\n")
        except Exception as e:
            self.logger.warning(f"Error formatting attempt status: {str(e)}")
            f.write("\nOverall Status: UNKNOWN\n")
        
        if isinstance(overall_status, dict) and 'error' in overall_status:
            f.write(f"Error: {overall_status['error']}\n")
        
        f.write("\n")

    def _get_fixed_tests(self, attempt: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of tests that were fixed in an attempt.
        
        Args:
            attempt: Attempt data to analyze
            
        Returns:
            List of fixed test information
        """
        fixed_tests = []
        results = attempt.get('results', {})
        
        for region, result in results.items():
            if region == 'overall_status':
                continue
            if not isinstance(result, dict):
                continue
                
            test_cases = result.get('test_cases', [])
            for test_case in test_cases:
                if isinstance(test_case, dict) and test_case.get('status') == 'passed':
                    fixed_tests.append({
                        'region': region,
                        'test_name': test_case.get('name', 'Unknown')
                    })
        return fixed_tests 