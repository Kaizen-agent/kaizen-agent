import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import sys

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
        except Exception as e:
            raise ValueError(f"Failed to configure Google API: {str(e)}")

    def _classify_input_as_email(self, text: str) -> bool:
        """
        Classifies if the given text appears to be an email draft using the LLM.
        
        Args:
            text (str): The input text to classify.
            
        Returns:
            bool: True if classified as an email draft, False otherwise.
            
        Raises:
            ValueError: If an unrecoverable error occurs during classification (e.g., API issues, content blocking).
        """
        validation_prompt = f"""Does the following text appear to be an email draft, a message intended to be an email, or does it contain content suitable for an email?
        
        Text:
        '''{text}'''
        
        Respond with 'EMAIL_DRAFT' if it is, or 'NOT_EMAIL' if it is not.
        Your response must be ONLY 'EMAIL_DRAFT' or 'NOT_EMAIL', with no other text or explanation.
        """
        
        try:
            validation_response = self.model.generate_content(
                validation_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Keep temperature low for reliable classification
                    max_output_tokens=15, # Expecting 'EMAIL_DRAFT' or 'NOT_EMAIL'
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            )
            
            # Check for block reasons or empty candidates
            if hasattr(validation_response, 'prompt_feedback') and validation_response.prompt_feedback:
                if hasattr(validation_response.prompt_feedback, 'block_reason'):
                    raise ValueError(f"Input blocked during classification: {validation_response.prompt_feedback.block_reason}")
            
            if not hasattr(validation_response, 'candidates') or not validation_response.candidates:
                raise ValueError("No candidate generated for classification.")
            
            val_candidate = validation_response.candidates[0]
            
            if hasattr(val_candidate, 'finish_reason') and val_candidate.finish_reason == "BLOCKED":
                raise ValueError("Classification content was blocked by safety filters during generation.")

            if hasattr(val_candidate, 'content') and hasattr(val_candidate.content, 'parts'):
                val_text = val_candidate.content.parts[0].text.strip().upper()
                return "EMAIL_DRAFT" in val_text
            
            raise ValueError("Could not extract classification text from the model's response.")
            
        except Exception as e:
            # Re-raise as ValueError to be caught by improve_email
            raise ValueError(f"Error during email draft classification: {str(e)}")


    def _generate_improved_email(self, draft: str) -> str:
        """
        Generates an improved email draft using the LLM.
        
        Args:
            draft (str): The original email draft.
            
        Returns:
            str: The improved email draft.
            
        Raises:
            ValueError: If an unrecoverable error occurs during generation (e.g., API issues, content blocking, token limits).
        """
        prompt = f"""You are an expert email assistant. Improve the following email draft.
        
        Focus on:
        - Professional tone and language.
        - Clear and concise communication.
        - Proper email etiquette.
        - Maintaining the original message's intent.
        
        IMPORTANT: Your response MUST contain ONLY the improved email draft. Do NOT include any introductory phrases, conversational remarks, subject lines, salutations, closings (like "Sincerely,"), or any other text outside of the refined email body itself. The output should be a standalone email draft, ready to be copied and pasted as is.
        
        Original Draft:
        '''{draft}'''
        """

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
            
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    raise ValueError(f"Content was blocked due to: {response.prompt_feedback.block_reason}")
            
            if not hasattr(response, 'candidates') or not response.candidates:
                raise ValueError("No response candidates were generated from the model.")
            
            candidate = response.candidates[0]
            
            if hasattr(candidate, 'finish_reason'):
                if candidate.finish_reason == "MAX_TOKENS":
                    raise ValueError("Response was cut off due to token limit. Please try with a shorter email draft or adjust max_output_tokens.")
                elif candidate.finish_reason == "BLOCKED":
                    raise ValueError("Content was blocked by safety filters during generation.")
            
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                if not candidate.content.parts:
                    raise ValueError("Model response contained no content parts.")
                
                return candidate.content.parts[0].text.strip()
            
            raise ValueError("Could not extract text from the model's response.")
            
        except Exception as e:
            raise ValueError(f"Failed to generate improved email: {str(e)}")

    def improve_email(self, draft: str) -> str:
        """
        Improve the given email draft using Gemini's API.
        
        Args:
            draft (str): The original email draft to improve
            
        Returns:
            str: The improved email draft or a specific error message if the input
                 is not a valid email draft or if an internal error occurs.
        """
        if not draft or not draft.strip():
            # This error is typically handled upstream by the CLI, but kept for robustness.
            raise ValueError("Email draft cannot be empty or contain only whitespace.")
            
        try:
            # First, validate if the input is actually an email draft using the LLM.
            is_email_draft = self._classify_input_as_email(draft)

            if not is_email_draft:
                # Returns specific message for non-email inputs, as per requirement
                return "I'm sorry, I can't help with that."
                
            # If it's classified as an email, proceed with improvement.
            improved_email = self._generate_improved_email(draft)
            return improved_email

        except ValueError as e:
            # Catch specific ValueErrors from helper methods and return the generic error message.
            # This covers API issues, blocked content during classification or generation.
            # print(f"Debug: Internal error during email processing: {str(e)}") # Uncomment for debugging
            return "I'm sorry, I can't help with that."
        except Exception as e:
            # Catch any unexpected errors and return the generic error message.
            # print(f"Debug: Unexpected error during email processing: {str(e)}") # Uncomment for debugging
            return "I'm sorry, I can't help with that."

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
            draft = sys.stdin.read()

        if not draft.strip():
            print("No email draft provided.")
            return

        improved_email = agent.improve_email(draft)
        print("\nImproved Email:")
        print("-" * 50)
        print(improved_email)
        print("-" * 50)

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
# kaizen:end:cli_interface