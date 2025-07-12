# Usage Guide

Learn how to configure and use Kaizen Agent effectively to accelerate your LLM development. This guide covers YAML configuration structure, CLI commands, and advanced features that help you ship reliable AI features faster.

## YAML Configuration Structure

Kaizen Agent uses YAML configuration files to define test suites for your AI agents. This approach eliminates the need for traditional Python test files while providing powerful testing capabilities that help you iterate quickly and build more reliable LLM applications.

### Complete Configuration Example

Here's a comprehensive example that demonstrates all available configuration options:

```yaml
name: Text Analysis Agent Test Suite
agent_type: dynamic_region
file_path: agents/text_analyzer.py
description: |
  Test suite for the TextAnalyzer agent that processes and analyzes text content.
  
  This agent performs sentiment analysis, extracts key information, and provides
  structured analysis results. Tests cover various input types, edge cases, and
  expected output formats to ensure reliable performance.

agent:
  module: agents.text_analyzer
  class: TextAnalyzer
  method: analyze_text

evaluation:
  evaluation_targets:
    - name: sentiment_score
      source: variable
      criteria: "The sentiment_score must be a float between -1.0 and 1.0. Negative values indicate negative sentiment, positive values indicate positive sentiment. The score should accurately reflect the emotional tone of the input text."
      description: "Evaluates the accuracy of sentiment analysis output"
      weight: 0.4
    - name: key_phrases
      source: variable
      criteria: "The key_phrases should be a list of strings containing the most important phrases from the input text"
      description: "Checks if key phrase extraction is working correctly"
      weight: 0.3
    - name: analysis_quality
      source: return
      criteria: "The response should be well-structured, professional, and contain actionable insights"
      description: "Evaluates the overall quality and usefulness of the analysis"
      weight: 0.3

max_retries: 3

files_to_fix:
  - agents/text_analyzer.py
  - agents/prompts.py

referenced_files:
  - agents/prompts.py
  - utils/text_utils.py

steps:
  - name: Positive Review Analysis
    description: "Analyze a positive customer review"
    input:
      file_path: agents/text_analyzer.py
      method: analyze_text
      input: 
        - name: text_content
          type: string
          value: "This product exceeded my expectations! The quality is outstanding and the customer service was excellent. I would definitely recommend it to others."
          
      expected_output: 
        sentiment_score: 0.8
        key_phrases: ["exceeded expectations", "outstanding quality", "excellent customer service"]

  - name: Negative Feedback Analysis
    description: "Analyze negative customer feedback"
    input:
      file_path: agents/text_analyzer.py
      method: analyze_text
      input: 
        - name: text_content
          type: string
          value: "I'm very disappointed with this purchase. The product arrived damaged and the support team was unhelpful."
          
      expected_output: 
        sentiment_score: -0.7
        key_phrases: ["disappointed", "damaged product", "unhelpful support"]

  - name: Object Input Analysis
    description: "Analyze text using a structured user review object"
    input:
      file_path: agents/text_analyzer.py
      method: analyze_review
      input: 
        - name: user_review
          type: object
          class_path: agents.review_processor.UserReview
          args: 
            text: "This product exceeded my expectations! The quality is outstanding."
            rating: 5
            category: "electronics"
            helpful_votes: 12
            verified_purchase: true
        - name: analysis_settings
          type: dict
          value:
            include_sentiment: true
            extract_keywords: true
            detect_emotions: false
          
      expected_output: 
        sentiment_score: 0.9
        key_phrases: ["exceeded expectations", "outstanding quality", "excellent customer service"]
        review_quality: "high"
```

## Configuration Sections Explained

### Basic Information

- **`name`**: A descriptive name for your test suite
- **`agent_type`**: Type of agent testing (e.g., `dynamic_region` for code-based agents)
- **`file_path`**: Path to the main agent file being tested
- **`description`**: Detailed description of what the agent does and what the tests cover

### Agent Configuration

