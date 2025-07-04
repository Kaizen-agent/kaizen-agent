# Frequently Asked Questions

Find answers to common questions about Kaizen Agent, troubleshooting tips, and guidance on when and how to use the tool effectively.

## General Questions

### What is Kaizen Agent?

Kaizen Agent is your AI development teammate that levels up your LLM applications. Instead of manually testing and iterating on your agents, you define your test inputs and evaluation criteria in YAML, and Kaizen handles the rest.

### When should I use Kaizen Agent?

**Kaizen Agent is most valuable when you want to ship reliable LLM features faster.**

Perfect use cases:
- **🚀 Rapid Development**: Test and improve agents during development cycles
- **⚡ Pre-Deployment Validation**: Ensure your agent works reliably before going live
- **🔧 Continuous Improvement**: Continuously enhance prompts and code based on test results
- **🛡️ Quality Assurance**: Maintain high standards as your agent evolves
- **📈 Performance Optimization**: Level up your agent's capabilities systematically

### When should I NOT use Kaizen Agent?

- **Production environments** - Kaizen is for development/testing, not live systems
- **Simple, stable agents** - If your agent is already working perfectly, you might not need it
- **Non-AI applications** - Kaizen is specifically designed for AI agents and LLM applications

### Do I need to write test code?

**No!** Kaizen Agent uses YAML configuration instead of traditional test files:

- **❌ Traditional approach**: Write test files with `unittest`, `pytest`, or `jest`
- **✅ Kaizen approach**: Define tests in YAML - no test code needed!

## Installation & Setup

### What are the system requirements?

- **Python 3.8+** (Python 3.9+ recommended for best performance)
- **Google API Key** for Gemini models
- Basic familiarity with Python or TypeScript

### How do I get a Google API key?

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key and set it as `GOOGLE_API_KEY` in your environment

### How do I set up environment variables?

**Option 1: Using .env file (Recommended)**

```bash
# Create .env file
cat > .env << EOF
GOOGLE_API_KEY=your_api_key_here
GITHUB_TOKEN=ghp_your_github_token_here
EOF
```

**Option 2: Set directly in shell**

```bash
export GOOGLE_API_KEY="your_api_key_here"
export GITHUB_TOKEN="ghp_your_github_token_here"
```

**Option 3: Using Kaizen commands**

```bash
# Create environment example file
kaizen setup create-env-example

# Check environment setup
kaizen setup check-env
```

## Configuration

### How do I write effective evaluation criteria?

**⚠️ CRITICAL: This section feeds directly into the LLM for automated evaluation. Write clear, specific criteria for best results.**

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

### What input types does Kaizen support?

Kaizen supports multiple input types:

**String Input:**
```yaml
- name: text_content
  type: string
  value: "Your text here"
```

**Dictionary Input:**
```yaml
- name: config
  type: dict
  value:
    key1: "value1"
    key2: "value2"
```

**Object Input:**
```yaml
- name: user_review
  type: object
  class_path: agents.review_processor.UserReview
  args: 
    text: "This product exceeded my expectations!"
    rating: 5
    category: "electronics"
```

### How do I test edge cases?

Include tests for:
- **Empty or minimal inputs**
- **Very long inputs**
- **Unusual or unexpected inputs**
- **Boundary conditions**

Example edge case tests:

```yaml
steps:
  - name: Normal Input
    input:
      input: "Hello, how are you?"
  
  - name: Edge Case - Empty Input
    input:
      input: ""
  
  - name: Edge Case - Very Long Input
    input:
      input: "This is a very long input that might cause issues..."
  
  - name: Edge Case - Special Characters
    input:
      input: "Test with special chars: !@#$%^&*()"
```

## Troubleshooting

### Common Error: "Module not found"

**Problem**: Kaizen can't import your agent module.

**Solutions**:
1. **Check file paths**: Ensure your YAML `file_path` matches the actual file location
2. **Verify module structure**: Make sure your Python module can be imported correctly
3. **Check working directory**: Run Kaizen from the correct directory
4. **Test import manually**: Try `python -c "import your_module"` to verify

### Common Error: "API key not found"

**Problem**: Kaizen can't find your Google API key.

**Solutions**:
1. **Check environment variable**: Ensure `GOOGLE_API_KEY` is set
2. **Verify .env file**: Make sure it's in the correct location
3. **Test manually**: Try `echo $GOOGLE_API_KEY` to verify it's set
4. **Use setup command**: Run `kaizen setup check-env` to diagnose

### Common Error: "Evaluation failed"

**Problem**: The LLM evaluator can't understand your evaluation criteria.

**Solutions**:
1. **Make criteria more specific**: Include exact requirements, ranges, or formats
2. **Provide context**: Explain what "good" means in your domain
3. **Include examples**: Reference expected patterns or behaviors
4. **Use clear language**: Avoid ambiguous terms that LLMs might misinterpret

### Common Error: "GitHub access denied"

**Problem**: Can't create pull requests or access GitHub.

