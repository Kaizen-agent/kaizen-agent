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

### Environment Configuration

Kaizen Agent supports multiple LLM providers and models. You can configure them in your `.env` file. Here are some example configurations:

```env
# OpenAI Configuration
KAIZEN_CLI_MODEL=gpt-4
KAIZEN_CLI_API_KEY=your-openai-key
KAIZEN_CLI_PROVIDER=openai

# Anthropic Configuration
KAIZEN_CLI_MODEL=claude-3-opus
KAIZEN_CLI_API_KEY=your-anthropic-key
KAIZEN_CLI_PROVIDER=anthropic

# Google Configuration (Default)
KAIZEN_CLI_MODEL=gemini-1.5-flash
KAIZEN_CLI_API_KEY=your-google-key
KAIZEN_CLI_PROVIDER=google

# Kaizen Custom Model
KAIZEN_CLI_MODEL=kaizen-custom-model
KAIZEN_CLI_API_KEY=your-kaizen-key
KAIZEN_CLI_PROVIDER=kaizen
```

You can use any model name supported by your chosen provider. The configuration system is flexible and will work with new models as they become available.

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
# Run all tests in a directory with default settings
kaizen test-all --config path/to/tests/ --auto-fix --create-pr

# Run with multiple retry attempts for auto-fix
kaizen test-all --config path/to/tests/ --auto-fix --max-retries 3

# Run specific test files with custom retry settings
kaizen test-all test1.yaml test2.yaml --auto-fix --max-retries 5 --create-pr
```

### Auto-Fix and PR Features

The auto-fix feature streamlines the improvement process by:
1. Collecting test failures
2. Analyzing issues using GPT-4
3. Making multiple attempts to fix the code (configurable via --max-retries)
4. Creating a new Git branch
5. Committing fixes
6. Creating a detailed Pull Request

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