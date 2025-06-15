import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import sys

# kaizen:start:email_agent
class EmailAgent:
    REFUSAL_MESSAGE = "I'm sorry, I can't help with that." # Define refusal message as a class constant

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
        except Exception as e:
            # More specific error message for API configuration issues
            raise ValueError(f"Failed to configure Google API or test model. Check API key and network connection: {str(e)}")

    def improve_email(self, draft: str) -> str:
        """
        Improve the given email draft using Gemini's API.
        
        Args:
            draft (str): The original email draft to improve
            
        Returns:
            str: The improved email draft or a refusal message if the input is not a valid email draft.
        """
        if not draft or not draft.strip():
            # For empty or whitespace-only drafts, raise an error as it's not a semantically valid draft to process.
            # The "I'm sorry, I can't help with that." is specifically for non-email *content*.
            raise ValueError("Email draft cannot be empty or contain only whitespace.")
            
        # Modified prompt to include conditional behavior for non-email drafts and strict output formatting
        prompt = f"""You are an AI assistant specialized in improving email drafts.
If the provided text is clearly NOT an email draft (e.g., it's a general question, a random sentence, a poem, or a very short, non-email like phrase), your ONLY response MUST be: '{EmailAgent.REFUSAL_MESSAGE}'
If the provided text IS an email draft, then please improve it. Make it more professional, clear, and effective while maintaining its original intent.
Crucially, ensure the improved version contains ONLY the email content. Do NOT include any conversational lead-ins (e.g., "Here's the improved email:", "Subject:", "Body:"), or any other extraneous text around the email itself. The output should be the raw email draft, ready to be copied and pasted.

Focus on:
- Professional tone and language
- Clear and concise communication
- Proper email etiquette
- Maintaining the original message's intent

Here's the draft:

{draft}

Improved version (if applicable, otherwise the exact refusal message specified above):"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2, # Lower temperature for more deterministic output, especially for the refusal
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
            
            # Check for prompt feedback blocking
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and \
               hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                raise ValueError(f"Content was blocked due to: {response.prompt_feedback.block_reason}")
            
            # Ensure candidates were generated
            if not hasattr(response, 'candidates') or not response.candidates:
                raise ValueError("No response candidates were generated from the model.")
            
            # Get the first candidate
            candidate = response.candidates[0]
            
            # Check for finish reasons indicating issues during generation
            if hasattr(candidate, 'finish_reason'):
                if candidate.finish_reason == "MAX_TOKENS":
                    raise ValueError("Response was cut off due to token limit. Please try with a shorter email draft or adjust max_output_tokens.")
                elif candidate.finish_reason == "BLOCKED":
                    raise ValueError("Content was blocked by safety filters during generation.")
            
            # Attempt to extract the text content from the response
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                if not candidate.content.parts:
                    raise ValueError("Model response contained no content parts.")
                
                generated_text = candidate.content.parts[0].text.strip()
                
                # Check if the generated text is the exact refusal message
                if generated_text == EmailAgent.REFUSAL_MESSAGE:
                    return generated_text
                
                return generated_text
            
            raise ValueError("Could not extract text from the model's response.")
            
        except Exception as e:
            # Catch any other exceptions during content generation and re-raise as ValueError
            raise ValueError(f"Failed to generate improved email: {str(e)}")
# kaizen:end:email_agent

# kaizen:start:cli_interface
def main():
    """Main function to run the email agent from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Email Improvement Agent")
    parser.add_argument("--draft", type=str, help="Email draft to improve")
    parser.add_argument("--file", type=str, help="Path to file containing email draft")
    args = parser.parse_args()

    try:
        agent = EmailAgent()
        
        draft = None
        if args.draft:
            draft = args.draft
        elif args.file:
            try:
                with open(args.file, 'r') as f:
                    draft = f.read()
            except FileNotFoundError:
                print(f"Error: File not found at '{args.file}'")
                return
            except Exception as e:
                print(f"Error reading file '{args.file}': {str(e)}")
                return

        if draft is None:
            # If no --draft or --file is provided, read from stdin
            print("Please enter your email draft (press Ctrl+D or Ctrl+Z on Windows when finished):")
            # Changed to use sys.stdin.read() for more robust input handling
            draft = sys.stdin.read()

        if not draft.strip():
            # If the draft is empty or just whitespace after reading, print an error and exit.
            # This is distinct from the semantic "not a valid email" handled by the LLM.
            print("No email draft provided.")
            return

        improved_email = agent.improve_email(draft)
        
        # Check if the output is the specific refusal message
        if improved_email == EmailAgent.REFUSAL_MESSAGE: # Use the constant here as well
            print(f"\n{improved_email}")
        else:
            print("\nImproved Email:")
            print("-" * 50)
            print(improved_email)
            print("-" * 50)

    except ValueError as ve: # Catch specific ValueErrors from EmailAgent for cleaner output
        print(f"Error: {str(ve)}")
    except Exception as e: # Catch any other unexpected errors
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
# kaizen:end:cli_interface