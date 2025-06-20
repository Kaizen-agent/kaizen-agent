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
- [Environment Setup](#environment-setup)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Multiple Inputs & Outputs](#multiple-inputs--outputs)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Features

- **Parallel Test Execution**: Run multiple tests simultaneously across different files
- **Multiple Input Support**: Test agents with various input types (strings, dictionaries, objects, and inline objects)
- **Multiple Output Evaluation**: Evaluate return values, specific variables, and multiple outputs from single test execution
- **Intelligent Failure Analysis**: Automatically analyze test failures and identify root causes
- **Automated Code Fixing**: Fix code issues automatically using AI-powered analysis
- **Pull Request Integration**: Create pull requests with fixes and improvements
- **Retry Mechanism**: Automatically retry failed tests after fixes
- **Detailed Reporting**: Generate comprehensive test reports and fix attempts
- **Configuration Management**: YAML-based configuration with validation and dependency management
- **Dependency Management**: Automatic handling of package dependencies and local file imports

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

## Environment Setup

Before using Kaizen, you need to set up your environment variables for API access.

### Required Environment Variables

- **`GOOGLE_API_KEY`** (Required): Your Google AI API key for LLM operations
  - Get it from: https://makersuite.google.com/app/apikey

- **`GITHUB_TOKEN`** (Required for PR creation): Your GitHub personal access token
  - Create it at: https://github.com/settings/tokens
  - Required scopes: `repo`, `workflow`

### Optional Environment Variables

- **`OPENAI_API_KEY`**: Alternative LLM provider
- **`ANTHROPIC_API_KEY`**: Alternative LLM provider
- **`LLM_MODEL_NAME`**: Custom LLM model name (default: `gemini-2.5-flash-preview-05-20`)

### Environment Setup

1. **Create a .env file:**
   ```bash
   # Create .env file with your API keys
   echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
   echo "GITHUB_TOKEN=your_github_token_here" >> .env
   ```

2. **Or use environment variables:**
   ```bash
   export GOOGLE_API_KEY="your_google_api_key_here"
   export GITHUB_TOKEN="your_github_token_here"
   ```

For detailed setup instructions, see the [Environment Setup Guide](docs/environment-setup.md).

## Quick Start

1. Create a test configuration file (YAML):

```yaml
name: My Test Suite
file_path: path/to/your/code.py
description: "Test suite for my application"

# Test steps
steps:
  - name: Test Case 1
    input:
      method: run
      input: "test input"
    description: "Test basic functionality"
    
  - name: Test Case 2
    input:
      method: process_data
      input: {"data": [1, 2, 3]}
    description: "Test data processing"
```

2. Run tests with auto-fix:

```bash
kaizen test-all --config test_config.yaml --auto-fix --create-pr
```

## Usage

### Available Commands

```bash
# Run all tests in configuration
kaizen test-all --config <config_file> [options]

# Fix specific test files
kaizen fix-tests <test_files> --project <project_path> [options]
```

### Run Tests with Auto-Fix

```bash
kaizen test-all --config <config_file> [--auto-fix] [--create-pr] [--max-retries <n>] [--base-branch <branch>]
```

Options:
- `--config`, `-c`: Path to test configuration file (required)
- `--auto-fix`: Enable automatic code fixing
- `--create-pr`: Create a pull request with fixes
- `--max-retries`: Maximum number of fix attempts (default: 1)
- `--base-branch`: Base branch for pull request (default: main)
- `--pr-strategy`: Strategy for when to create PRs (default: ANY_IMPROVEMENT)

### Fix Specific Tests

```bash
kaizen fix-tests <test_files> --project <project_path> [--make-pr] [--max-retries <n>] [--base-branch <branch>]
```

Options:
- `test_files`: One or more test files to fix
- `--project`, `-p`: Project root directory (required)
- `--make-pr`: Create a pull request with fixes
- `--max-retries`: Maximum number of fix attempts (default: 1)
- `--base-branch`: Base branch for pull request (default: main)
- `--results`, `-r`: Path to save test results

## Configuration

The test configuration file (YAML) supports the following structure:

```yaml
name: Test Suite Name
file_path: path/to/main/code.py
description: "Description of the test suite"

# Package dependencies to import before test execution
dependencies:
  - "requests>=2.25.0"
  - "pandas==1.3.0"
  - "numpy"

# Local files to import (relative to config file location)
referenced_files:
  - "utils/helper.py"
  - "models/data_processor.py"

# Files that should be fixed if tests fail
files_to_fix:
  - "main_code.py"
  - "utils/helper.py"

# Test configuration
agent_type: "default"
auto_fix: true
create_pr: false
max_retries: 3
base_branch: "main"
pr_strategy: "ANY_IMPROVEMENT"

# Test regions to execute
regions:
  - "test_function"
  - "test_class"

# Test steps
steps:
  - name: Test Case Name
    input:
      method: run
      input: "test input"
    description: "Description of the test case"
    timeout: 30
    retries: 2

# Evaluation criteria
evaluation:
  criteria:
    - "Function returns expected result"
    - "Error handling works correctly"
  llm_provider: "openai"
  model: "gpt-4"
  settings:
    temperature: 0.1
    max_tokens: 1000

# Metadata
metadata:
  version: "1.0.0"
  author: "Test Author"
  created_at: "2024-01-01T00:00:00Z"
```

### Configuration Fields

- `name`: Name of the test suite
- `file_path`: Path to the main code file
- `description`: Description of the test suite
- `dependencies`: List of package dependencies
- `referenced_files`: List of local files to import
- `files_to_fix`: List of files that should be fixed if tests fail
- `agent_type`: Type of agent to use (default: "default")
- `auto_fix`: Whether to enable automatic fixing
- `create_pr`: Whether to create pull requests
- `max_retries`: Maximum number of fix attempts
- `base_branch`: Base branch for pull requests
- `pr_strategy`: Strategy for when to create PRs
- `regions`: List of code regions to test
- `steps`: List of test steps
- `evaluation`: Evaluation criteria and settings
- `metadata`: Additional metadata

### Expected Outcomes

You can define expected outcomes for your tests in several ways:

#### 1. Simple Expected Output
```yaml
steps:
  - name: Addition Test
    input:
      method: add
      input: [5, 3]
    expected_output: 8
    description: "Test basic addition functionality"
```

#### 2. Structured Expected Output
```yaml
steps:
  - name: User Creation Test
    input:
      method: create_user
      input: {"name": "John Doe", "email": "john@example.com"}
    expected_output:
      status: "success"
      user_id: "user_123"
      message: "User created successfully"
    description: "Test user creation API response"
```

#### 3. Evaluation Criteria
```yaml
evaluation:
  criteria:
    - "Output should be properly formatted"
    - "Result should be meaningful"
    - "Status should indicate success"
  required_fields:
    - "result"
    - "status"
```

#### 4. Advanced Evaluation Targets
```yaml
evaluation:
  evaluation_targets:
    - name: summary_text
      source: variable
      criteria: "Should include key insights from the data"
      description: "Summary should highlight important patterns"
      weight: 1.0
    - name: return
      source: return
      criteria: "Should be a dictionary with 'status' and 'results' keys"
      description: "Return value should have expected structure"
      weight: 1.0
```

## Multiple Inputs & Outputs

Kaizen supports advanced multiple inputs and multiple outputs evaluation, making it perfect for complex agent workflows and multi-step processes.

### Multiple Inputs

Kaizen supports four types of inputs that can be combined in any configuration:

#### 1. String Inputs
```yaml
steps:
  - name: String Input Test
    input:
      method: process_text
      input:
        - name: user_query
          type: string
          value: "How stable is this compound in ethanol?"
```

#### 2. Dictionary Inputs
```yaml
steps:
  - name: Dictionary Input Test
    input:
      method: analyze_conditions
      input:
        - name: experimental_conditions
          type: dict
          value:
            temperature: 25
            solvent: "ethanol"
            pressure: 1.0
            concentration: 0.1
```

#### 3. Object Inputs (with dynamic imports)
```yaml
steps:
  - name: Object Input Test
    input:
      method: process_feedback
      input:
        - name: chemist_feedback
          type: object
          class_path: "input_types.ChemistFeedback"
          args:
            text: "Too reactive"
            tags: ["solubility", "stability"]
            confidence: 0.9
```

#### 4. Class Object Inputs
```yaml
steps:
  - name: Model Input Test
    input:
      method: predict
      input:
        - name: saved_model
          type: class_object
          pickle_path: "trained_model.pkl"
```

### Multiple Outputs Evaluation

Evaluate multiple outputs from your agents including return values and specific variables:

```yaml
evaluation:
  evaluation_targets:
    - name: summary_text
      source: variable
      criteria: "Should include clarification about the compound's instability"
      description: "The summary text should explain stability concerns"
      weight: 1.0

    - name: recommended_action
      source: variable
      criteria: "Should suggest an experiment or alternative solvent"
      description: "The recommendation should be actionable"
      weight: 1.0

    - name: return
      source: return
      criteria: "Should be a dictionary with 'status' and 'summary' keys"
      description: "The return value should have the expected structure"
      weight: 1.0
```

### Complete Example

Here's a comprehensive example showing multiple inputs and outputs:

```yaml
name: Chemistry Analysis Test
agent_type: dynamic_region
file_path: chemistry_agent.py
description: Test chemistry analysis with multiple input types and output evaluation

evaluation:
  evaluation_targets:
    - name: stability_analysis
      source: variable
      criteria: "Should identify potential stability issues and their causes"
      description: "Analysis should cover chemical stability factors"
      weight: 1.0

    - name: safety_recommendations
      source: variable
      criteria: "Should provide specific safety precautions and handling instructions"
      description: "Recommendations should be practical and safety-focused"
      weight: 1.0

    - name: return
      source: return
      criteria: "Should return a structured response with 'status', 'analysis', and 'recommendations' fields"
      description: "Return value should be well-structured for API consumption"
      weight: 1.0

regions:
  - ChemistryAgent

max_retries: 2

files_to_fix:
  - chemistry_agent.py

steps:
  - name: Complex Chemistry Query
    description: Test handling of mixed input types with multiple outputs
    input:
      file_path: chemistry_agent.py
      method: analyze_compound
      input:
        # String inputs
        - name: user_query
          type: string
          value: "How stable is this compound in ethanol?"
        
        # Dictionary inputs
        - name: experimental_conditions
          type: dict
          value:
            temperature: 298.15
            pressure: 101325
            solvent: "ethanol"
            pH: 7.0
        
        # Object inputs
        - name: chemist_feedback
          type: object
          class_path: "input_types.ChemistFeedback"
          args:
            text: "Too reactive under current conditions"
            tags: ["solubility", "stability", "safety"]
            confidence: 0.95
            source: "lab_analysis"
        
        # Class object inputs
        - name: stability_model
          type: class_object
          pickle_path: "trained_stability_model.pkl"
    
    evaluation:
      type: llm
```

### Agent Implementation Example

To use multiple inputs and outputs, implement your agent like this:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChemistFeedback:
    text: str
    tags: List[str]
    confidence: Optional[float] = None
    source: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'text': self.text,
            'tags': self.tags,
            'confidence': self.confidence,
            'source': self.source
        }

