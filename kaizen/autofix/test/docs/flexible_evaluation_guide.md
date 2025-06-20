# Flexible Output Evaluation Guide

This guide explains how to use the new flexible output evaluation system in Kaizen, which allows you to evaluate multiple outputs from your agents including return values, specific variables, and variable patterns.

## Overview

The flexible evaluation system enables you to:

- **Evaluate return values**: Check the function's return value against specific criteria
- **Track specific variables**: Monitor and evaluate specific variable names during execution
- **Multi-point evaluation**: Evaluate multiple outputs from a single test execution
- **Granular feedback**: Get detailed feedback on each evaluation target

## YAML Configuration Format

### Basic Structure

```yaml
name: "Your Test Name"
agent_type: dynamic_region
file_path: your_agent.py
description: "Description of your test"

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

regions:
  - your_agent_class

max_retries: 2
files_to_fix:
  - your_agent.py

steps:
  - name: Test Step
    description: Description of the test step
    input:
      file_path: your_agent.py
      method: your_method_name
      input: "Your test input"
    evaluation:
      type: llm
```

### Evaluation Target Configuration

Each evaluation target has the following fields:

#### Required Fields

- **`name`**: The name of the target (variable name or "return")
- **`source`**: The source type:
  - `"return"`: Evaluate the function's return value
  - `"variable"`: Track and evaluate a specific variable name
  - `"pattern"`: Future feature for wildcard matching
- **`criteria`**: The evaluation criteria for this target

#### Optional Fields

- **`description`**: Human-readable description of what this target should contain
- **`weight`**: Weight for this target in overall evaluation (default: 1.0)

## Examples

### Example 1: Chemistry Agent

```yaml
name: "Chemistry Agent Test"
agent_type: dynamic_region
file_path: chemistry_agent.py

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

steps:
  - name: Compound Analysis
    input:
      file_path: chemistry_agent.py
      method: analyze_compound
      input: "Analyze the stability of compound X in ethanol"
    evaluation:
      type: llm
```

### Example 2: Email Agent

```yaml
name: "Email Agent Test"
agent_type: dynamic_region
file_path: email_agent.py

evaluation:
  evaluation_targets:
    - name: email_content
      source: variable
      criteria: "Should be professional, clear, and grammatically correct"
      description: "Email content should be well-written"
      weight: 1.0

    - name: tone_analysis
      source: variable
      criteria: "Should maintain appropriate professional tone"
      description: "Tone should be suitable for business communication"
      weight: 0.8

    - name: return
      source: return
      criteria: "Should return a dictionary with 'status' and 'email' fields"
      description: "Return structure should be consistent"
      weight: 1.0

regions:
  - EmailAgent

steps:
  - name: Email Improvement
    input:
      file_path: email_agent.py
      method: improve_email
      input: "Improve this email: Dear John, I want to meet tomorrow. Thanks, Jane"
    evaluation:
      type: llm
```

### Example 3: Data Analysis Agent

```yaml
name: "Data Analysis Agent Test"
agent_type: dynamic_region
file_path: data_agent.py

evaluation:
  evaluation_targets:
    - name: data_summary
      source: variable
      criteria: "Should provide key statistical insights and trends"
      description: "Summary should highlight important data patterns"
      weight: 1.0

    - name: visualization_suggestions
      source: variable
      criteria: "Should suggest appropriate chart types and visualizations"
      description: "Suggestions should be relevant to the data type"
      weight: 0.7

    - name: insights
      source: variable
      criteria: "Should identify actionable insights and recommendations"
      description: "Insights should be business-relevant and actionable"
      weight: 1.0

    - name: return
      source: return
      criteria: "Should return analysis results in JSON format with 'summary', 'insights', and 'recommendations'"
      description: "Return should be structured for further processing"
      weight: 1.0

regions:
  - DataAnalysisAgent

steps:
  - name: Dataset Analysis
    input:
      file_path: data_agent.py
      method: analyze_dataset
      input: "Analyze this sales data and provide insights"
    evaluation:
      type: llm
```

## Implementation in Your Agent

To use variable tracking, your agent should set variables that will be tracked:

```python
class YourAgent:
    def __init__(self):
        self.summary_text = ""
        self.recommendations = ""
        self.analysis_results = {}
    
    def your_method(self, input_data):
        # Set variables that will be tracked
        self.summary_text = "Your summary text here"
        self.recommendations = "Your recommendations here"
        self.analysis_results = {"key": "value"}
        
        # Return the main result
        return {
            "status": "completed",
            "summary": self.summary_text,
            "recommendations": self.recommendations
        }
```

## How It Works

1. **Variable Tracking**: When you specify `source: variable`, the system tracks assignments to that variable name during execution
2. **Return Value Tracking**: When you specify `source: return`, the system captures the function's return value
3. **Multi-Target Evaluation**: The LLM evaluates each target based on its specific criteria
4. **Comprehensive Feedback**: You get detailed feedback for each target plus an overall evaluation

## LLM Evaluation Response

The LLM provides evaluation in this format:

```json
{
  "status": "passed",
  "evaluation": "Overall evaluation of all targets",
  "reasoning": "Explanation of the overall decision",
  "confidence": 0.9,
  "target_evaluations": {
    "summary_text": {
      "status": "passed",
      "evaluation": "Summary text meets criteria",
      "reasoning": "Contains required information"
    },
    "recommended_action": {
      "status": "passed",
      "evaluation": "Recommendations are actionable",
      "reasoning": "Provides specific next steps"
    },
    "return": {
      "status": "passed",
      "evaluation": "Return structure is correct",
      "reasoning": "Contains all required fields"
    }
  }
}
```

## Best Practices

1. **Be Specific**: Write clear, specific criteria for each target
2. **Use Descriptive Names**: Choose meaningful variable names that reflect their purpose
3. **Balance Weights**: Use weights to prioritize more important targets
4. **Test Incrementally**: Start with simple targets and add complexity gradually
5. **Document Expectations**: Use descriptions to clarify what each target should contain

## Migration from Legacy Format

If you're migrating from the legacy evaluation format:

**Before:**
```yaml
evaluation:
  criteria:
    - "Output should be professional"
    - "Should include recommendations"
```

**After:**
```yaml
evaluation:
  evaluation_targets:
    - name: return
      source: return
      criteria: "Output should be professional and include recommendations"
      description: "Overall output quality and completeness"
```

## Troubleshooting

### Common Issues

1. **Variable Not Found**: Ensure the variable name matches exactly what's in your code
2. **Tracking Not Working**: Make sure the variable is assigned during execution
3. **LLM Evaluation Errors**: Check that criteria are clear and specific

### Debug Tips

1. Check the logs for variable tracking information
2. Verify variable names match between code and configuration
3. Test with simple criteria first
4. Use the example configurations as templates

## Future Features

- **Pattern Matching**: Support for wildcard patterns like `*_summary`
- **Conditional Evaluation**: Evaluate targets based on conditions
- **Custom Evaluators**: Support for custom evaluation functions
- **Performance Metrics**: Track evaluation performance and timing 