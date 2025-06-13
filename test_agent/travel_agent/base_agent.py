import openai
from typing import List, Dict, Any

class BaseLLMAgent:
    """Base class for LLM-powered agents."""
    
    def __init__(self, api_key: str, system_prompt: str):
        """Initialize with OpenAI API key and system prompt."""
        self.api_key = api_key
        openai.api_key = api_key
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]
    
    def _call_llm(self, user_input: str, temperature: float = 0.7) -> str:
        """Make a call to the OpenAI API."""
        try:
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Get response from OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history,
                temperature=temperature
            )
            
            # Extract and store the response
            assistant_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def clear_history(self):
        """Clear the conversation history except for the system prompt."""
        self.conversation_history = [self.conversation_history[0]] 