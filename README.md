# Kaizen Agent - AI Debugging Engineer for AI Agents and LLM Applications

[![Python Versions](https://img.shields.io/pypi/pyversions/kaizen.svg)](https://pypi.org/project/kaizen/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Kaizen Agent is an AI debugging engineer that continuously tests, analyzes, and improves your AI agents and LLM applications. It runs multiple tests simultaneously, intelligently analyzes failures, automatically fixes code and prompts, and creates pull requests with improvements - all powered by AI.

## Table of Contents

- [How It Works](#how-it-works)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Examples](#examples)
- [Usage](#usage)
- [Configuration](#configuration)
- [Multiple Inputs & Outputs](#multiple-inputs--outputs)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## How It Works

🎥 **Watch Kaizen Agent in Action:**

<div>
    <a href="https://www.loom.com/share/d3d8a5c344dc4108906d60e5c209962e">
      <p>Kaizen Agent Demo - Watch Video</p>
    </a>
    <a href="https://www.loom.com/share/d3d8a5c344dc4108906d60e5c209962e">
      <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/d3d8a5c344dc4108906d60e5c209962e-54c4b35b3c755f5d-full-play.gif">
    </a>
  </div>

Kaizen Agent acts as an AI debugging engineer that continuously tests, analyzes, and improves your AI agents and LLM applications. Here's how it works at a high level:

![Kaizen Agent Architecture](kaizen_agent_architecture.png)

### 1. Test Execution
- **Parallel Testing**: Runs multiple test cases simultaneously across your AI agents
- **Multiple Input Types**: Supports strings, dictionaries, objects, and inline objects as inputs
- **Dynamic Loading**: Automatically imports dependencies and referenced files

### 2. Failure Analysis
- **Intelligent Detection**: Uses AI to analyze test failures and identify root causes
- **Context Understanding**: Examines code, prompts, and test outputs to understand issues
- **Pattern Recognition**: Identifies common problems in AI agent implementations

### 3. Automated Fixing
- **Code Improvements**: Automatically fixes code issues, bugs, and logic problems
- **Prompt Optimization**: Improves prompts for better AI agent performance
- **Best Practices**: Applies AI development best practices and patterns

### 4. Quality Assurance
- **Multiple Output Evaluation**: Evaluates return values, variables, and complex outputs
- **LLM-based Assessment**: Uses AI to assess the quality and correctness of responses
- **Continuous Improvement**: Iteratively improves until tests pass

### 5. Integration & Deployment
- **Pull Request Creation**: Automatically creates PRs with fixes and improvements
- **Version Control**: Integrates with GitHub for seamless deployment
- **Documentation**: Updates documentation and comments as needed

This workflow ensures your AI agents are robust, reliable, and continuously improving through automated testing and fixing cycles.

## Installation

### From Source

```bash
git clone https://github.com/Kaizen-agent/kaizen-agent.git
cd kaizen-agent
pip install -e ".[dev]"
```

## Environment Setup

Before using Kaizen Agent, you need to set up your environment variables for API access.

### Required Environment Variables

- **`GOOGLE_API_KEY`** (Required): Your Google AI API key for LLM operations
  - Get it from: https://makersuite.google.com/app/apikey

- **`GITHUB_TOKEN`** (Required for PR creation): Your GitHub personal access token
  - Create it at: https://github.com/settings/tokens
  - Required scopes: `repo`, `workflow`

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

3. **Use the built-in setup commands:**
   ```bash
   # Check your environment setup
   kaizen setup check-env
   
   # Create a template .env file
   kaizen setup create-env-example
   
   # Validate environment for CI/CD
   kaizen setup validate-env
   ```

For detailed setup instructions, see the [Environment Setup Guide](docs/environment-setup.md).

## Examples

Kaizen Agent comes with two example agents to help you get started quickly. These examples demonstrate how to test AI agents and LLM applications.

### Example 1: Summarizer Agent

The summarizer agent demonstrates basic text summarization functionality:

1. **Navigate to the example:**
   ```bash
   cd examples/summarizer_agent
   ```

2. **Set up your environment:**
   ```bash
   # Create .env file with your Google API key
   echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
   ```

3. **Run the tests:**
   ```bash
   # From the summarizer_agent directory
   kaizen test-all --config test_config.yaml --auto-fix
   ```

### Example 2: Email Agent

The email agent demonstrates email improvement functionality:

1. **Navigate to the example:**
   ```bash
   cd examples/email_agent
   ```

2. **Set up your environment:**
   ```bash
   # Create .env file with your Google API key
   echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
   ```

3. **Run the tests:**
   ```bash
   # From the email_agent directory
   kaizen test-all --config test_config.yaml --auto-fix
   ```

### Creating Your Own Test Configuration

1. **Navigate to your project directory:**
   ```bash
   cd path/to/your/ai-agent-project
   ```

2. Create a test configuration file (YAML):

```yaml
name: My AI Agent Test Suite
file_path: path/to/your/agent.py
description: "Test suite for my AI agent"

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

3. **Run tests with auto-fix:**
   ```bash
   # From your project directory
   kaizen test-all --config test_config.yaml --auto-fix --create-pr
   ```

## Usage

### Available Commands

```bash
# Run all tests in configuration
kaizen test-all --config <config_file> [options]

# Check environment setup
kaizen setup check-env [--features core github optional]

# Test GitHub access and permissions
kaizen test-github-access --config <config_file> [--repo owner/repo]

# Comprehensive GitHub access diagnostics
kaizen diagnose-github-access --config <config_file> [--repo owner/repo]
```

### Run Tests with Auto-Fix

```bash
# Navigate to the directory containing your config file first
cd path/to/your/project

# Then run the kaizen command
kaizen test-all --config <config_file> [--auto-fix] [--create-pr] [--max-retries <n>] [--base-branch <branch>] [--save-logs] [--verbose]
```

Options:
- `--config`, `-c`: Path to test configuration file (required)
- `--auto-fix`: Enable automatic code fixing
- `--create-pr`: Create a pull request with fixes
- `--max-retries`: Maximum number of fix attempts (default: 1)
- `--base-branch`: Base branch for pull request (default: main)
- `--pr-strategy`: Strategy for when to create PRs (default: ANY_IMPROVEMENT)
- `--test-github-access`: Test GitHub access before running tests
- `--save-logs`: Save detailed test logs in JSON format
- `--verbose`, `-v`: Show detailed debug information

### Environment Setup Commands

```bash
# Check environment status
kaizen setup check-env --features core github

# Create .env.example template
kaizen setup create-env-example

# Validate environment (for CI/CD)
kaizen setup validate-env --features core github
```

### GitHub Access Testing

```bash
# Navigate to the directory containing your config file first
cd path/to/your/project

# Test GitHub access with config file
kaizen test-github-access --config test_config.yaml

# Test specific repository
kaizen test-github-access --repo owner/repo-name --base-branch main

# Comprehensive diagnostics
kaizen diagnose-github-access --repo owner/repo-name
```

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

# Metadata
metadata:
  version: "1.0.0"
  author: "Test Author"
  created_at: "2024-01-01T00:00:00Z"

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

### Defining Code Regions

To test specific parts of your code, you need to define regions using special comment markers. Kaizen Agent will only test the code within these marked regions.

#### Region Markers

Use these comment markers to define testable regions in your Python code:

```python
# kaizen:start:{region_name}
# Your code here - this will be tested
class MyAgent:
    def __init__(self):
        self.name = "My Agent"
    
    def process_data(self, data):
        # This method will be tested
        return {"status": "success", "data": data}
# kaizen:end:{region_name}
```

#### Example: Complete Agent with Regions

```python
import json
from typing import Dict, Any

# kaizen:start:customer_support_agent
class CustomerSupportAgent:
    def __init__(self):
        self.issue_analysis = ""
        self.improvement_recommendations = ""
        self.analysis_results = {}
    
    def analyze_customer_issues(self, *inputs):
        """Analyze customer issues with multiple inputs."""
        # Process different input types
        user_query = None
        customer_data = None
        customer_feedback = None
        
        for input_item in inputs:
            if isinstance(input_item, str):
                user_query = input_item
            elif isinstance(input_item, dict):
                customer_data = input_item
            elif hasattr(input_item, 'text'):
                customer_feedback = input_item
        
        # Set variables that will be tracked for evaluation
        self.issue_analysis = "Customers are experiencing performance issues."
        self.improvement_recommendations = "Implement performance optimization."
        self.analysis_results = {
            "satisfaction_score": 2.5,
            "main_issues": ["performance", "stability"],
            "recommendations": ["optimize code", "add monitoring"]
        }
        
        return {
            "status": "completed",
            "analysis": self.issue_analysis,
            "recommendations": self.improvement_recommendations,
            "details": self.analysis_results
        }
# kaizen:end:customer_support_agent

# This code outside the region won't be tested
def utility_function():
    return "This won't be tested"
```

#### Configuration Reference

In your YAML configuration, reference the region name:

```yaml
# Test regions to execute
regions:
  - "customer_support_agent"  # Matches the region name in your code
```

#### Best Practices

- **Descriptive Names**: Use clear, descriptive region names (e.g., `customer_support_agent`, `data_processor`)
- **Complete Classes**: Include entire classes or functions within a single region
- **Avoid Nesting**: Don't nest regions within other regions
- **Clean Boundaries**: Place markers at logical code boundaries (class/function level)
- **Consistent Naming**: Use the same naming convention across your codebase

#### Multiple Regions

You can define multiple regions in the same file:

```python
# kaizen:start:data_processor
class DataProcessor:
    def process(self, data):
        return {"processed": data}
# kaizen:end:data_processor

# kaizen:start:report_generator
class ReportGenerator:
    def generate(self, data):
        return {"report": data}
# kaizen:end:report_generator
```

Then reference both in your configuration:

```yaml
regions:
  - "data_processor"
  - "report_generator"
```

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

#### 3. Advanced Evaluation Targets
```yaml
evaluation:
  evaluation_targets:
    - name: summary_text
      source: variable
      criteria: "Should include clarification about the compound's instability"
      description: "The summary text should explain stability concerns"
      weight: 1.0
    - name: return
      source: return
      criteria: "Should be a dictionary with 'status' and 'summary' keys"
      description: "The return value should have the expected structure"
      weight: 1.0
```

## Multiple Inputs & Outputs

Kaizen Agent supports advanced multiple inputs and multiple outputs evaluation, making it perfect for complex agent workflows and multi-step processes.

### Multiple Inputs

Kaizen Agent supports four types of inputs that can be combined in any configuration:

#### 1. String Inputs
```yaml
steps:
  - name: String Input Test
    input:
      method: process_text
      input:
        - name: user_query
          type: string
          value: "What are the main issues customers are reporting?"
```

#### 2. Dictionary Inputs
```yaml
steps:
  - name: Dictionary Input Test
    input:
      method: analyze_conditions
      input:
        - name: customer_data
          type: dict
          value:
            customer_id: "CUST123"
            product: "Premium Widget"
            subscription_tier: "Enterprise"
            support_tickets: 3
```

#### 3. Object Inputs (with dynamic imports)
```yaml
steps:
  - name: Object Input Test
    input:
      method: process_feedback
      input:
        - name: customer_feedback
          type: object
          class_path: "input_types.CustomerFeedback"
          args:
            text: "Product is too slow"
            tags: ["performance", "speed"]
            priority: "high"
```

#### 4. Inline Object Inputs (recommended)
```yaml
steps:
  - name: Inline Object Test
    input:
      method: process_feedback
      input:
        - name: customer_feedback
          type: inline_object
          class_path: "input_types.CustomerFeedback"
          attributes:
            text: "Excellent customer service experience"
            tags: ["service", "satisfaction"]
            priority: "low"
            source: "survey_response"
```

### Multiple Outputs Evaluation

Evaluate multiple outputs from your agents including return values and specific variables:

```yaml
evaluation:
  evaluation_targets:
    - name: issue_analysis
      source: variable
      criteria: "Should identify the root cause of customer complaints"
      description: "The analysis should explain why customers are dissatisfied"
      weight: 1.0

    - name: recommended_action
      source: variable
      criteria: "Should suggest specific improvements or solutions"
      description: "The recommendation should be actionable and specific"
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
name: Customer Support Analysis Test
agent_type: dynamic_region
file_path: support_agent.py
description: Test customer support analysis with multiple input types and output evaluation

evaluation:
  evaluation_targets:
    - name: issue_analysis
      source: variable
      criteria: "Should identify the main customer pain points and their causes"
      description: "Analysis should cover customer satisfaction factors"
      weight: 1.0

    - name: improvement_recommendations
      source: variable
      criteria: "Should provide specific actionable recommendations for improvement"
      description: "Recommendations should be practical and business-focused"
      weight: 1.0

    - name: return
      source: return
      criteria: "Should return a structured response with 'status', 'analysis', and 'recommendations' fields"
      description: "Return value should be well-structured for API consumption"
      weight: 1.0

regions:
  - SupportAgent

max_retries: 2

files_to_fix:
  - support_agent.py

steps:
  - name: Complex Customer Query
    description: Test handling of mixed input types with multiple outputs
    input:
      file_path: support_agent.py
      method: analyze_customer_issues
      input:
        # String inputs
        - name: user_query
          type: string
          value: "What are the main issues customers are reporting?"
        
        # Dictionary inputs
        - name: customer_data
          type: dict
          value:
            customer_id: "CUST123"
            product: "Premium Widget"
            subscription_tier: "Enterprise"
            support_tickets: 3
            satisfaction_score: 2.5
        
        # Inline object inputs (recommended)
        - name: customer_feedback
          type: inline_object
          class_path: "input_types.CustomerFeedback"
          attributes:
            text: "Product is too slow and crashes frequently"
            tags: ["performance", "stability", "frustration"]
            priority: "high"
            source: "support_ticket"
    
    evaluation:
      type: llm
```

### Agent Implementation Example

To use multiple inputs and outputs, implement your agent like this:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CustomerFeedback:
    text: str
    tags: List[str]
    priority: Optional[str] = None
    source: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'text': self.text,
            'tags': self.tags,
            'priority': self.priority,
            'source': self.source
        }

class SupportAgent:
    def __init__(self):
        # Variables that will be tracked for evaluation
        self.issue_analysis = ""
        self.improvement_recommendations = ""
        self.analysis_results = {}
    
    def analyze_customer_issues(self, *inputs):
        """Analyze customer issues with multiple inputs."""
        # Process different input types
        user_query = None
        customer_data = None
        customer_feedback = None
        
        for input_item in inputs:
            if isinstance(input_item, str):
                user_query = input_item
            elif isinstance(input_item, dict):
                customer_data = input_item
            elif hasattr(input_item, 'text'):  # CustomerFeedback object
                customer_feedback = input_item
        
        # Set variables that will be tracked for evaluation
        self.issue_analysis = "Customers are experiencing performance issues and system crashes, leading to low satisfaction scores."
        self.improvement_recommendations = "Implement performance optimization and add crash recovery mechanisms. Consider upgrading server infrastructure."
        self.analysis_results = {
            "satisfaction_score": 2.5,
            "main_issues": ["performance", "stability"],
            "recommendations": ["optimize code", "add monitoring", "improve error handling"]
        }
        
        # Return structured result
        return {
            "status": "completed",
            "analysis": self.issue_analysis,
            "recommendations": self.improvement_recommendations,
            "details": self.analysis_results
        }
```

### Input Types Reference

| Type | Description | Example |
|------|-------------|---------|
| `string` | Simple text input | `{"type": "string", "value": "Hello world"}` |
| `dict` | Structured data | `{"type": "dict", "value": {"key": "value"}}` |
| `object` | Dynamic class instantiation | `{"type": "object", "class_path": "module.Class", "args": {...}}` |
| `inline_object` | Direct object specification | `{"type": "inline_object", "class_path": "module.Class", "attributes": {...}}` |

### Evaluation Sources Reference

| Source | Description | Example |
|--------|-------------|---------|
| `return` | Function's return value | `{"source": "return", "name": "return"}` |
| `variable` | Specific variable tracking | `{"source": "variable", "name": "summary_text"}` |

## Save Logs Feature

The `--save-logs` option allows you to save detailed test execution logs in JSON format for later analysis and debugging.

### Usage

```bash
# Navigate to the directory containing your config file first
cd path/to/your/project

# Run tests with detailed logging
kaizen test-all --config test_config.yaml --save-logs

# Combine with other options
kaizen test-all --config test_config.yaml --auto-fix --create-pr --save-logs
```

### Output Files

When `--save-logs` is enabled, two files are created in the `test-logs/` directory:

1. **Detailed Logs File**: `{test_name}_{timestamp}_detailed_logs.json`
   - Complete test execution data
   - Individual test case results with inputs/outputs
   - LLM evaluation results and scores
   - Auto-fix attempts and their outcomes
   - Error details and stack traces
   - Execution timing information

2. **Summary File**: `{test_name}_{timestamp}_summary.json`
   - Quick reference with key metrics
   - Test name and status
   - Execution timestamps
   - Error messages
   - Overall status summary

## Development

### Prerequisites

- Python 3.8+
- pip
- git

### Setup Development Environment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kaizen-agent.git
cd kaizen-agent
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
- 🐛 [Issue Tracker](https://github.com/yourusername/kaizen-agent/issues)
- 📧 [Email Support](mailto:support@kaizen.dev)

## Acknowledgments

- Thanks to all our contributors
- Inspired by modern AI-powered development tools
- Built with Python, Click, Rich, and Google AI APIs