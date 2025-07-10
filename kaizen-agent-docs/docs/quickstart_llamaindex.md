---
sidebar_position: 3
---

# LlamaIndex Quickstart Guide

**Get started with Kaizen Agent for LlamaIndex applications in minutes**

This guide will walk you through setting up Kaizen Agent to test and improve your LlamaIndex-based AI applications.

## Prerequisites

Before you begin, make sure you have:

- Python 3.8+ installed
- A LlamaIndex application you want to test
- Access to an LLM API (OpenAI, Anthropic, etc.)

## Installation

Install Kaizen Agent using pip:

```bash
pip install kaizen-agent
```

## Step 1: Create Your Test Configuration

Create a `test_config.yaml` file in your project root:

```yaml
name: Email Agent
agent_type: dynamic_region
file_path: email_agent.py
description: |
  An agent that improves an email draft by making it more professional, clear, and effective.

framework: llamaindex

agent:
  module: email_agent
  class: EmailAgent
  method: improve_email

evaluation:
  evaluation_targets:
    - name: improved_email
      source: return
      criteria: "The improved_email must be a string that is easy to understand and follow."
      description: "Evaluates the accuracy of the improved email"
      weight: 0.5
    - name: formatted_email
      source: return
      criteria: "The improved_email must be a string that is formatted correctly and contains only the improved email no other text."
      description: "Checks if the improved email is formatted correctly"
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
          value: "Hey, can you send me the report?"
          
  - name: Edge Case
    input:
      input: 
        - name: email_draft
          type: string
          value: "test"
```

## Step 2: Prepare Your LlamaIndex Agent

Create your LlamaIndex agent file (e.g., `email_agent.py`):

```python
from llama_index.core.agent import ReActAgent
from llama_index.llms.gemini import Gemini
from llama_index.core.tools.function_tool import FunctionTool
from typing import Dict, Any
import os
from dotenv import load_dotenv


class EmailAgent:
    """An agent for improving email drafts using AI."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the EmailAgent.
        
        Args:
            api_key (str, optional): Google API key. If not provided, will try to load from environment.
        """
        # Load environment variables
        load_dotenv()
        
        # Get API key
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable or pass it to the constructor.")
        
        # Initialize components
        self.llm = Gemini(model="models/gemini-2.0-flash-lite", temperature=0.1)
        self.agent = self._create_agent()
    
    def _improve_email_with_llm(self, email_draft: str) -> str:
        """
        Improve an email draft using the LLM to make it more professional, clear, and effective.
        
        Args:
            email_draft (str): The original email draft to improve
            
        Returns:
            str: The improved email version
        """
        prompt = f"""
        improve this email: "{email_draft}"
        """
        
        try:
            response = self.llm.complete(prompt)
            return response.text.strip()
        except Exception as e:
            # Fallback to basic improvements if LLM fails
            return f"Error using LLM: {e}. Original email: {email_draft}"
    
    def _create_agent(self) -> ReActAgent:
        """Create and return the email improvement agent."""
        
        # Create the email improvement tool with LLM
        def improve_email_wrapper(email_draft: str) -> str:
            return self._improve_email_with_llm(email_draft)
        
        email_tool = FunctionTool.from_defaults(
            fn=improve_email_wrapper,
            name="improve_email",
            description="Improve an email draft by making it more professional, clear, and effective using AI"
        )
        
        # Create the agent
        agent = ReActAgent.from_tools(
            tools=[email_tool],
            llm=self.llm,
            verbose=True
        )
        
        return agent
    
    def improve_email(self, email_draft: str) -> str:
        """
        Improve an email draft.
        
        Args:
            email_draft (str): The email draft to improve
            
        Returns:
            str: The improved email version
        """
        if not email_draft or not email_draft.strip():
            raise ValueError("Email draft cannot be empty")
        
        try:
            response = self.agent.chat(
                f"Please use the improve_email tool to enhance this email draft: '{email_draft}'. "
                "Make it more professional and well-formatted."
            )
            return response.response
        except Exception as e:
            raise RuntimeError(f"Failed to improve email: {e}")


def main():
    """Main function to run the interactive email agent."""
    
    try:
        # Create the agent
        agent = EmailAgent()
        
        print("=== Email Improvement Agent ===\n")
        print("Type your email draft and I'll help improve it!")
        print("Type 'quit' to exit the program.\n")
        
        while True:
            try:
                # Get user input
                email_draft = input("Enter your email draft: ").strip()
                
                # Check if user wants to quit
                if email_draft.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                # Check if input is empty
                if not email_draft:
                    print("Please enter a valid email draft.\n")
                    continue
                
                print("\nImproving your email...")
                
                # Get improved version from agent
                improved_email = agent.improve_email(email_draft)
                
                print("\n" + "="*50)
                print("IMPROVED EMAIL:")
                print("="*50)
                print(improved_email)
                print("="*50 + "\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"Error improving email: {e}")
                print("Please try again.\n")
                
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
```

## Step 3: Set Up Environment Variables

Create a `.env` file in your project root:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

## Step 4: Run Kaizen Agent

Execute the test command:

```bash
kaizen test-all --config test_config.yaml --auto-fix
```

Add the `--better-ai` flag to enable enhanced AI capabilities for improved code suggestions and fixes.


Kaizen Agent will:
1. Load your LlamaIndex EmailAgent
2. Run it against your test cases
3. Evaluate the responses using AI
4. Automatically fix issues it finds
5. Re-test until all cases pass

## Step 4: Review Results

Kaizen Agent provides detailed reports showing:

- **Test Results**: Pass/fail status for each test case
- **Improvements Made**: What changes were automatically applied
- **Performance Metrics**: Response quality scores
- **Before/After Comparisons**: How your agent improved

## Advanced Configuration

### Custom Evaluation Criteria

You can define more sophisticated evaluation criteria for email improvement:

```yaml
evaluation:
  evaluation_targets:
    - name: professional_tone
      source: return
      criteria: "The email should maintain a professional and courteous tone"
      description: "Evaluates the professionalism of the improved email"
      weight: 0.3
    - name: clarity
      source: return
      criteria: "The email should be clear, concise, and easy to understand"
      description: "Checks if the email is clear and well-structured"
      weight: 0.3
    - name: grammar_spelling
      source: return
      criteria: "The email should be free of grammatical and spelling errors"
      description: "Ensures proper grammar and spelling"
      weight: 0.2
    - name: formatting
      source: return
      criteria: "The email should be properly formatted with appropriate structure"
      description: "Checks email formatting and structure"
      weight: 0.2
```


## Troubleshooting

### Common Issues

**Issue**: Import errors with LlamaIndex
```bash
pip install llama-index
```

**Issue**: Google API key not found
```bash
# Make sure your .env file contains:
GOOGLE_API_KEY=your_actual_api_key_here
```


## Next Steps

- Explore [Usage Guide](./usage.md) for advanced features
- Check out [Examples](./examples.md) for more LlamaIndex patterns
- Join our [Discord community](https://discord.gg/2A5Genuh) for support

