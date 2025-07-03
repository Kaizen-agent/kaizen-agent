# Examples

Explore real-world examples of AI agents and their Kaizen Agent test configurations. These examples demonstrate different use cases, input types, and evaluation strategies.

## Email Improvement Agent

A simple agent that improves email drafts by making them more professional and well-structured.

### Python Version

**Agent Code** (`my_agent.py`):

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

**Test Configuration** (`kaizen.yaml`):

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

### TypeScript Version (Mastra)

**Agent Code** (`my_agent.ts`):

```typescript
import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';

export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: `You are an email assistant. Improve this email draft.`,
  model: google('gemini-2.5-flash-preview-05-20'),
});
```

**Test Configuration** (`kaizen.yaml`):

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

## Text Analysis Agent

A more complex agent that performs sentiment analysis and extracts key information from text.

### Agent Code

**Agent Code** (`agents/text_analyzer.py`):

```python
import google.generativeai as genai
import os
import json

class TextAnalyzer:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        self.system_prompt = """
        You are a text analysis expert. Analyze the given text and provide:
        1. A sentiment score between -1.0 (very negative) and 1.0 (very positive)
        2. Key phrases that capture the main points
        3. A structured analysis summary
        
        Return your response as a JSON object with these fields:
        - sentiment_score: float
        - key_phrases: list of strings
        - analysis_summary: string
        """
    
    def analyze_text(self, text_content):
        if not text_content.strip():
            return {
                "sentiment_score": 0.0,
                "key_phrases": [],
                "analysis_summary": "No text provided for analysis."
            }
        
        full_prompt = f"{self.system_prompt}\n\nText to analyze:\n{text_content}\n\nAnalysis:"
        response = self.model.generate_content(full_prompt)
        
        try:
            # Try to parse JSON response
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # Fallback to structured text response
            return {
                "sentiment_score": 0.0,
                "key_phrases": [],
                "analysis_summary": response.text
            }
    
    def analyze_review(self, user_review, analysis_settings=None):
        """Analyze a structured user review object"""
        if analysis_settings is None:
            analysis_settings = {
                "include_sentiment": True,
                "extract_keywords": True,
                "detect_emotions": False
            }
        
        # Combine review text with metadata
        review_text = f"Review: {user_review.text}\nRating: {user_review.rating}/5\nCategory: {user_review.category}"
        
        result = self.analyze_text(review_text)
        result["review_quality"] = "high" if user_review.rating >= 4 else "medium"
        
        return result
```

**User Review Class** (`agents/review_processor.py`):

```python
class UserReview:
    def __init__(self, text, rating, category, helpful_votes=0, verified_purchase=False):
        self.text = text
        self.rating = rating
        self.category = category
        self.helpful_votes = helpful_votes
        self.verified_purchase = verified_purchase
```

### Test Configuration

**Test Configuration** (`kaizen.yaml`):

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

  - name: Neutral Text Analysis
    description: "Analyze neutral or mixed sentiment text"
    input:
      file_path: agents/text_analyzer.py
      method: analyze_text
      input: 
        - name: text_content
          type: string
          value: "The product has both good and bad aspects. The design is nice but the price is high."
          
      expected_output: 
        sentiment_score: 0.0
        key_phrases: ["good aspects", "bad aspects", "nice design", "high price"]

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

  - name: Empty Input Handling
    description: "Test how the agent handles empty or minimal input"
    input:
      file_path: agents/text_analyzer.py
      method: analyze_text
      input: 
        - name: text_content
          type: string
          value: ""
          
      expected_output: 
        sentiment_score: 0.0
        key_phrases: []
```

## Code Review Agent

An agent that reviews code and provides feedback on quality, security, and best practices.

### Agent Code

**Agent Code** (`agents/code_reviewer.py`):

```python
import google.generativeai as genai
import os

