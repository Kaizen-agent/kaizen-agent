import os
import sys
from typing import Optional

import click
from dotenv import load_dotenv
import google.generativeai as genai


# kaizen:start:email_agent
class EmailAgent:
    """Initialize the EmailAgent with Google API key."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the EmailAgent with Google API key."""
        load_dotenv()  # Load environment variables from .env file
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key is required. Set it as GOOGLE_API_KEY environment "
                "variable or pass it to the constructor."
            )

        # Configure the API. Add essential error handling for critical initialization.
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            # Test the model to ensure connectivity and API key validity
            self.model.generate_content("Test")
        except Exception as e:
            raise RuntimeError(
                "Failed to initialize Google Generative AI model. Check your API key "
                f"and network connection: {e}"
            )

    def improve_email(self, draft: str) -> str:
        """
        Improve the given email draft using Gemini's API.

        Args:
            draft (str): The original email draft to improve

        Returns:
            str: The improved email draft
        """
        # Improve the prompt using modern prompt engineering best practices:
        # - Define a clear role for the AI.
        # - Clearly state the task and specific instructions.
        # - Add explicit constraints on the output format to ensure only the email draft is returned.
        # - Use clear input/output formatting.
        prompt = f"""
        Role: You are an expert email communication specialist.

        Task: Improve the following email draft to be more professional, clear, and effective.

        Instructions:
        1.  Maintain the original intent and core message of the email.
        2.  Focus on the following aspects:
            *   Professional tone and language
            *   Clear and concise communication
            *   Proper email etiquette
        3.  Your response MUST ONLY contain the improved email draft. DO NOT include any introductory phrases, explanations, or additional commentary.

        Original Email Draft:
        ---
        {draft}
        ---

        Improved Email Draft:
        """

        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
                top_p=0.8,
                top_k=40,
            ),
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        )

        # Strip any leading/trailing whitespace or newlines that the model might add,
        # although the prompt is designed to prevent extra text.
        return response.text.strip()
# kaizen:end:email_agent


@click.command()
@click.option('--draft', type=str, help='Email draft to improve')
@click.option('--file', type=str, help='Path to file containing email draft')
def main(draft: str, file: str):
    """Main function to run the email agent from command line."""
    agent = EmailAgent()

    email_draft = None
    if draft:
        email_draft = draft
    elif file:
        with open(file, 'r') as f:
            email_draft = f.read()
    else:
        # If no --draft or --file is provided, read from stdin
        click.echo(
            "Please enter your email draft (press Ctrl+D or Ctrl+Z on Windows "
            "when finished):"
        )
        email_draft = sys.stdin.read()

    if not email_draft.strip():
        click.echo("No email draft provided.", err=True)
        return

    improved_email = agent.improve_email(email_draft)
    click.echo("\nImproved Email:")
    click.echo("-" * 50)
    click.echo(improved_email)
    click.echo("-" * 50)


if __name__ == '__main__':
    main()