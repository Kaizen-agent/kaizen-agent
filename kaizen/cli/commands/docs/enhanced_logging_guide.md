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

### 2. **Auto-Fix Attempt Tracking**
For tests with auto-fix enabled:
- **Complete attempt history**: All fix attempts and their results
- **Code changes**: What changes were made in each attempt
- **Improvement tracking**: How test results improved over attempts
- **Learning insights**: Patterns and strategies that worked

### 3. **Multiple Output Formats**
The system generates three types of files:
- **Detailed JSON logs**: Complete test execution data for programmatic analysis
- **Summary JSON**: Quick reference with key metrics
- **Markdown reports**: Human-readable summaries (same format as PR descriptions)

### 4. **GitHub Token Independence**
- **Summary reports work without GitHub token**: Generate detailed test summaries locally
- **Perfect for local development**: No need for GitHub integration to get comprehensive reports
- **CI/CD friendly**: Works in any environment without GitHub access

## Usage Examples

### Basic Logging
```bash
# Save detailed logs for a test run
kaizen test --config test_config.yaml --save-logs
```

### With Auto-Fix
```bash
# Save logs including auto-fix attempts
kaizen test --config test_config.yaml --auto-fix --save-logs
```

### Without GitHub Integration
```bash
# Generate summary reports without GitHub token
kaizen test --config test_config.yaml --auto-fix --save-logs
# No GITHUB_TOKEN required - summary reports generated locally
```

### Complete Workflow
```bash
# Full workflow with logging
kaizen test --config test_config.yaml --auto-fix --create-pr --save-logs
```

## Output File Structure

```
test-logs/
├── example_test_20240115_103045_detailed_logs.json
├── example_test_20240115_103045_summary.json
└── test_report_20240115_103045.md
```

### File Descriptions

1. **Detailed Logs** (`*_detailed_logs.json`)
   - Complete test execution data
   - All test cases with inputs/outputs
   - Auto-fix attempt history
   - Error details and stack traces
   - Execution timing information

2. **Summary** (`*_summary.json`)
   - Quick reference with key metrics
   - Test status and error messages
   - Reference to detailed logs
   - Compact format for quick analysis

3. **Summary Report** (`test_report_*.md`)
   - Human-readable test summary
   - Same format as PR descriptions
   - **Includes baseline results** (before any fixes)
   - **Shows actual outputs** (not just N/A)
   - Executive summary with improvements
   - Detailed test results table
   - Improvement analysis
   - **Works without GitHub token**

## Analyzing the Data

### JSON Logs Analysis
```python
import json

# Load detailed logs
with open('test-logs/example_test_20240115_103045_detailed_logs.json', 'r') as f:
    logs = json.load(f)

# Analyze test results
test_results = logs['test_results']
for region, region_data in test_results.items():
    if region != 'overall_status':
        print(f"Region: {region}")
        for test_case in region_data['test_cases']:
            print(f"  {test_case['name']}: {test_case['status']}")

# Analyze auto-fix attempts
if 'auto_fix_attempts' in logs:
    for attempt in logs['auto_fix_attempts']:
        print(f"Attempt {attempt['attempt']}: {attempt['status']}")
```

### Markdown Report Analysis
The Markdown reports provide:
- **Executive Summary**: High-level results and improvements
- **Test Results Table**: All test cases with status changes
- **Detailed Results**: Complete test case information
- **Improvement Analysis**: What was fixed and how

## Benefits for Different Use Cases

### 1. **Development and Debugging**
- **Complete visibility**: See exactly what inputs produced what outputs
- **Error analysis**: Detailed error messages and stack traces
- **Reproducibility**: All test data preserved for later analysis
- **No GitHub required**: Generate reports locally without GitHub integration

### 2. **CI/CD Integration**
- **Automated analysis**: JSON format allows programmatic processing
- **Artifact preservation**: Save logs as build artifacts
- **Failure investigation**: Detailed logs help debug CI failures
- **Summary reports**: Human-readable summaries for notifications

### 3. **Team Collaboration**
- **Shared understanding**: Markdown reports provide clear summaries
- **PR consistency**: Same format as PR descriptions
- **Historical tracking**: Keep logs for important test runs
- **No dependencies**: Works without GitHub token or internet access

### 4. **Performance Analysis**
- **Timing data**: Execution time for each test case
- **Resource usage**: Track performance over time
- **Optimization insights**: Identify slow tests and bottlenecks

## Best Practices

### 1. **When to Use Enhanced Logging**
- **Debugging test failures**: Enable for troubleshooting
- **Performance analysis**: Track execution times
- **Auto-fix development**: Understand fix attempts
- **Documentation**: Generate reports for team sharing
- **CI/CD integration**: Automated test result analysis

### 2. **File Management**
- **Organize by date**: Use timestamps to avoid conflicts
- **Archive important runs**: Keep logs for significant executions
- **Monitor disk usage**: Large log files may accumulate
- **Clean up regularly**: Remove old logs to save space

### 3. **Security Considerations**
- **Sensitive data**: Logs may contain test inputs/outputs
- **Selective sharing**: Share summary reports rather than detailed logs
- **Access control**: Restrict access to detailed logs in shared environments

### 4. **Integration Tips**
- **GitHub Actions**: Upload logs as artifacts
- **Slack/Teams**: Share summary reports in notifications
- **JIRA**: Attach summary reports to tickets
- **Documentation**: Include summary reports in test documentation

## Troubleshooting

### Common Issues

1. **Large log files**
   - **Cause**: Verbose test output or many auto-fix attempts
   - **Solution**: Monitor file sizes and clean up old logs

2. **Missing summary report**
   - **Cause**: No test results available
   - **Solution**: Summary reports are generated for any test run, including baseline results without auto-fix

3. **GitHub token errors**
   - **Cause**: Missing GITHUB_TOKEN when using --create-pr
   - **Solution**: Summary reports work without GitHub token - only PR creation requires it

4. **Permission errors**
   - **Cause**: Cannot write to test-logs directory
   - **Solution**: Ensure write permissions to the current directory

### Getting Help

If you encounter issues with enhanced logging:
1. Check the console output for error messages
2. Verify file permissions in the current directory
3. Ensure sufficient disk space for log files
4. Review the generated logs for clues about failures
5. Use summary reports for quick analysis without detailed logs

## Future Enhancements

The enhanced logging system is designed to be extensible:
- **Custom log formats**: Support for different output formats
- **Log compression**: Automatic compression of large log files
- **Remote logging**: Integration with external logging services
- **Advanced analytics**: Built-in analysis tools for log data
- **Real-time monitoring**: Live log streaming for long-running tests 