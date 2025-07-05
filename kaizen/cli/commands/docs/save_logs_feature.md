# Save Logs Feature

The `--save-logs` option allows you to save detailed test execution logs in JSON format and summary reports in Markdown format for later analysis and debugging.

## Overview

When you run tests with the `--save-logs` flag, the system creates comprehensive log files containing:

- **Test metadata**: Configuration, timing, and execution details
- **Individual test results**: Inputs, outputs, and evaluation scores for each test case
- **Auto-fix attempts**: Complete history of fix attempts and their outcomes
- **Error details**: Stack traces and error messages
- **Execution timing**: Performance metrics and timing information
- **Summary reports**: Detailed test summaries in Markdown format (same as PR descriptions)

## Usage

```bash
# Run tests with detailed logging
kaizen test --config test_config.yaml --save-logs

# Combine with other options
kaizen test --config test_config.yaml --auto-fix --create-pr --save-logs

# Save logs without GitHub integration (no GitHub token required)
kaizen test --config test_config.yaml --auto-fix --save-logs
```

## Output Files

When `--save-logs` is enabled, three files are created in the `test-logs/` directory:

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

### 3. Summary Report File
**Filename**: `test_report_{timestamp}.md`

Detailed test summary in Markdown format (same content as PR descriptions):
- Comprehensive test summary with agent information
- Test results table showing all attempts
- Detailed analysis of improvements and regressions
- Executive summary with success rates and improvements
- Improvement analysis with specific test case details
- Can be viewed in any Markdown viewer or text editor
- **Works without GitHub token** - no GitHub integration required

## GitHub Token Requirements

### Summary Reports (.md files)
- **No GitHub token required** - Summary reports are generated locally
- Works in any environment without GitHub access
- Perfect for local development and CI/CD pipelines without GitHub integration

### JSON Logs
- **No GitHub token required** - All logging is done locally
- Works independently of GitHub functionality

### PR Creation
- **GitHub token required** - Only needed when using `--create-pr` flag
- Summary reports are still generated even if PR creation fails due to missing token

## Example Output

### JSON Logs
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

### Markdown Summary Report
```markdown
## Agent Summary

Agent: Kaizen AutoFix Agent
Version: 1.0.0
Description: Automated code fixing agent using LLM-based analysis

## Executive Summary

This AutoFix session processed **2** test cases across **2** attempts.

**Results:**
- **Baseline Success Rate:** 50.0% (1/2)
- **Final Success Rate:** 100.0% (2/2)
- **Improvement:** +1 tests (+50.0%)

✅ **Success:** Code fixes improved test results.

## Test Results Summary

| Test Case | Baseline | Attempt 1 | Final Status | Improvement |
|-----------|----------|-----------|--------------|-------------|
| test_basic_functionality | passed | passed | passed | No |
| test_edge_case | failed | passed | passed | Yes |

## Detailed Results

### Baseline (Before Fixes)
**Status:** failed

**Test Case:** test_basic_functionality
- **Input:** hello world
- **Expected Output:** Hello World!
- **Actual Output:** Hello World!
- **Result:** PASS
- **Evaluation:** Output matches expected exactly

**Test Case:** test_edge_case
- **Input:** 
- **Expected Output:** Empty input
- **Actual Output:** None
- **Result:** FAIL
- **Evaluation:** Output does not match expected

### Best Attempt (Attempt 1)
**Status:** passed

**Test Case:** test_basic_functionality
- **Input:** hello world
- **Expected Output:** Hello World!
- **Actual Output:** Hello World!
- **Result:** PASS
- **Evaluation:** Output matches expected exactly

**Test Case:** test_edge_case
- **Input:** 
- **Expected Output:** Empty input
- **Actual Output:** Empty input
- **Result:** PASS
- **Evaluation:** Output matches expected exactly

## Improvement Analysis

### ✅ Improvements:
The following test cases were successfully fixed:
- test_edge_case: failed → passed

### Overall Assessment:
- **Total Improvements:** 1
- **Total Regressions:** 0
- **Net Change:** +1
```

## Benefits

1. **Debugging**: Complete visibility into test execution for troubleshooting
2. **Analysis**: Detailed metrics for performance optimization
3. **Audit Trail**: Full history of test runs and auto-fix attempts
4. **Reproducibility**: All inputs and outputs preserved for later analysis
5. **Integration**: JSON format allows easy integration with other tools
6. **Documentation**: Markdown reports provide human-readable summaries
7. **PR Consistency**: Summary reports match PR description format exactly
8. **No Dependencies**: Works without GitHub token or internet access

## File Size Considerations

- Detailed logs can be large (several MB) for complex test suites
- Summary files are typically small (< 1KB) for quick reference
- Summary reports (.md files) are typically 5-20KB depending on test complexity
- Files are automatically timestamped to avoid conflicts
- Consider cleanup strategies for long-running test environments

## Integration with CI/CD

The logs and reports can be easily integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run tests with logging
  run: kaizen test --config test_config.yaml --save-logs

- name: Upload test logs
  uses: actions/upload-artifact@v2
  with:
    name: test-logs
    path: test-logs/

- name: Comment with summary report
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const path = require('path');
      
      // Find the latest summary report
      const logsDir = 'test-logs';
      const files = fs.readdirSync(logsDir);
      const reportFiles = files.filter(f => f.endsWith('.md'));
      const latestReport = reportFiles.sort().pop();
      
      if (latestReport) {
        const reportContent = fs.readFileSync(path.join(logsDir, latestReport), 'utf8');
        github.rest.issues.createComment({
          issue_number: context.issue.number,
          owner: context.repo.owner,
          repo: context.repo.repo,
          body: `## Test Summary Report\n\n${reportContent}`
        });
      }
```

## Best Practices

1. **Use for debugging**: Enable `--save-logs` when investigating test failures
2. **Archive important runs**: Keep logs for significant test executions
3. **Monitor file sizes**: Large log files may indicate verbose output
4. **Clean up regularly**: Remove old logs to save disk space
5. **Share selectively**: Detailed logs may contain sensitive information
6. **Use summary reports**: Markdown reports are perfect for documentation and sharing
7. **PR consistency**: Summary reports ensure consistent formatting across PRs and logs
8. **No GitHub required**: Use summary reports for local development without GitHub integration 