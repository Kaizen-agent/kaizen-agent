# Kaizen Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![OpenAI GPT-4](https://img.shields.io/badge/OpenAI-GPT--4-purple)](https://openai.com/gpt-4)

Kaizen Agent is an AI-powered testing framework that helps you run tests, analyze failures, and automatically fix issues in your code. The name "Kaizen" comes from the Japanese philosophy of continuous improvement, reflecting our tool's purpose of helping developers write better code.

## 🌟 Features

- 🧪 Run multiple tests from YAML files
- 🔍 Analyze test failures
- 🛠️ Automatically fix failing tests
- 🔄 Rerun tests after fixes
- 📊 Create pull requests for successful improvements

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
```

## 💻 Usage

### Command Line Interface

Kaizen provides two main commands for testing and fixing your code:

1. Run tests from YAML files:
```bash
kaizen run-tests test1.yaml test2.yaml --project path/to/project --results path/to/results
```

2. Fix failing tests and create a PR:
```bash
kaizen fix-tests test1.yaml test2.yaml --project path/to/project --results path/to/results --make-pr
```

### Test Configuration

Example test configuration:
```yaml
name: Email Agent Test
agent_type: dynamic_region
steps:
  - name: Basic Email Test
    input:
      file_path: email_agent.py
      region: email_agent
      method: improve_email
      input: "hey, can we meet tomorrow?"
    expected_output_contains:
      - "Dear"
      - "meeting"
      - "schedule"
    validation:
      type: contains
      min_length: 100
      max_length: 500
```

### Using as a Python Module

You can integrate Kaizen into your Python projects:

```python
from kaizen import TestRunner, auto_fix_tests

# Run tests
runner = TestRunner("path/to/project", "path/to/results")
results = runner.run_tests(["test1.yaml", "test2.yaml"])

# Fix failing tests
fixed_tests = auto_fix_tests(["test1.yaml", "test2.yaml"], "path/to/project", "path/to/results", make_pr=True)
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
- [ ] Enhanced test failure analysis
- [ ] Integration with more CI/CD platforms
- [ ] Custom test validation rules
- [ ] Performance optimization suggestions

---

Made with ❤️ by the Kaizen Agent team