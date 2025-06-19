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
        # AI Agent Best Practice: Handle empty or whitespace-only input explicitly at the agent boundary
        if not text or text.strip() == "":
            return "Please provide some text to summarize."

        # AI Agent Best Practice: Classify user intent before proceeding with specific tasks.
        # This ensures the agent only performs its intended function (summarization).
        classification_prompt = (
            f"""Analyze the following user input. Determine if it is a request """
            f"""for summarization or if it contains text that needs to be """
            f"""summarized.\n"""
            f"""Respond with 'YES' if the input is clearly intended for """
            f"""summarization.\n"""
            f"""Respond with 'NO' if the input is a general question, a """
            f"""request for information, or anything else not related to """
            f"""summarizing text.\n"""
            f"""Your response must be ONLY 'YES' or 'NO'. Do not include any """
            f"""other words or punctuation.\n\n"""
            f"""User Input: "{text}"\n"""
        )

        try:
            # Call LLM for intent classification
            classification_response = call_gemini_llm(
                classification_prompt
            ).strip().upper()
        except Exception:
            # If LLM call fails for classification, return a generic error message
            return "I'm sorry, I encountered an issue and cannot process your request."

        # Based on classification, either proceed with summarization or return out-of-scope message
        if classification_response == "YES":
            prompt = get_prompt(text)
            return call_gemini_llm(prompt)
        else:
            return "I'm sorry, I can't help with that."
# kaizen:end:summarizer_agent