class CodeReviewer:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        self.system_prompt = """
        You are a senior software engineer conducting code reviews. Analyze the provided code and provide:
        1. Code quality assessment (1-10 scale)
        2. Security concerns (if any)
        3. Performance considerations
        4. Specific improvement suggestions
        
        Be constructive and provide actionable feedback.
        """
    
    def review_code(self, code_content, language="python"):
        full_prompt = f"{self.system_prompt}\n\nLanguage: {language}\n\nCode to review:\n```{language}\n{code_content}\n```\n\nReview:"
        response = self.model.generate_content(full_prompt)
        return response.text
    
    def review_function(self, function_code, context=None):
        """Review a specific function with optional context"""
        context_info = f"\nContext: {context}" if context else ""
        full_prompt = f"{self.system_prompt}\n\nFunction to review:{context_info}\n\n```python\n{function_code}\n```\n\nReview:"
        response = self.model.generate_content(full_prompt)
        return response.text
```

### Test Configuration

**Test Configuration** (`kaizen.yaml`):

```yaml
name: Code Review Agent Test Suite
file_path: agents/code_reviewer.py
description: |
  Test suite for the CodeReviewer agent that analyzes code quality, security, and best practices.
  
  This agent provides comprehensive code reviews with actionable feedback for
  improving code quality, identifying security issues, and suggesting optimizations.

agent:
  module: agents.code_reviewer
  class: CodeReviewer
  method: review_code

evaluation:
  evaluation_targets:
    - name: review_quality
      source: return
      criteria: "The review should be comprehensive, constructive, and provide specific, actionable feedback. It should identify potential issues and suggest concrete improvements."
      weight: 0.4
    - name: technical_depth
      source: return
      criteria: "The review should demonstrate technical expertise and cover code quality, security, performance, and best practices relevant to the programming language."
      weight: 0.3
    - name: clarity
      source: return
      criteria: "The feedback should be clear, well-structured, and easy to understand. It should avoid overly technical jargon when possible and provide explanations for suggestions."
      weight: 0.3

files_to_fix:
  - agents/code_reviewer.py

steps:
  - name: Python Function Review
    description: "Review a Python function for quality and best practices"
    input:
      file_path: agents/code_reviewer.py
      method: review_code
      input: 
        - name: code_content
          type: string
          value: |
            def calculate_total(items):
                total = 0
                for item in items:
                    total += item.price
                return total
        - name: language
          type: string
          value: "python"

  - name: Security Vulnerability Review
    description: "Review code for potential security vulnerabilities"
    input:
      file_path: agents/code_reviewer.py
      method: review_code
      input: 
        - name: code_content
          type: string
          value: |
            def process_user_input(user_data):
                query = "SELECT * FROM users WHERE id = " + user_data
                return execute_query(query)
        - name: language
          type: string
          value: "python"

  - name: Performance Review
    description: "Review code for performance optimizations"
    input:
      file_path: agents/code_reviewer.py
      method: review_code
      input: 
        - name: code_content
          type: string
          value: |
            def find_duplicates(items):
                duplicates = []
                for i in range(len(items)):
                    for j in range(i + 1, len(items)):
                        if items[i] == items[j]:
                            duplicates.append(items[i])
                return duplicates
        - name: language
          type: string
          value: "python"
```

## Chatbot Agent

A conversational agent that handles customer support queries.

### Agent Code

**Agent Code** (`agents/customer_support.py`):

```python
import google.generativeai as genai
import os
import json

class CustomerSupportBot:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        self.system_prompt = """
        You are a helpful customer support representative for TechCorp. 
        You help customers with product questions, troubleshooting, and general inquiries.
        
        Guidelines:
        - Be polite, professional, and helpful
        - Provide accurate information about our products
        - Escalate complex issues appropriately
        - Keep responses concise but informative
        - Always ask if there's anything else you can help with
        """
        self.conversation_history = []
    
    def respond(self, user_message, context=None):
        # Build conversation context
        conversation_context = ""
        if self.conversation_history:
            conversation_context = "\n\nPrevious conversation:\n"
            for msg in self.conversation_history[-3:]:  # Last 3 messages
                conversation_context += f"{msg['role']}: {msg['content']}\n"
        
        full_prompt = f"{self.system_prompt}{conversation_context}\n\nCustomer: {user_message}\n\nSupport Agent:"
        response = self.model.generate_content(full_prompt)
        
        # Update conversation history
        self.conversation_history.append({"role": "customer", "content": user_message})
        self.conversation_history.append({"role": "agent", "content": response.text})
        
        return response.text
    
    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation_history = []
