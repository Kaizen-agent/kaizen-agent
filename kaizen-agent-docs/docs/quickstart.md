# Quick Start Guide

Get up and running with Kaizen Agent in under 5 minutes! This guide will walk you through installing Kaizen Agent, creating a simple AI agent, and running your first automated test to accelerate your LLM development.

## Prerequisites

- **Python 3.8+** (Python 3.9+ recommended for best performance)
- **Google API Key** for Gemini models ([Get your API key here](https://aistudio.google.com/app/apikey))
- Basic familiarity with Python or TypeScript

## Step 1: Install & Setup

### Create a Test Directory

```bash
# Create a test directory for your specific agent
mkdir my-email-agent-test
cd my-email-agent-test

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Kaizen Agent

```bash
# Install Kaizen Agent from PyPI
pip install kaizen-agent
```

### Set Up Environment Variables

```bash
# Create .env file with your Google API key
cat > .env << EOF
GOOGLE_API_KEY=your_api_key_here
EOF

# Or set it directly in your shell
export GOOGLE_API_KEY="your_api_key_here"
```

## Step 2: Create Your AI Agent

### Python Version

Create `my_agent.py`:

```python
import google.generativeai as genai
import os

class EmailAgent:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        # Simple prompt that Kaizen can improve significantly
        self.system_prompt = "Improve this email draft."
    
    def improve_email(self, email_draft):
        full_prompt = f"{self.system_prompt}\n\nEmail draft:\n{email_draft}\n\nImproved version:"
        response = self.model.generate_content(full_prompt)
        return response.text
```

### TypeScript Version (Mastra)

Create `my_agent.ts`:

```typescript
import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';

export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: `You are an email assistant. Improve this email draft.`,
  model: google('gemini-2.5-flash-preview-05-20'),
});
```

## Step 3: Create Test Configuration

**🎯 No Test Code Required!** 

Kaizen Agent uses YAML configuration instead of traditional test files. This is a new, simpler way to test AI agents:

- **❌ Traditional approach**: Write test files with `unittest`, `pytest`, or `jest`
- **✅ Kaizen approach**: Define tests in YAML - no test code needed!

### Python Version

Create `kaizen.yaml`:

```yaml
name: Email Improvement Agent Test
file_path: my_agent.py
description: This agent improves email drafts by making them more professional, clear, and well-structured. It transforms casual or poorly written emails into polished, business-appropriate communications.
agent:
  module: my_agent
  class: EmailAgent
  method: improve_email

evaluation:
  evaluation_targets:
    - name: quality
      source: return
      criteria: "The email should be professional, polite, and well-structured with proper salutations and closings"
      weight: 0.5
    - name: format
      source: return
      criteria: "The response should contain only the improved email content without any explanatory text, markdown formatting, or additional commentary. It should be a clean, standalone email draft ready for use."
      weight: 0.5

files_to_fix:
  - my_agent.py

steps:
  - name: Professional Email Improvement
    input:
      input: "hey boss, i need time off next week. thanks"
  
  - name: Edge Case - Empty Email
    input:
      input: ""
  
  - name: Edge Case - Very Informal Email
    input:
      input: "yo dude, can't make it to the meeting tomorrow. got stuff to do. sorry!"
```

### TypeScript Version

Create `kaizen.yaml`:

```yaml
name: Email Improvement Agent Test
file_path: src/mastra/agents/email-agent.ts
language: typescript
description: This agent improves email drafts by making them more professional, clear, and well-structured. It transforms casual or poorly written emails into polished, business-appropriate communications.
agent:
  module: email-agent  # Just the file name without extension

evaluation:
  evaluation_targets:
    - name: quality
      source: return
      criteria: "The email should be professional, polite, and well-structured with proper salutations and closings"
      weight: 0.5
    - name: format
      source: return
      criteria: "The response should contain only the improved email content without any explanatory text, markdown formatting, or additional commentary. It should be a clean, standalone email draft ready for use."
      weight: 0.5

files_to_fix:
  - src/mastra/agents/email-agent.ts

settings:
  timeout: 180

steps:
  - name: Professional Email Improvement
    input:
      input: "hey boss, i need time off next week. thanks"
  
  - name: Edge Case - Very Informal Email
    input:
      input: "yo dude, can't make it to the meeting tomorrow. got stuff to do. sorry!"
```

## Step 4: Run Your First Test

```bash
# Run tests with auto-fix and save detailed logs
kaizen test-all --config kaizen.yaml --auto-fix --save-logs
```

Add the `--better-ai` flag to enable enhanced AI capabilities for improved code suggestions and fixes.

This command will:

1. **Test your email improvement agent** with realistic scenarios
2. **Automatically improve the simple prompt** to handle different email types
3. **Save detailed logs** to `test-logs/` so you can see the before/after improvements
4. **Generate a test report** showing what was tested and improved

## What Happens Next?

After running the test, Kaizen Agent will:

1. **Execute each test step** with the provided inputs
2. **Evaluate the results** using AI-powered criteria
3. **Identify areas for improvement** in your prompts or code
4. **Automatically fix issues** by improving prompts and code
5. **Re-test** to ensure the improvements work
6. **Generate a comprehensive report** with before/after comparisons

## Viewing Results

Check the `test-logs/` directory for detailed logs:

```bash
# View the latest test results
ls test-logs/
```

The logs contain:
- **Detailed execution logs** showing each step
- **Before/after comparisons** of your agent's performance
- **Improvement suggestions** and applied fixes
- **Performance metrics** and evaluation scores

## Next Steps

Now that you've run your first test, you can:

- **Explore the [Usage Guide](./usage.md)** to learn about advanced configuration options
- **Set up GitHub integration** to create pull requests with fixes (see [GitHub Guide](./github.md))
- **Check out [Examples](./examples.md)** for more complex agent scenarios
- **Join our [Discord community](https://discord.gg/2A5Genuh)** for support and tips

## Troubleshooting

If you encounter issues:

1. **Check your API key**: Ensure `GOOGLE_API_KEY` is set correctly
2. **Verify Python version**: Make sure you're using Python 3.8+
3. **Check file paths**: Ensure your agent file and YAML config are in the correct locations
4. **Review logs**: Check the `test-logs/` directory for detailed error information

For more help, see our [FAQ](./faq.md) or join our [Discord community](https://discord.gg/2A5Genuh). 