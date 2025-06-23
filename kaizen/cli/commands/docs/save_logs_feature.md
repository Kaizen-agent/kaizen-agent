# Save Logs Feature

The `--save-logs` option allows you to save detailed test execution logs in JSON format for later analysis and debugging.

## Overview

When you run tests with the `--save-logs` flag, the system creates comprehensive log files containing:

- **Test metadata**: Configuration, timing, and execution details
- **Individual test results**: Inputs, outputs, and evaluation scores for each test case
- **Auto-fix attempts**: Complete history of fix attempts and their outcomes
- **Error details**: Stack traces and error messages
- **Execution timing**: Performance metrics and timing information

## Usage

```bash
# Run tests with detailed logging
kaizen test --config test_config.yaml --save-logs

# Combine with other options
kaizen test --config test_config.yaml --auto-fix --create-pr --save-logs
```

## Output Files

When `--save-logs` is enabled, two files are created in the `test-logs/` directory:

### 1. Detailed Logs File
**Filename**: `{test_name}_{timestamp}_detailed_logs.json`

Contains complete test execution data:
- Test metadata and configuration
- Individual test case results with inputs/outputs
- LLM evaluation results and scores
- Auto-fix attempts and their outcomes
- Error details and stack traces
- Execution timing information

### 2. Summary File
**Filename**: `{test_name}_{timestamp}_summary.json`

Quick reference with key metrics:
- Test name and status
- Execution timestamps
- Error messages
- Overall status summary
- Reference to detailed logs file

## Example Output

```json
{
  "metadata": {
    "test_name": "example_test",
    "file_path": "example_agent.py",
    "config_path": "test_config.yaml",
    "start_time": "2024-01-15T10:30:00",
    "end_time": "2024-01-15T10:30:45",
    "status": "failed",
    "timestamp": "2024-01-15T10:30:45",
    "config": {
      "auto_fix": true,
      "create_pr": false,
      "max_retries": 2,
      "base_branch": "main",
      "pr_strategy": "ANY_IMPROVEMENT"
    }
  },
  "test_results": {
    "overall_status": {
      "status": "failed",
      "summary": {
        "total_tests": 2,
        "passed_tests": 1,
        "failed_tests": 1
      }
    },
    "test_region_1": {
      "test_cases": [
        {
          "name": "test_basic_functionality",
          "status": "passed",
          "input": "hello world",
          "expected_output": "Hello World!",
          "output": "Hello World!",
          "evaluation": {"score": 0.95, "reason": "Output matches expected"}
        }
      ]
    }
  },
  "unified_test_results": {
    "test_cases": [
      {
        "name": "test_basic_functionality",
        "status": "passed",
        "region": "test_region_1",
        "input": "hello world",
        "expected_output": "Hello World!",
        "actual_output": "Hello World!",
        "evaluation": {"score": 0.95},
        "execution_time": 0.5,
        "timestamp": "2024-01-15T10:30:00"
      }
    ]
  },
  "auto_fix_attempts": [
    {
      "attempt": 1,
      "status": "partial_success",
      "fixed_tests": ["test_edge_case"],
      "results": {...}
    }
  ]
}
```

## Benefits

1. **Debugging**: Complete visibility into test execution for troubleshooting
2. **Analysis**: Detailed metrics for performance optimization
3. **Audit Trail**: Full history of test runs and auto-fix attempts
4. **Reproducibility**: All inputs and outputs preserved for later analysis
5. **Integration**: JSON format allows easy integration with other tools

## File Size Considerations

- Detailed logs can be large (several MB) for complex test suites
- Summary files are typically small (< 1KB) for quick reference
- Files are automatically timestamped to avoid conflicts
- Consider cleanup strategies for long-running test environments

## Integration with CI/CD

The JSON logs can be easily integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run tests with logging
  run: kaizen test --config test_config.yaml --save-logs

- name: Upload test logs
  uses: actions/upload-artifact@v2
  with:
    name: test-logs
    path: test-logs/
```

## Best Practices

1. **Use for debugging**: Enable `--save-logs` when investigating test failures
2. **Archive important runs**: Keep logs for significant test executions
3. **Monitor file sizes**: Large log files may indicate verbose output
4. **Clean up regularly**: Remove old logs to save disk space
5. **Share selectively**: Detailed logs may contain sensitive information 