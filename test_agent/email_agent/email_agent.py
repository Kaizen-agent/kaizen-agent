import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import sys
import click

# kaizen:start:email_agent
class EmailAgent:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the EmailAgent with Google API key."""
        load_dotenv()  # Load environment variables from .env file
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set it as GOOGLE_API_KEY environment variable or pass it to the constructor.")
        
        try:
            # Configure the API
            genai.configure(api_key=self.api_key)
            # Use the same model version as TestRunner
            self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            # Test the configuration by generating content
            # This helps catch issues like invalid API keys or network problems early
            self.model.generate_content("Test")
        except (ValueError, ImportError, AttributeError) as e:
            raise ValueError(f"Failed to configure Google API: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error configuring Google API: {str(e)}")

    def improve_email(self, draft: str) -> str:
        """
        Improve the given email draft using Gemini's API.
        
        Args:
            draft (str): The original email draft to improve
            
        Returns:
            str: The improved email draft
        """
        if not draft or not draft.strip():
            raise ValueError("Email draft cannot be empty or contain only whitespace.")
            
        # Add safety instructions to the prompt
        prompt = f"""Please improve the following email draft. Make it more professional, clear, and effective while maintaining its original intent.
        Focus on:
        - Professional tone and language
        - Clear and concise communication
        - Proper email etiquette
        - Maintaining the original message's intent
        
        Here's the draft:
        
        {draft}
        
        Improved version:"""

        try:
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
            
            # Check for safety issues in the prompt feedback
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    raise ValueError(f"Content was blocked due to: {response.prompt_feedback.block_reason}")
            
            # Ensure candidates were generated
            if not hasattr(response, 'candidates') or not response.candidates:
                raise ValueError("No response candidates were generated from the model.")
            
            # Get the first candidate
            candidate = response.candidates[0]
            
            # Check for finish reasons indicating issues
            if hasattr(candidate, 'finish_reason'):
                if candidate.finish_reason == "MAX_TOKENS":
                    raise ValueError("Response was cut off due to token limit. Please try with a shorter email draft or adjust max_output_tokens.")
                elif candidate.finish_reason == "BLOCKED":
                    raise ValueError("Content was blocked by safety filters during generation.")
            
            # Attempt to extract the text content from the response
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                if not candidate.content.parts:
                    raise ValueError("Model response contained no content parts.")
                # Access the text from the first part
                return candidate.content.parts[0].text.strip()
            
            # If text could not be extracted, raise an error
            raise ValueError("Could not extract text from the model's response.")
            
        except ValueError as e:
            # Re-raise ValueError as is
            raise
        except (ImportError, AttributeError) as e:
            # Convert specific exceptions to ValueError
            raise ValueError(f"Failed to generate improved email: {str(e)}")
        except Exception as e:
            # Catch any other unexpected exceptions
            raise ValueError(f"Unexpected error generating improved email: {str(e)}")
# kaizen:end:email_agent

# kaizen:start:cli_interface
@click.command()
@click.option('--draft', type=str, help='Email draft to improve')
@click.option('--file', type=str, help='Path to file containing email draft')
def main(draft: str, file: str):
    """Main function to run the email agent from command line."""
    try:
        agent = EmailAgent()
        
        email_draft = None
        if draft:
            email_draft = draft
        elif file:
            try:
                with open(file, 'r') as f:
                    email_draft = f.read()
            except FileNotFoundError:
                click.echo(f"Error: File not found at '{file}'", err=True)
                return
            except Exception as e:
                click.echo(f"Error reading file '{file}': {str(e)}", err=True)
                return

        if email_draft is None:
            # If no --draft or --file is provided, read from stdin
            click.echo("Please enter your email draft (press Ctrl+D or Ctrl+Z on Windows when finished):")
            email_draft = sys.stdin.read()

        if not email_draft.strip():
            click.echo("No email draft provided.", err=True)
            return

        improved_email = agent.improve_email(email_draft)
        click.echo("\nImproved Email:")
        click.echo("-" * 50)
        click.echo(improved_email)
        click.echo("-" * 50)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    main()
# kaizen:end:cli_interface