```yaml
agent:
  module: agents.text_analyzer    # Python module path
  class: TextAnalyzer            # Class name to instantiate
  method: analyze_text           # Method to call during testing
```

### Evaluation Criteria

**⚠️ CRITICAL: This section feeds directly into the LLM for automated evaluation. Write clear, specific criteria for best results.**

The `evaluation` section defines how Kaizen's LLM evaluates your agent's performance. Each `evaluation_target` specifies what to check and how to score it.

```yaml
evaluation:
  evaluation_targets:
    - name: sentiment_score       # Name of the output to evaluate
      source: variable            # Source: 'variable' (from agent output) or 'return' (from method return)
      criteria: "Description of what constitutes a good result"
      description: "Additional context about this evaluation target"
      weight: 0.4                 # Relative importance (0.0 to 1.0)
```

#### Key Components

- **`name`**: Must match a field in your agent's output or return value
- **`source`**: 
  - `variable`: Extract from agent's output variables/attributes
  - `return`: Use the method's return value
- **`criteria`**: **Most important** - Instructions for the LLM evaluator
- **`description`**: Additional context to help the LLM understand the evaluation
- **`weight`**: Relative importance (0.0 to 1.0, total should equal 1.0)

#### Writing Effective Criteria

**✅ Good Examples:**

```yaml
- name: sentiment_score
  source: variable
  criteria: "The sentiment_score must be a float between -1.0 and 1.0. Negative values indicate negative sentiment, positive values indicate positive sentiment. The score should accurately reflect the emotional tone of the input text."
  weight: 0.4

- name: response_quality
  source: return
  criteria: "The response should be professional, well-structured, and contain actionable insights. It must be free of grammatical errors and provide specific, relevant information that addresses the user's query directly."
  weight: 0.6
```

**❌ Poor Examples:**

```yaml
- name: result
  source: return
  criteria: "Should be good"  # Too vague
  weight: 1.0

- name: accuracy
  source: variable
  criteria: "Check if it's correct"  # Not specific enough
  weight: 1.0
```

#### Tips for Better LLM Evaluation

1. **Be Specific**: Include exact requirements, ranges, or formats
2. **Provide Context**: Explain what "good" means in your domain
3. **Include Examples**: Reference expected patterns or behaviors
4. **Consider Edge Cases**: Mention how to handle unusual inputs
5. **Use Clear Language**: Avoid ambiguous terms that LLMs might misinterpret

### Testing Configuration

- **`max_retries`**: Number of retry attempts if a test fails
- **`files_to_fix`**: Files that Kaizen can modify to fix issues
- **`referenced_files`**: Additional files for context (not modified)

### Test Steps

Each step defines a test case with:
- **`name`**: Descriptive name for the test
- **`description`**: What this test is checking
- **`input`**: 
  - `file_path`: Path to the agent file
  - `method`: Method to call
  - `input`: List of parameters with name, type, and value

### Input Types Supported

Kaizen supports multiple input types for test parameters:

#### String Input

```yaml
- name: text_content
  type: string
  value: "Your text here"
```

#### Dictionary Input

```yaml
- name: config
  type: dict
  value:
    key1: "value1"
    key2: "value2"
```

#### Object Input

```yaml
- name: user_review
  type: object
  class_path: agents.review_processor.UserReview
  args: 
    text: "This product exceeded my expectations! The quality is outstanding."
    rating: 5
    category: "electronics"
    helpful_votes: 12
    verified_purchase: true
```

The `class_path` specifies the Python class to instantiate, and `args` provides the constructor arguments.

- **`expected_output`**: Expected results for evaluation

## CLI Commands

### Basic Testing Commands

```bash
# Run tests
kaizen test-all --config kaizen.yaml

# With auto-fix
kaizen test-all --config kaizen.yaml --auto-fix

# Create PR with fixes
kaizen test-all --config kaizen.yaml --auto-fix --create-pr

# Save detailed logs
kaizen test-all --config kaizen.yaml --save-logs
```

### Environment Setup Commands

