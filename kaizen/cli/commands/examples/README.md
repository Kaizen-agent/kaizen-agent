# Dependency Management in Kaizen CLI

This directory contains examples demonstrating how to use dependency management in Kaizen CLI test configurations.

## Overview

The Kaizen CLI now supports specifying dependencies and referenced files in test configuration files. This allows you to:

1. **Import Python packages** before test execution
2. **Import local files** that are referenced by your test code
3. **Ensure all dependencies are available** before running tests

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

## How It Works

1. **Configuration Loading**: When you run a test, the CLI loads the configuration file
2. **Dependency Import**: The system imports all specified packages and files
3. **Test Execution**: Tests are executed with all dependencies available
4. **Cleanup**: The system cleans up any modifications to the Python environment

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

### Local File Dependencies

- **Relative Paths**: Supports relative paths from the config file location
- **Absolute Paths**: Supports absolute paths
- **Module Import**: Imports files as Python modules
- **Path Resolution**: Automatically resolves file paths

### Error Handling

- **Missing Packages**: Logs warnings for missing packages but continues execution
- **Missing Files**: Logs warnings for missing files but continues execution
- **Import Errors**: Provides detailed error messages for import failures

## Best Practices

1. **Specify Versions**: Use version specifiers for critical dependencies
2. **Use Relative Paths**: Use relative paths for local files when possible
3. **Test Dependencies**: Ensure all dependencies are available in your test environment
4. **Minimize Dependencies**: Only include dependencies that are actually needed
5. **Document Dependencies**: Add comments explaining why each dependency is needed

## Example Files

- `test_config_with_dependencies.yaml`: Complete configuration example
- `test_file.py`: Example test file that uses dependencies
- `README.md`: This documentation file

## Troubleshooting

### Common Issues

1. **Package Not Found**: Ensure the package is installed in your environment
2. **File Not Found**: Check that the file path is correct relative to the config file
3. **Import Errors**: Verify that the file contains valid Python code
4. **Version Conflicts**: Use specific version requirements to avoid conflicts

### Debugging

Enable debug logging to see detailed information about dependency imports:

```bash
kaizen test-all --config test_config.yaml --auto-fix --log-level DEBUG
```

## Integration with Existing Features

The dependency management system integrates seamlessly with existing Kaizen CLI features:

- **Auto-fix**: Dependencies are available during auto-fix operations
- **Test Execution**: All dependencies are imported before test execution
- **Error Reporting**: Dependency errors are included in test reports
- **Configuration Validation**: Dependencies are validated during configuration loading 