**Solutions**:
1. **Check token permissions**: Ensure your GitHub token has the `repo` scope
2. **Verify repository access**: Make sure you have write access to the repository
3. **Test GitHub access**: Run `kaizen test-github-access --repo owner/repo-name`
4. **Check repository format**: Use `owner/repo-name` format (e.g., `myuser/myproject`)

### Tests are taking too long

**Problem**: Tests are running slowly or timing out.

**Solutions**:
1. **Set timeout**: Add `timeout: 180` to your YAML settings
2. **Reduce test complexity**: Simplify evaluation criteria
3. **Use parallel testing**: Enable `parallel: true` in settings
4. **Check API limits**: Ensure you're not hitting rate limits

### Generated fixes don't make sense

**Problem**: Kaizen's automatic fixes seem incorrect or inappropriate.

**Solutions**:
1. **Review evaluation criteria**: Make sure they're clear and specific
2. **Check test inputs**: Ensure test cases are realistic
3. **Review before applying**: Always review fixes before merging
4. **Adjust weights**: Modify evaluation target weights to focus on priorities

## Performance & Optimization

### How can I speed up my tests?

1. **Use parallel testing**:
   ```yaml
   settings:
     parallel: true
     max_workers: 4
   ```

2. **Set appropriate timeouts**:
   ```yaml
   settings:
     timeout: 180  # seconds
   ```

3. **Optimize evaluation criteria**: Make them more specific and concise
4. **Reduce test complexity**: Focus on the most important aspects

### How do I handle rate limits?

1. **Add delays between requests**:
   ```yaml
   settings:
     request_delay: 1  # seconds between requests
   ```

2. **Use retry logic**:
   ```yaml
   max_retries: 3
   ```

3. **Monitor API usage**: Check your Google AI Studio dashboard
4. **Consider API quotas**: Upgrade your plan if needed

## Best Practices

### How should I structure my test configuration?

1. **Use descriptive names**: `Professional Email Improvement` vs `Test 1`
2. **Balance test coverage**: Mix happy path and edge case tests
3. **Write clear evaluation criteria**: Be specific about what constitutes success
4. **Include realistic inputs**: Use test data that reflects real usage
5. **Review generated fixes**: Always check before applying

### How do I maintain test quality over time?

1. **Regularly update evaluation criteria** based on new requirements
2. **Add new test cases** as you discover edge cases
3. **Review and refine prompts** based on test results
4. **Monitor performance metrics** and adjust weights accordingly
5. **Keep test data current** with your application's evolution

### How do I collaborate with team members?

1. **Share YAML configurations** in version control
2. **Use consistent naming conventions** for tests and evaluations
3. **Document evaluation criteria** so others understand the standards
4. **Review pull requests** created by Kaizen before merging
5. **Set up CI/CD integration** for automated testing

## Advanced Topics

### Can I use custom evaluation functions?

Yes, you can define custom evaluation logic:

```yaml
evaluation:
  evaluation_targets:
    - name: custom_score
      source: custom_function
      function: my_evaluator.evaluate_response
      criteria: "Custom evaluation criteria"
      weight: 0.5
```

### How do I integrate with CI/CD?

You can integrate Kaizen Agent with GitHub Actions:

```yaml
name: Kaizen Agent Testing

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install Kaizen Agent
        run: pip install kaizen-agent
      - name: Run Kaizen tests
        run: kaizen test-all --config kaizen.yaml --auto-fix --create-pr --repo ${{ github.repository }}
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### How do I debug test failures?

1. **Enable debug mode**:
   ```bash
   kaizen test-all --config kaizen.yaml --debug
   ```

2. **Save detailed logs**:
   ```bash
   kaizen test-all --config kaizen.yaml --save-logs
   ```

3. **Analyze logs**:
   ```bash
   kaizen analyze-logs test-logs/latest_test.json
   ```

4. **Check the logs directory** for detailed execution information

## Getting Help

### Where can I get more help?

1. **Discord Community**: Join our [Discord server](https://discord.gg/2A5Genuh) for real-time support
2. **GitHub Issues**: Report bugs and request features on [GitHub](https://github.com/Kaizen-agent/kaizen-agent)
3. **Documentation**: Check the other guides in this documentation
4. **Examples**: Review the [Examples](./examples.md) page for working configurations

### How do I report a bug?

1. **Check existing issues** on GitHub first
2. **Create a new issue** with:
   - Clear description of the problem
   - Steps to reproduce
   - Your YAML configuration (with sensitive data removed)
   - Error messages and logs
   - Environment details (Python version, OS, etc.)

### How can I contribute?

1. **Star the repository** on GitHub
2. **Share examples** of your configurations
3. **Report bugs** and request features
4. **Join the Discord community** to help other users
5. **Submit pull requests** for improvements

For more help, join our [Discord community](https://discord.gg/2A5Genuh) or check out our [GitHub repository](https://github.com/Kaizen-agent/kaizen-agent). 