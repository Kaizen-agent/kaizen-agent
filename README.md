# Kaizen Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![OpenAI GPT-4](https://img.shields.io/badge/OpenAI-GPT--4-purple)](https://openai.com/gpt-4)

Kaizen Agent is an AI-powered code improvement tool that leverages OpenAI's GPT-4 to enhance code quality, fix issues, and automatically create pull requests for improvements. The name "Kaizen" comes from the Japanese philosophy of continuous improvement, reflecting our tool's purpose of helping developers write better code.

## 🌟 Features

- 🤖 AI-powered code analysis and improvements
- 🔍 Automated security and performance checks
- 🛠️ Interactive code testing and fixing
- 🔄 Automatic pull request creation
- 📊 Comprehensive test coverage
- 🎯 Multiple testing modes (automated, interactive)
- 🧪 AI-powered test generation

## 📋 Prerequisites

- Python 3.8 or higher
- OpenAI API key
- GitHub account (for PR features)
- Git

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kaizen-agent.git
cd kaizen-agent
```

2. Create and activate a virtual environment:
```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

4. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

5. Set up your environment variables:
```bash
# Create a .env file in the project root
OPENAI_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_here
```

## 💻 Usage

### Command Line Interface

Kaizen provides several commands for testing and improving your code:

1. Test a specific file:
```bash
kaizen test path/to/your/file.py --config path/to/test.yaml
```

2. Start an interactive test session:
```bash
kaizen interactive "your code here" --language python --turns 5
```

3. Run a specific test file:
```bash
kaizen run-test path/to/test.yaml
```

4. Run multiple tests with auto-fix and PR creation:
```bash
# Run all tests in a directory
kaizen test-all --config path/to/tests/ --auto-fix --create-pr

# Run specific test files
kaizen test-all test1.yaml test2.yaml --auto-fix --create-pr
```

5. Generate new test cases:
```bash
# Basic test generation
kaizen generate-tests \
  --project ./my-agent \
  --results ./test-results/ \
  --output ./test-examples/

# Generate tests with existing configuration
kaizen generate-tests \
  --project ./my-agent \
  --results ./test-results/ \
  --output ./test-examples/ \
  --config ./existing-tests/

# Generate tests with rationale and create PR
kaizen generate-tests \
  --project ./my-agent \
  --results ./test-results/ \
  --output ./test-examples/ \
  --config ./existing-tests/ \
  --suggestions \
  --make-pr
```

### Auto-Fix and PR Features

The auto-fix feature streamlines the improvement process by:
1. Collecting test failures
2. Analyzing issues using GPT-4
3. Creating a new Git branch
4. Committing fixes
5. Creating a detailed Pull Request

Example test configuration:
```yaml
name: Security and Performance Test
agent_type: test
learning_mode: automated
learning_focus:
  - security
  - performance
  - code_quality

evaluation:
  llm_provider: openai
  criteria:
    - name: security
      description: "Check for security issues"
    - name: performance
      description: "Check for performance issues"
```

### Test Generation

The test generation feature analyzes your codebase and existing test results to:
1. Identify untested functions and classes
2. Find complex code regions that need more test coverage
3. Analyze existing test failures
4. Generate new YAML test cases using GPT-4
5. Optionally create a pull request with the new tests

When using the `--config` option, the generator will:
1. Analyze existing test configurations
2. Extract patterns and test scenarios
3. Ensure new tests follow the same structure
4. Avoid duplicating existing test cases
5. Complement existing test coverage

Example generated test case:
```yaml
name: Test Email Agent Response
agent_type: python
steps:
  - name: Test basic email improvement
    input:
      text: "hi, can we meet tomorrow?"
    expected_output_contains:
      - "Dear"
      - "Would you be available"
    # Reason: Tests basic email formalization and time reference handling
```

### Using as a Python Module

You can integrate Kaizen into your Python projects:

```python
from kaizen import run_autofix_and_pr

failures = [
    {"test_name": "Security Test", "error_message": "Code is missing input validation"},
    {"test_name": "Performance Test", "error_message": "Inefficient loop found in line 24"}
]
run_autofix_and_pr(failures, "path/to/file.py")
```

## 🧪 Testing

Run the test suite using pytest:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=kaizen

# Run specific test file
pytest test_kaizen.py
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please read our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for providing the GPT-4 API
- All contributors who have helped improve this project

## 📚 Documentation

For more detailed documentation, visit our [documentation site](https://kaizen-agent.readthedocs.io/).

## 💬 Support

If you need help or have questions:
- Open an issue
- Join our [Discord community](https://discord.gg/kaizen-agent)
- Check our [FAQ](docs/FAQ.md)

## 🔄 Roadmap

- [ ] Support for more programming languages
- [ ] Enhanced security analysis
- [ ] Integration with more CI/CD platforms
- [ ] Custom rule creation interface
- [ ] Performance optimization suggestions

---

Made with ❤️ by the Kaizen Agent team