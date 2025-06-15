from .prompt import get_prompt
from .utils import call_gemini_llm
# kaizen:start:summarizer_agent
class SummarizerAgent:
    """Agent that processes user input using the Gemini model."""
    
    @staticmethod
    def run(text: str) -> str:
        """
        Process the user's input and return a response.
        
        Args:
            text (str): The user's input text
            
        Returns:
            str: The agent's response
        """
        prompt = get_prompt(text)
        return call_gemini_llm(prompt) 
# kaizen:end:summarizer_agent