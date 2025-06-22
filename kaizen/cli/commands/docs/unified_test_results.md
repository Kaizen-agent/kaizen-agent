# Unified Test Results

## Overview

The Kaizen CLI now uses a unified approach for handling test results through the `TestExecutionResult` class. This replaces the previous multiple formats and provides a cleaner, more maintainable way to work with test data.

## Problem Solved

Previously, test results were stored in multiple different formats:
- `results` - Raw dictionary from test runner
- `failed_tests` - List of dictionaries extracted from results
- `attempts` - List of fix attempts with their own format
- `TestResult` - Legacy model for CLI output

This created confusion and made the code harder to maintain.

## Solution

The new `TestExecutionResult` class provides:

### 1. **Unified Data Structure**
```python
@dataclass
class TestExecutionResult:
    name: str
    file_path: Path
    config_path: Path
    test_cases: List[TestCaseResult]
    summary: TestExecutionSummary
    status: TestStatus
    # ... other fields
```

### 2. **Rich Test Case Information**
```python
@dataclass
class TestCaseResult:
    name: str
    status: TestStatus
    region: str
    input: Optional[Any]
    expected_output: Optional[Any]
    actual_output: Optional[Any]
    error_message: Optional[str]
    evaluation: Optional[Dict[str, Any]]
    # ... other fields
```

### 3. **Comprehensive Summary**
```python
@dataclass
class TestExecutionSummary:
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    success_rate: float
    regions: Dict[str, Dict[str, int]]
    # ... other fields
```

## Key Benefits

### 1. **Single Source of Truth**
All test data is stored in one place, eliminating confusion about which format to use.

### 2. **Type Safety**
Using dataclasses with proper typing provides better IDE support and catches errors at development time.

### 3. **Easy Data Access**
```python
# Get failed tests
failed_tests = test_result.get_failed_tests()

# Get tests by region
region_tests = test_result.get_tests_by_region("test_region_1")

# Get tests by status
passed_tests = test_result.get_tests_by_status(TestStatus.PASSED)

# Check overall success
is_successful = test_result.is_successful()
```

### 4. **Backward Compatibility**
The class can convert to and from legacy formats:
```python
# Convert legacy format to unified
unified_result = TestExecutionResult.from_legacy_format(
    name, file_path, config_path, legacy_results
)

# Convert unified to legacy format
legacy_format = unified_result.to_legacy_format()
```

### 5. **Rich Metadata**
Each test case includes:
- Input and output data
- Error messages and details
- Evaluation results
- Execution timing
- Region information
- Custom metadata

## Simplified Workflow

### Before (Multiple Formats)
```python
# Old approach - confusing and error-prone
runner = TestRunner(config)
results = runner.run_tests(file_path)  # Returns dict
failed_tests = collect_failed_tests(results)  # Extract failed tests
if failed_tests:  # Check if any failed
    # Handle failures
```

### After (Unified Format)
```python
# New approach - clean and simple
runner = TestRunner(config)
test_result = runner.run_tests(file_path)  # Returns TestExecutionResult
if not test_result.is_successful():  # Check directly
    failed_tests = test_result.get_failed_tests()  # Extract when needed
    # Handle failures
```

## Usage Examples

### Creating a Test Result
```python
from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus

# Create test cases
test_cases = [
    TestCaseResult(
        name="test_basic_functionality",
        status=TestStatus.PASSED,
        region="test_region_1",
        input="test_input",
        expected_output="expected",
        actual_output="expected"
    ),
    TestCaseResult(
        name="test_edge_case",
        status=TestStatus.FAILED,
        region="test_region_2",
        input="edge_input",
        expected_output="expected",
        actual_output="actual",
        error_message="Test failed"
    )
]

# Create test execution result
result = TestExecutionResult(
    name="My Test Suite",
    file_path=Path("test_file.py"),
    config_path=Path("config.yaml")
)
result.add_test_cases(test_cases)
```

### Working with Test Results
```python
# Check overall status
if result.is_successful():
    print("All tests passed!")
else:
    print(f"{result.get_failure_count()} tests failed")

# Get specific test data
failed_tests = result.get_failed_tests()
for tc in failed_tests:
    print(f"Failed: {tc.name} - {tc.get_error_summary()}")

# Get summary statistics
summary = result.summary
print(f"Success rate: {summary.get_success_rate():.1f}%")
print(f"Total tests: {summary.total_tests}")
```

### Real-World Usage in Test Commands
```python
# In test_commands.py - much cleaner now
runner = TestRunner(runner_config)
test_execution_result = runner.run_tests(self.config.file_path)

# No need for conversion or separate failed_tests
if self.config.auto_fix and not test_execution_result.is_successful():
    # Extract failed tests only when needed for auto-fix
    failed_tests = get_failed_tests_dict_from_unified(test_execution_result)
    test_attempts = self._handle_auto_fix(failed_tests, config, runner_config, test_execution_result)
```

## Migration Guide

### For Existing Code

1. **Replace direct dictionary access**:
   ```python
   # Old way
   failed_tests = collect_failed_tests(results)
   
   # New way
   test_result = runner.run_tests(file_path)  # Now returns TestExecutionResult
   failed_tests = test_result.get_failed_tests()
   ```

2. **Use unified methods**:
   ```python
   # Old way
   if not failed_tests:
       # handle success
   
   # New way
   if test_result.is_successful():
       # handle success
   ```

3. **Access test data directly**:
   ```python
   # Old way
   for test in failed_tests:
       region = test['region']
       name = test['test_name']
   
   # New way
   for test_case in test_result.get_failed_tests():
       region = test_case.region
       name = test_case.name
   ```

### For New Code

Use the unified format directly:
```python
from kaizen.cli.commands.models import TestExecutionResult, TestCaseResult, TestStatus

# TestRunner now returns TestExecutionResult directly
runner = TestRunner(config)
test_result = runner.run_tests(file_path)

# Work with the unified result
if test_result.is_successful():
    print("All tests passed!")
else:
    for failed_test in test_result.get_failed_tests():
        print(f"Failed: {failed_test.name}")
```

## File Structure

```
kaizen/cli/commands/models/
├── test_execution_result.py    # New unified classes
├── result.py                   # Legacy TestResult (for backward compatibility)
└── __init__.py                 # Exports both old and new

kaizen/autofix/test/
└── runner.py                   # Updated to return TestExecutionResult

kaizen/utils/
└── test_utils.py               # Simplified utility functions
```

## Key Changes

### 1. **TestRunner API Change**
- **Before**: `run_tests()` returned `Dict[str, Any]`
- **After**: `run_tests()` returns `TestExecutionResult`

### 2. **No More Conversion**
- **Before**: Had to convert between formats
- **After**: Work with unified format directly

### 3. **Extract on Demand**
- **Before**: Had to maintain separate `failed_tests` list
- **After**: Extract failed tests only when needed with `get_failed_tests()`

### 4. **Simplified Test Commands**
- **Before**: Complex logic with multiple formats
- **After**: Clean, straightforward code

## Future Enhancements

1. **Serialization**: Add JSON/YAML serialization methods
2. **Comparison**: Add methods to compare test results
3. **Filtering**: Add more sophisticated filtering options
4. **Statistics**: Add more detailed statistical analysis
5. **Visualization**: Add methods for generating charts and graphs

## Conclusion

The unified test results approach provides a much cleaner and more maintainable way to work with test data. It eliminates confusion about data formats, provides better type safety, and makes the codebase easier to understand and extend.

The key improvement is that the TestRunner now returns the unified format directly, eliminating the need for conversion and separate data structures. This follows the principle of "extract on demand" rather than maintaining multiple formats. 