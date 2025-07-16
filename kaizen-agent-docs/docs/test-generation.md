# Test Generation Guide

Learn how to use Kaizen Agent's test generation feature to automatically create additional test cases for your AI agents. This feature uses Gemini AI to analyze your existing test cases and generate new ones that maintain the same structure and quality.

## Overview

The `kaizen augment` command helps you expand your test coverage by generating additional test cases based on your existing YAML configuration. It analyzes your current test structure and uses AI to create new test cases that follow the same patterns and cover different scenarios.

## Basic Usage

```bash
# Generate additional test cases to reach a total of 10
kaizen augment test.yaml --total 10

# Use enhanced AI model for better generation
kaizen augment test.yaml --total 15 --better-ai

# Show detailed debug information
kaizen augment test.yaml --total 12 --verbose
```

## Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `config_path` | Path to existing YAML configuration file | `test.yaml` |
| `--total` | Total number of test cases desired (original + new) | `--total 10` |
| `--better-ai` | Use Gemini 2.5 Pro for improved test generation | `--better-ai` |
| `--verbose` | Show detailed debug information | `--verbose` |

## How It Works

1. **Analysis Phase**: The command analyzes your existing test cases to understand:
   - Test structure and field patterns
   - Input parameter types and names
   - Expected output patterns
   - Agent purpose and functionality

2. **Generation Phase**: Using Gemini AI, it generates new test cases that:
   - Follow the same YAML structure as your existing tests
   - Cover different scenarios and edge cases
   - Maintain consistent input/output patterns
   - Test various aspects of your agent's functionality

3. **Output**: Creates a new file with the `.augmented.yaml` suffix containing both original and new test cases.

## Example Workflow

### Step 1: Start with a Basic Configuration

```yaml
name: Email Improvement Agent Test
file_path: agents/email_agent.py
description: "Test email improvement functionality"

agent:
  module: agents.email_agent
  class: EmailAgent
  method: improve_email

evaluation:
  evaluation_targets:
    - name: improved_email
      source: return
      criteria: "The response should be a well-written, professional email that improves upon the original"
      weight: 1.0

files_to_fix:
  - agents/email_agent.py

steps:
  - name: Professional Email Improvement
    description: "Improve a casual email to professional tone"
    input:
      file_path: agents/email_agent.py
      method: improve_email
      input: 
        - name: email_content
          type: string
          value: "Hey, just wanted to check if you got my email about the meeting tomorrow."
      expected_output: 
        improved_email: "Dear [Name], I hope this email finds you well. I wanted to follow up regarding my previous email about tomorrow's meeting. Please let me know if you have received it and if you have any questions. Best regards, [Your name]"
```

### Step 2: Generate Additional Test Cases

```bash
kaizen augment email_test.yaml --total 8 --better-ai
```

### Step 3: Review Generated Tests

The command will create `email_test.augmented.yaml` with additional test cases like:

```yaml
# ... existing configuration ...

steps:
  # ... original test cases ...
  
  - name: Formal Complaint Email
    description: "Transform an informal complaint into a formal business email"
    input:
      file_path: agents/email_agent.py
      method: improve_email
      input: 
        - name: email_content
          type: string
          value: "This service is terrible and I want my money back immediately!"
      expected_output: 
        improved_email: "Dear Customer Service Team, I am writing to express my concerns regarding the service I recently received..."

  - name: Meeting Request Email
    description: "Improve a brief meeting request to be more detailed and professional"
    input:
      file_path: agents/email_agent.py
      method: improve_email
      input: 
        - name: email_content
          type: string
          value: "Can we meet next week to discuss the project?"
      expected_output: 
        improved_email: "Dear [Name], I hope this email finds you well. I would like to schedule a meeting with you next week to discuss the ongoing project..."

  - name: Thank You Email Enhancement
    description: "Enhance a simple thank you message"
    input:
      file_path: agents/email_agent.py
      method: improve_email
      input: 
        - name: email_content
          type: string
          value: "Thanks for your help with the project."
      expected_output: 
        improved_email: "Dear [Name], I wanted to take a moment to express my sincere gratitude for your invaluable assistance with the project..."
```

## Best Practices

### 1. Start with Quality Base Tests

The quality of generated tests depends on your existing test cases. Ensure your base tests:
- Have clear, descriptive names
- Cover different scenarios
- Include realistic input values
- Have well-defined expected outputs

### 2. Use the `--better-ai` Flag for Complex Agents

For agents with complex functionality or multiple input types, use the enhanced AI model:

```bash
kaizen augment complex_agent.yaml --total 15 --better-ai
```

### 3. Review Generated Tests

Always review the generated test cases before using them:
- Check that input values are realistic
- Verify expected outputs are appropriate
- Ensure test names are descriptive
- Confirm the tests cover meaningful scenarios

### 4. Iterate and Refine

Use the generated tests as a starting point:
- Modify test cases as needed
- Add specific edge cases
- Customize expected outputs
- Remove tests that don't fit your use case

## Advanced Usage

### Generating Tests for Different Agent Types

The command automatically detects your agent's purpose and generates appropriate tests:

**Evaluation Agents:**
```bash
# Generates tests with feedback, ratings, and evaluation criteria
kaizen augment evaluator.yaml --total 12
```

**Summarization Agents:**
```bash
# Generates tests with various text lengths and content types
kaizen augment summarizer.yaml --total 10
```

**Question Answering Agents:**
```bash
# Generates tests with different question types and complexity
kaizen augment qa_agent.yaml --total 15
```

### Using Verbose Mode for Debugging

When troubleshooting generation issues:

```bash
kaizen augment test.yaml --total 8 --verbose
```

This will show:
- Analysis of existing test structure
- Agent context extraction
- Generation prompts and responses
- Validation of generated YAML