class ChemistryAgent:
    def __init__(self):
        # Variables that will be tracked for evaluation
        self.stability_analysis = ""
        self.safety_recommendations = ""
        self.analysis_results = {}
    
    def analyze_compound(self, *inputs):
        """Analyze compound with multiple inputs."""
        # Process different input types
        user_query = None
        experimental_conditions = None
        chemist_feedback = None
        
        for input_item in inputs:
            if isinstance(input_item, str):
                user_query = input_item
            elif isinstance(input_item, dict):
                experimental_conditions = input_item
            elif hasattr(input_item, 'text'):  # ChemistFeedback object
                chemist_feedback = input_item
        
        # Set variables that will be tracked for evaluation
        self.stability_analysis = "The compound shows moderate instability in ethanol due to its polar nature."
        self.safety_recommendations = "Use appropriate PPE and work in a fume hood. Consider alternative solvents."
        self.analysis_results = {
            "stability_score": 0.3,
            "risk_factors": ["polar solvent", "temperature sensitivity"],
            "recommendations": ["use less polar solvent", "maintain low temperature"]
        }
        
        # Return structured result
        return {
            "status": "completed",
            "analysis": self.stability_analysis,
            "recommendations": self.safety_recommendations,
            "details": self.analysis_results
        }
```

### Input Types Reference

| Type | Description | Example |
|------|-------------|---------|
| `string` | Simple text input | `{"type": "string", "value": "Hello world"}` |
| `dict` | Structured data | `{"type": "dict", "value": {"key": "value"}}` |
| `object` | Dynamic class instantiation | `{"type": "object", "class_path": "module.Class", "args": {...}}` |
| `class_object` | Direct class object | `{"type": "class_object", "pickle_path": "file.pkl"}` |

### Evaluation Sources Reference

| Source | Description | Example |
|--------|-------------|---------|
| `return` | Function's return value | `{"source": "return", "name": "return"}` |
| `variable` | Specific variable tracking | `{"source": "variable", "name": "summary_text"}` |
| `pattern` | Future: wildcard matching | Coming soon |

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
- Inspired by modern AI-powered development tools
- Built with Python, Click, Rich, and Google AI APIs