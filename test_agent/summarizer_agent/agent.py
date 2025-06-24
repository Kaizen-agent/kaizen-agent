from .prompt import get_prompt
from .utils import call_gemini_llm


# kaizen:start:summarizer_agent
class SummarizerAgent:
    """Agent that processes user input using the Gemini model."""

    @staticmethod
    def run(text: str) -> str:
        return call_gemini_llm(get_prompt(text))
# kaizen:end:summarizer_agent