```

### Test Configuration

**Test Configuration** (`kaizen.yaml`):

```yaml
name: Customer Support Bot Test Suite
file_path: agents/customer_support.py
description: |
  Test suite for the CustomerSupportBot that handles customer inquiries and support requests.
  
  This agent provides helpful, professional responses to customer questions about
  products, troubleshooting, and general support issues.

agent:
  module: agents.customer_support
  class: CustomerSupportBot
  method: respond

evaluation:
  evaluation_targets:
    - name: helpfulness
      source: return
      criteria: "The response should be helpful and directly address the customer's question or concern. It should provide relevant information or guidance."
      weight: 0.4
    - name: professionalism
      source: return
      criteria: "The response should be polite, professional, and maintain a helpful tone. It should reflect good customer service practices."
      weight: 0.3
    - name: accuracy
      source: return
      criteria: "The information provided should be accurate and appropriate for a customer support context. It should not contain false or misleading information."
      weight: 0.3

files_to_fix:
  - agents/customer_support.py

steps:
  - name: Product Inquiry
    description: "Handle a customer asking about product features"
    input:
      file_path: agents/customer_support.py
      method: respond
      input: 
        - name: user_message
          type: string
          value: "What are the main features of your premium plan?"

  - name: Technical Support
    description: "Handle a technical troubleshooting request"
    input:
      file_path: agents/customer_support.py
      method: respond
      input: 
        - name: user_message
          type: string
          value: "I can't log into my account. It says 'invalid credentials' but I'm sure my password is correct."

  - name: Billing Question
    description: "Handle a billing-related inquiry"
    input:
      file_path: agents/customer_support.py
      method: respond
      input: 
        - name: user_message
          type: string
          value: "I was charged twice this month. Can you help me get a refund?"

  - name: Conversation Continuity
    description: "Test conversation history and context"
    input:
      file_path: agents/customer_support.py
      method: respond
      input: 
        - name: user_message
          type: string
          value: "Thanks for the help. How do I contact you if I have more questions?"
```

## Running the Examples

To run any of these examples:

1. **Create the agent file** with the provided code
2. **Create the YAML configuration** file
3. **Set up your environment** with the required API keys
4. **Run the tests**:

```bash
# Run with auto-fix
kaizen test-all --config kaizen.yaml --auto-fix --save-logs

# Run with PR creation (if GitHub is set up)
kaizen test-all --config kaizen.yaml --auto-fix --create-pr --repo your-username/your-repo-name
```

## Customizing Examples

You can customize these examples by:

- **Modifying the prompts** to match your specific use case
- **Adjusting evaluation criteria** to focus on your priorities
- **Adding more test cases** to cover additional scenarios
- **Changing input types** to match your agent's expected inputs
- **Updating file paths** to match your project structure

## Best Practices from Examples

1. **Clear Evaluation Criteria**: Each example shows specific, measurable evaluation criteria
2. **Edge Case Testing**: Examples include tests for empty inputs, error conditions, and unusual scenarios
3. **Descriptive Test Names**: Test names clearly indicate what's being tested
4. **Balanced Test Coverage**: Mix of happy path and edge case tests
5. **Realistic Inputs**: Test inputs reflect real-world usage scenarios

For more examples and community contributions, check out our [GitHub repository](https://github.com/Kaizen-agent/kaizen-agent) or join our [Discord community](https://discord.gg/2A5Genuh). 