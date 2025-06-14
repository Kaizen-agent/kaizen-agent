import google.generativeai as genai
from typing import List, Dict, Any

class BaseLLMAgent:
    """Base class for LLM-powered agents using Google's Gemini model."""
    
    def __init__(self, api_key: str, system_prompt: str):
        """Initialize with Google API key and system prompt."""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.system_prompt = system_prompt
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        self.conversation_history: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]
    
    def _call_llm(self, user_input: str, temperature: float = 0.7) -> str:
        """Make a call to the Gemini API."""
        try:
            # Add user input to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Prepare the chat session
            chat = self.model.start_chat(history=self.conversation_history)
            
            # Get response from Gemini
            response = chat.send_message(user_input, temperature=temperature)
            
            # Extract and store the response
            assistant_response = response.text
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def clear_history(self):
        """Clear the conversation history except for the system prompt."""
        self.conversation_history = [self.conversation_history[0]] 