## Troubleshooting

### Common Issues

1. **Empty or Invalid YAML File**
   ```
   Error: Empty or invalid YAML file
   ```
   **Solution**: Ensure your YAML file has valid structure and contains test cases.

2. **No Test Cases Found**
   ```
   Error: No 'steps' section found in YAML file
   ```
   **Solution**: Make sure your YAML file has a `steps` section with test cases.

3. **Invalid Test Structure**
   ```
   Error: Invalid test structure: Test case 0 missing fields: ['name']
   ```
   **Solution**: Ensure all test cases follow the same structure with required fields.

4. **API Key Issues**
   ```
   Error: GOOGLE_API_KEY environment variable not set
   ```
   **Solution**: Set your Google API key:
   ```bash
   export GOOGLE_API_KEY=your_api_key_here
   ```

### Generation Quality Issues

If generated tests don't meet your expectations:

1. **Improve Base Tests**: Add more diverse and well-structured test cases to your original file
2. **Use Better AI**: Try the `--better-ai` flag for more sophisticated generation
3. **Provide Context**: Ensure your YAML includes a clear description of the agent's purpose
4. **Review and Edit**: Manually refine generated tests to match your specific requirements

## Integration with Testing Workflow

### Complete Workflow Example

```bash
# 1. Create initial test configuration
# (Create your YAML file with 2-3 test cases)

# 2. Generate additional test cases
kaizen augment my_agent.yaml --total 10 --better-ai

# 3. Review and edit the augmented file
# (Manually review and modify test cases as needed)

# 4. Run tests with the expanded configuration
kaizen test-all --config my_agent.augmented.yaml --auto-fix

# 5. Save detailed logs for analysis
kaizen test-all --config my_agent.augmented.yaml --save-logs
```

### Continuous Improvement

Use test generation as part of your iterative development process:

1. **Start Small**: Begin with 2-3 well-crafted test cases
2. **Generate More**: Use augment to expand test coverage
3. **Run Tests**: Execute tests and identify issues
4. **Fix Issues**: Use auto-fix to resolve problems
5. **Refine Tests**: Update test cases based on results
6. **Repeat**: Generate more tests for uncovered scenarios

## Tips for Better Generation

### 1. Clear Agent Description

Include a detailed description in your YAML:

```yaml
description: |
  This agent analyzes customer feedback and provides sentiment analysis,
  key phrase extraction, and actionable insights. It handles various
  feedback types including reviews, complaints, and suggestions.
```

### 2. Diverse Input Types

Include tests with different input types to guide generation:

```yaml
steps:
  - name: Short Review
    input:
      input: 
        - name: feedback
          type: string
          value: "Great product!"
  
  - name: Detailed Complaint
    input:
      input: 
        - name: feedback
          type: string
          value: "I'm very disappointed with the quality and customer service..."
```

### 3. Realistic Expected Outputs

Provide realistic expected outputs to guide the AI:

```yaml
expected_output: 
  sentiment_score: 0.8
  key_phrases: ["great product", "excellent quality"]
  insights: "Positive feedback highlighting product quality"
```

### 4. Real-World Example: Email Agent Test Generation

Here's an example of a YAML configuration file that was enhanced by the Kaizen Agent, showing how it can generate diverse test cases covering various scenarios:

```yaml
name: Email Agent
agent_type: dynamic_region
file_path: email_agent.py
description: "An agent that improves an email draft by making it more professional,
  clear, and effective."
framework: llamaindex
agent:
  module: email_agent
  class: EmailAgent
  method: improve_email
evaluation:
  evaluation_targets:
    - name: improved_email
      source: return
      criteria: The improved_email must be a string that is easy to understand 
        and follow.
      description: Evaluates the accuracy of the improved email
      weight: 0.5
    - name: formatted_email
      source: return
      criteria: The improved_email must be a string that is formatted correctly 
        and contains only the improved email no other text.
      description: Checks if the improved email is formatted correctly
      weight: 0.5
max_retries: 3
files_to_fix:
  - email_agent.py
steps:
  - name: Email Draft improvement
    input:
      input:
        - name: email_draft
          type: string
          value: Hey, can you send me the report?
  - name: Edge Case
    input:
      input:
        - name: email_draft
          type: string
          value: test
  - name: Complex Multi-Point Request
    input:
      input:
        - name: email_draft
          type: string
          value: hey team, just a reminder about the meeting tomorrow. i need 
            the slides from marketing, the sales figures from john, and can 
            someone check if the projector is working? also, i think we should 
            push the deadline for the Q3 report back a week. let me know.
  - name: Negative Tone Neutralization
    input:
      input:
        - name: email_draft
          type: string
          value: I've been waiting for the updated designs for 3 days. This is 
            unacceptable and is holding up the entire project. Where are they? I
            need them NOW.
  - name: Empty String Input
    input:
      input:
        - name: email_draft
          type: string
          value: ''
```

This example demonstrates how the Kaizen Agent can generate test cases that cover:
- **Basic functionality** (Email Draft improvement)
- **Edge cases** (minimal input like "test")
- **Complex scenarios** (multi-point requests with multiple requirements)
- **Tone transformation** (converting negative/angry tone to professional)
- **Boundary conditions** (empty string input)

The agent automatically identified these different test scenarios based on the original configuration and generated appropriate test cases that maintain the same structure while covering diverse use cases.

## Limitations

- **AI Dependency**: Generation quality depends on the AI model's understanding
- **Context Sensitivity**: Results may vary based on test complexity
- **Manual Review Required**: Always review generated tests before use
- **API Costs**: Uses Google's Gemini API (costs apply based on usage)

For more help with test generation, see our [FAQ](./faq.md) or join our [Discord community](https://discord.gg/2A5Genuh). 