```bash
# Check environment setup
kaizen setup check-env

# Create environment example file
kaizen setup create-env-example
```

### GitHub Integration Commands

```bash
# Test GitHub access
kaizen test-github-access --repo owner/repo-name

# Diagnose GitHub access issues
kaizen diagnose-github-access --repo owner/repo-name
```

### Test Generation Commands

```bash
# Generate additional test cases to reach a total of 10
kaizen augment test.yaml --total 10

# Use enhanced AI model for better generation
kaizen augment test.yaml --total 15 --better-ai

# Show detailed debug information
kaizen augment test.yaml --total 12 --verbose
```

For detailed information about test generation, see our [Test Generation Guide](./test-generation.md).

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--config` | Path to YAML configuration file | `--config kaizen.yaml` |
| `--auto-fix` | Automatically fix issues found during testing | `--auto-fix` |
| `--create-pr` | Create a pull request with fixes (requires GitHub setup) | `--create-pr` |
| `--save-logs` | Save detailed execution logs to `test-logs/` directory | `--save-logs` |
| `--repo` | GitHub repository for PR creation (format: owner/repo-name) | `--repo myuser/myproject` |
| `--total` | Total number of test cases desired for augmentation | `--total 10` |
| `--better-ai` | Use enhanced AI model for improved test generation | `--better-ai` |

## Simple Configuration Template

For quick testing, you can use this minimal template:

```yaml
name: My Agent Test
file_path: my_agent.py
description: "Test my AI agent"

agent:
  module: my_agent
  class: MyAgent
  method: process

evaluation:
  evaluation_targets:
    - name: result
      source: return
      criteria: "The response should be accurate and helpful"
      weight: 1.0

files_to_fix:
  - my_agent.py

steps:
  - name: Basic Test
    input:
      file_path: my_agent.py
      method: process
      input: 
        - name: user_input
          type: string
          value: "Hello, how are you?"
      expected_output: 
        result: "I'm doing well, thank you!"
```

## Best Practices

### 1. Write Clear Evaluation Criteria

The quality of your evaluation criteria directly impacts how well Kaizen can improve your agent. Be specific and comprehensive.

### 2. Test Edge Cases

Include tests for:
- Empty or minimal inputs
- Very long inputs
- Unusual or unexpected inputs
- Boundary conditions

### 3. Use Descriptive Test Names

Good test names help you understand what's being tested:
- ✅ `Professional Email Improvement`
- ✅ `Edge Case - Empty Email`
- ❌ `Test 1`
- ❌ `Basic Test`

### 4. Balance Test Coverage

Include a mix of:
- **Happy path tests** (normal, expected inputs)
- **Edge case tests** (unusual inputs)
- **Error condition tests** (invalid inputs)

### 5. Review Generated Fixes

Always review the fixes Kaizen generates before applying them to production code.

## Advanced Features

### Custom Evaluation Functions

You can define custom evaluation logic for complex scenarios:

```yaml
evaluation:
  evaluation_targets:
    - name: custom_score
      source: custom_function
      function: my_evaluator.evaluate_response
      criteria: "Custom evaluation criteria"
      weight: 0.5
```

### Parallel Testing

For large test suites, you can enable parallel execution:

```yaml
settings:
  parallel: true
  max_workers: 4
```

### Timeout Configuration

Set timeouts for long-running tests:

```yaml
settings:
  timeout: 180  # seconds
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure your agent module can be imported correctly
2. **API Key Issues**: Verify your `GOOGLE_API_KEY` is set and valid
3. **File Path Issues**: Check that all file paths in your YAML are correct
4. **Evaluation Failures**: Review your evaluation criteria for clarity

### Debug Mode

Enable debug mode for more detailed output:

```bash
kaizen test-all --config kaizen.yaml --debug
```

### Log Analysis

Use the log analyzer to understand test failures:

```bash
kaizen analyze-logs test-logs/latest_test.json
```

For more help, see our [FAQ](./faq.md) or join our [Discord community](https://discord.gg/2A5Genuh).