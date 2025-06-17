# Kaizen - AI-Powered Test Automation and Code Fixing

[![PyPI version](https://badge.fury.io/py/kaizen.svg)](https://badge.fury.io/py/kaizen)
[![Python Versions](https://img.shields.io/pypi/pyversions/kaizen.svg)](https://pypi.org/project/kaizen/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://github.com/yourusername/kaizen/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/kaizen/actions/workflows/tests.yml)
[![Documentation](https://readthedocs.org/projects/kaizen/badge/?version=latest)](https://kaizen.readthedocs.io/en/latest/?badge=latest)

Kaizen is a powerful CLI tool that automates test execution, failure analysis, and code fixing. It can run multiple tests simultaneously, analyze failures, automatically fix code issues, and create pull requests with the fixes.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Features

- **Parallel Test Execution**: Run multiple tests simultaneously across different files
- **Intelligent Failure Analysis**: Automatically analyze test failures and identify root causes
- **Automated Code Fixing**: Fix code issues automatically using AI-powered analysis
- **Pull Request Integration**: Create pull requests with fixes for review
- **Retry Mechanism**: Automatically retry failed tests after fixes
- **Detailed Reporting**: Generate comprehensive test reports and fix attempts

## Installation

### From PyPI

```bash
pip install kaizen
```

### From Source

```bash
git clone https://github.com/yourusername/kaizen.git
cd kaizen
pip install -e ".[dev]"
```

## Quick Start

1. Create a test configuration file (YAML):

```yaml
name: My Test Suite
file_path: path/to/your/code.py
tests:
  - name: Test Case 1
    input:
      region: block  # Optional: specify code region to test
      method: run    # Optional: specify method to run
      input: "test input"  # Optional: input for the test
  - name: Test Case 2
    input:
      file: path/to/test/file.py  # Optional: specify test file
```

2. Run tests with auto-fix:

```bash
kaizen test-all --config test_config.yaml --auto-fix --create-pr
```

## Usage

### Run Tests with Auto-Fix

```bash
kaizen test-all --config <config_file> [--auto-fix] [--create-pr] [--max-retries <n>] [--base-branch <branch>]
```

Options:
- `--config`: Path to test configuration file (required)
- `--auto-fix`: Enable automatic code fixing
- `--create-pr`: Create a pull request with fixes
- `--max-retries`: Maximum number of fix attempts (default: 1)
- `--base-branch`: Base branch for pull request (default: main)

### Fix Specific Tests

```bash
kaizen fix-tests <test_files> --project <project_path> [--make-pr] [--max-retries <n>] [--base-branch <branch>]
```

Options:
- `test_files`: One or more test files to fix
- `--project`: Project root directory (required)
- `--make-pr`: Create a pull request with fixes
- `--max-retries`: Maximum number of fix attempts (default: 1)
- `--base-branch`: Base branch for pull request (default: main)

### Run Individual Test Block

```bash
kaizen run-block <file_path> [input_text] [--output <output_file>]
```

Options:
- `file_path`: Path to the file containing the code block
- `input_text`: Optional input for the test
- `--output`: Optional output file path for test results

## Configuration

The test configuration file (YAML) supports the following structure:

```yaml
name: Test Suite Name
file_path: path/to/main/code.py
tests:
  - name: Test Case Name
    input:
      # Optional: Test a specific code region
      region: block
      method: run
      input: "test input"
      
  - name: Another Test Case
    input:
      # Optional: Test a specific file
      file: path/to/test/file.py
```

Configuration fields:
- `name`: Name of the test suite
- `file_path`: Path to the main code file
- `tests`: List of test cases
  - `name`: Name of the test case
  - `input`: Test input configuration
    - `region`: Optional code region to test
    - `method`: Optional method to run
    - `input`: Optional input for the test
    - `file`: Optional test file path

## Development

### Prerequisites

- Python 3.8+
- pip
- git

### Setup Development Environment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kaizen.git
cd kaizen
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

### Running Tests

```bash
pytest
```

### Code Style

We use [black](https://github.com/psf/black) for code formatting and [isort](https://pycqa.github.io/isort/) for import sorting. To format your code:

```bash
black .
isort .
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📚 [Documentation](https://kaizen.readthedocs.io/)
- 💬 [Discord Community](https://discord.gg/kaizen)
- 🐛 [Issue Tracker](https://github.com/yourusername/kaizen/issues)
- 📧 [Email Support](mailto:support@kaizen.dev)

## Acknowledgments

- Thanks to all our contributors
- Inspired by [list of inspirations]
- Built with [list of key technologies]