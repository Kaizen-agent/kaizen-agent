# Enhanced Test Logging Guide

## Overview

The Kaizen CLI now provides enhanced logging capabilities that save comprehensive test results including inputs, outputs, and evaluations for each test case. This makes it much easier to analyze test results after execution and understand what outputs were generated.

## Key Features

### 1. **Comprehensive Test Case Data**
When you run tests with `--save-logs`, the system saves:
- **Inputs**: The exact input data provided to each test case
- **Expected Outputs**: What the test expected to receive
- **Actual Outputs**: What the system actually generated
- **Evaluations**: LLM evaluation results and scores
- **Error Messages**: Detailed error information if tests fail
- **Metadata**: Additional context about test execution

### 2. **Two Types of Log Files**
- **Detailed Logs**: Complete test data in `{test_name}_{timestamp}_detailed_logs.json`
- **Summary Logs**: Quick reference in `{test_name}_{timestamp}_summary.json`

### 3. **Easy Analysis Tools**
- **CLI Command**: `kaizen analyze-logs` for quick analysis
- **Rich Display**: Color-coded output with tables and panels
- **Flexible Detail Levels**: Summary-only or detailed views

## Usage

### Running Tests with Enhanced Logging

```bash
# Run tests and save detailed logs
kaizen test-all --config test_config.yaml --save-logs

# Run with auto-fix and save logs
kaizen test-all --config test_config.yaml --auto-fix --save-logs

# Run with verbose output and save logs
kaizen test-all --config test_config.yaml --save-logs --verbose
```

### Analyzing Saved Logs

```bash
# Quick summary of test results
kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json

# Detailed view with all inputs, outputs, and evaluations
kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json --details

# Summary only (no test case details)
kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json --summary-only
```

## Log File Structure

### Detailed Logs (`*_detailed_logs.json`)

```json
{
  "metadata": {
    "test_name": "My Test Suite",
    "file_path": "/path/to/test_file.py",
    "config_path": "/path/to/config.yaml",
    "start_time": "2024-12-01T12:00:00",
    "end_time": "2024-12-01T12:01:30",
    "status": "failed",
    "config": {
      "auto_fix": true,
      "create_pr": false,
      "max_retries": 2
    }
  },
  "unified_test_results": {
    "test_summary": {
      "total_test_cases": 5,
      "passed_test_cases": 3,
      "failed_test_cases": 2,
      "error_test_cases": 0,
      "regions": ["function_1", "function_2"]
    },
    "test_cases_detailed": [
      {
        "name": "test_basic_functionality",
        "status": "passed",
        "region": "function_1",
        "input": "test input data",
        "expected_output": "expected result",
        "actual_output": "expected result",
        "evaluation": {
          "score": 0.95,
          "reason": "Output matches expected exactly"
        },
        "summary": {
          "passed": true,
          "has_evaluation": true,
          "input_type": "str",
          "output_type": "str"
        }
      }
    ]
  },
  "auto_fix_attempts": [
    {
      "status": "failed",
      "test_cases": [...]
    }
  ]
}
```

### Summary Logs (`*_summary.json`)

```json
{
  "test_name": "My Test Suite",
  "status": "failed",
  "test_cases_summary": {
    "total": 5,
    "passed": 3,
    "failed": 2,
    "error": 0,
    "regions": ["function_1", "function_2"]
  },
  "failed_test_cases": [
    {
      "name": "test_edge_case",
      "region": "function_2",
      "status": "failed",
      "input": "edge case input",
      "expected_output": "expected",
      "actual_output": "actual",
      "error_message": "Test failed: output does not match",
      "evaluation_score": 0.3
    }
  ]
}
```

## Analysis Examples

### 1. **Quick Overview**
```bash
kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json
```

**Output:**
```
Test Log Analysis: my_test_20241201_120000_detailed_logs.json
================================================================================

Test Metadata:
┌─────────────┬─────────────────────────────────────┐
│ Property    │ Value                               │
├─────────────┼─────────────────────────────────────┤
│ Test Name   │ My Test Suite                       │
│ Status      │ failed                              │
│ Total Tests │ 5                                   │
│ Passed      │ 3                                   │
│ Failed      │ 2                                   │
└─────────────┴─────────────────────────────────────┘
```

### 2. **Detailed Analysis**
```bash
kaizen analyze-logs test-logs/my_test_20241201_120000_detailed_logs.json --details
```

**Output:**
```
Test Case 1: test_basic_functionality [green]passed[/green]
┌─────────────────────────────────────────────────────────────────────────────┐
│ Region: function_1                                                          │
│                                                                             │
│ Input:                                                                      │
│ "test input data"                                                           │
│                                                                             │
│ Expected Output:                                                            │
│ "expected result"                                                           │
│                                                                             │
│ Actual Output:                                                              │
│ "expected result"                                                           │
│                                                                             │
│ Evaluation:                                                                 │
│ {                                                                           │
│   "score": 0.95,                                                            │
│   "reason": "Output matches expected exactly"                               │
│ }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Best Practices

### 1. **When to Use Enhanced Logging**
- **Debugging**: When tests fail and you need to understand why
- **Quality Assurance**: To verify that outputs meet expectations
- **Performance Analysis**: To track how outputs change over time
- **Documentation**: To create examples of system behavior

### 2. **File Management**
- Log files can be large, so consider cleanup strategies
- Use meaningful test names to make logs easier to find
- Keep logs for important test runs and delete old ones

### 3. **Analysis Workflow**
1. Run tests with `--save-logs`
2. Use `kaizen analyze-logs` for quick overview
3. Use `--details` flag for deep analysis
4. Check summary file for failed test cases
5. Open JSON directly for programmatic analysis

## Troubleshooting

### Common Issues

**1. Log files not created**
- Ensure you're using `--save-logs` flag
- Check that the test-logs directory is writable
- Verify that unified test results are available

**2. Large log files**
- Consider using `--summary-only` for quick analysis
- Log files include all test data, so they can be large
- Use the summary file for quick reference

**3. Missing test case details**
- Ensure you're using the latest version of Kaizen
- Check that tests are using the unified test result format
- Verify that the test runner is properly configured

### Getting Help

If you encounter issues with enhanced logging:

1. Check the console output for error messages
2. Verify that the log files were created in the `test-logs/` directory
3. Try running with `--verbose` to see more details
4. Check the summary file for basic information

## Integration with Other Tools

The JSON log files can be easily integrated with:
- **CI/CD pipelines**: Parse results programmatically
- **Monitoring systems**: Track test performance over time
- **Reporting tools**: Generate custom reports
- **Data analysis**: Use pandas or other tools to analyze trends

The structured format makes it easy to extract specific information and create custom analysis tools. 