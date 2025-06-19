# Dependency Management in Kaizen CLI

This directory contains examples demonstrating how to use dependency management in Kaizen CLI test configurations.

## Overview

The Kaizen CLI now supports specifying dependencies and referenced files in test configuration files. This allows you to:

1. **Import Python packages** before test execution
2. **Import local files** that are referenced by your test code
3. **Ensure all dependencies are available** before running tests
4. **Use imported dependencies during test execution**

## How It Works

### Complete Integration Flow

1. **Configuration Loading**: When you run a test, the CLI loads the configuration file
2. **Dependency Import**: The system imports all specified packages and files using the `DependencyManager`
3. **Namespace Creation**: A namespace dictionary is created containing all imported modules
4. **Test Execution**: The namespace is passed to the test runner and made available during test execution
5. **Code Execution**: When test code runs, it has access to all imported dependencies
6. **Cleanup**: The system cleans up any modifications to the Python environment

### Technical Details

The integration works through several components:

- **DependencyManager**: Handles importing packages and files, creating a namespace
- **TestAllCommand**: Orchestrates the dependency import and test execution
- **TestRunner**: Receives the imported dependencies and passes them to the execution system
- **CodeRegionExecutor**: Uses the imported dependencies during code execution

## Configuration Structure

### Dependencies

The `dependencies` field allows you to specify Python packages that should be imported before test execution:

```yaml
dependencies:
  - "requests>=2.25.0"    # Package with version requirement
  - "pandas==1.3.0"       # Exact version
  - "numpy"               # Latest version
  - "click"               # Latest version
  - "rich"                # Latest version
```

### Referenced Files

The `referenced_files` field allows you to specify local Python files that should be imported:

```yaml
referenced_files:
  - "utils/helper.py"           # Relative to config file
  - "models/data_processor.py"  # Relative to config file
  - "config/settings.py"        # Relative to config file
```

### Complete Example

See `test_config_with_dependencies.yaml` for a complete example configuration.

## Usage

### Running Tests with Dependencies

```bash
kaizen test-all --config test_config_with_dependencies.yaml --auto-fix
```

### Configuration File Structure

```yaml
name: "Test with Dependencies"
file_path: "test_file.py"
description: "Example test that demonstrates dependency management"

# Package dependencies
dependencies:
  - "requests>=2.25.0"
  - "pandas==1.3.0"
  - "numpy"

# Local files to import
referenced_files:
  - "utils/helper.py"
  - "models/data_processor.py"

# Test configuration
agent_type: "default"
auto_fix: true
create_pr: false
max_retries: 3

# Test regions and steps
regions:
  - "test_function"
  - "test_class"

steps:
  - name: "Test basic functionality"
    input:
      method: "run"
      input: "test input data"
    expected_output:
      status: "success"
    description: "Test the basic functionality"
    timeout: 30
```

## Features

### Package Dependencies

- **Version Support**: Supports version specifiers (`==`, `>=`, `<=`, `>`, `<`)
- **Error Handling**: Gracefully handles missing packages with warnings
- **Import Validation**: Validates that packages can be imported
- **Runtime Availability**: Imported packages are available during test execution

### Local File Dependencies

- **Relative Paths**: Supports relative paths from the config file location
- **Absolute Paths**: Supports absolute paths
- **Module Import**: Imports files as Python modules
- **Path Resolution**: Automatically resolves file paths
- **Runtime Availability**: Imported files are available during test execution

### Error Handling

- **Missing Packages**: Logs warnings for missing packages but continues execution
- **Missing Files**: Logs warnings for missing files but continues execution
- **Import Errors**: Provides detailed error messages for import failures
- **Graceful Degradation**: Tests can still run even if some dependencies fail to import

## Testing the Integration

### Running the Integration Test

```bash
cd kaizen/cli/commands
python examples/test_integration.py
```

This test verifies that:
1. Dependencies are properly imported
2. The namespace is created correctly
3. Dependencies are passed to the test runner
4. The integration works end-to-end

### Example Test File

The `test_file.py` example demonstrates how to use imported dependencies:

```python
import requests
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def test_function(input_data: str) -> Dict[str, Any]:
    """Test function that uses dependencies."""
    try:
        # Use pandas for data processing
        df = pd.DataFrame({'data': [input_data]})
        
        # Use numpy for calculations
        result = np.mean([1, 2, 3, 4, 5])
        
        # Use requests for API call (simulated)
        response = {"status": "success", "data": input_data}
        
        return {
            "status": "success",
            "result": result,
            "data": df.to_dict(),
            "response": response
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
```

## Best Practices

1. **Specify Versions**: Use version specifiers for critical dependencies
2. **Use Relative Paths**: Use relative paths for local files when possible
3. **Test Dependencies**: Ensure all dependencies are available in your test environment
4. **Minimize Dependencies**: Only include dependencies that are actually needed
5. **Document Dependencies**: Add comments explaining why each dependency is needed
6. **Handle Import Errors**: Write your test code to handle cases where dependencies might not be available

## Troubleshooting

### Common Issues

1. **Package Not Found**: Ensure the package is installed in your environment
2. **File Not Found**: Check that the file path is correct relative to the config file
3. **Import Errors**: Verify that the file contains valid Python code
4. **Version Conflicts**: Use specific version requirements to avoid conflicts
5. **Namespace Issues**: Check that imported modules are available in your test code

### Debugging

Enable debug logging to see detailed information about dependency imports:

```bash
kaizen test-all --config test_config.yaml --auto-fix --log-level DEBUG
```

### Verification

To verify that dependencies are properly imported, you can:

1. Check the console output for dependency import messages
2. Use the integration test to verify the complete flow
3. Add logging to your test code to verify imports are available

## Integration with Existing Features

The dependency management system integrates seamlessly with existing Kaizen CLI features:

- **Auto-fix**: Dependencies are available during auto-fix operations
- **Test Execution**: All dependencies are imported before test execution
- **Error Reporting**: Dependency errors are included in test reports
- **Configuration Validation**: Dependencies are validated during configuration loading
- **Code Region Execution**: Imported dependencies are available in the execution namespace

## Example Files

- `test_config_with_dependencies.yaml`: Complete configuration example
- `test_file.py`: Example test file that uses dependencies
- `test_integration.py`: Integration test to verify functionality
- `README.md`: This documentation file 