# Kaizen - AI-Powered Test Automation and Code Fixing

Kaizen is a powerful CLI tool that automates test execution, failure analysis, and code fixing. It can run multiple tests simultaneously, analyze failures, automatically fix code issues, and create pull requests with the fixes.

## Key Features

- **Parallel Test Execution**: Run multiple tests simultaneously across different files
- **Intelligent Failure Analysis**: Automatically analyze test failures and identify root causes
- **Automated Code Fixing**: Fix code issues automatically using AI-powered analysis
- **Pull Request Integration**: Create pull requests with fixes for review
- **Retry Mechanism**: Automatically retry failed tests after fixes
- **Detailed Reporting**: Generate comprehensive test reports and fix attempts

## Installation

```bash
pip install kaizen
```

## Quick Start

1. Create a test configuration file (YAML):

```yaml
name: My Test Suite
file_path: path/to/your/code.py
tests:
  - name: Test Case 1
    input: "test input"
    expected_output: "expected output"
  - name: Test Case 2
    input: "another input"
    expected_output: "another output"
```

2. Run tests with auto-fix:

```bash
kaizen test-all --config test_config.yaml --auto-fix --create-pr
```

## Core Commands

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

### Run Individual Test Block

```bash
kaizen run-block <file_path> [input_text] [--output <output_file>]
```

## Project Structure

```
kaizen/
├── cli/              # CLI implementation
├── core/             # Core functionality
├── utils/            # Utility functions
├── models/           # Data models
├── config/           # Configuration management
├── agents/           # Agent implementations
└── autofix/          # Auto-fix functionality
    ├── main.py       # Main auto-fix logic
    ├── pr/           # Pull request handling
    ├── test/         # Test execution
    ├── code/         # Code analysis and fixing
    ├── file/         # File operations
    └── prompt/       # AI prompts
```

## Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kaizen.git
cd kaizen
```

2. Install development dependencies:
```bash
pip install -e ".[dev]"
```

3. Run tests:
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details