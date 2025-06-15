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

    def improve_email(self, draft: str) -> str:
        """
        Improve the given email draft using Gemini's API.
        
        Args:
            draft (str): The original email draft to improve
            
        Returns:
            str: The improved email draft
        """
        # --- Input Classification ---
        try:
            classification_prompt = f"""Classify the following text as either "EMAIL_DRAFT" or "NOT_EMAIL". Respond with ONLY one of these two phrases.

            Text:
            {draft}

            Classification:"""

            classification_response = self.model.generate_content(
                classification_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=20,
                ),
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE"
                    }
                ]
            )

            # Check for safety issues in the prompt feedback for classification
            if hasattr(classification_response, 'prompt_feedback') and classification_response.prompt_feedback:
                if hasattr(classification_response.prompt_feedback, 'block_reason'):
                    return "I'm sorry, I can't help with that."
            
            if not hasattr(classification_response, 'candidates') or not classification_response.candidates:
                return "I'm sorry, I can't help with that."

            classification_candidate = classification_response.candidates[0]
            if hasattr(classification_candidate, 'finish_reason') and classification_candidate.finish_reason == "BLOCKED":
                return "I'm sorry, I can't help with that."

            if hasattr(classification_candidate, 'content') and hasattr(classification_candidate.content, 'parts'):
                if not classification_candidate.content.parts:
                    return "I'm sorry, I can't help with that."
                classification_result = classification_candidate.content.parts[0].text.strip().upper()
            else:
                classification_result = "" # Fallback if content not found or structured unexpectedly

            if "NOT_EMAIL" in classification_result:
                return "I'm sorry, I can't help with that."
            elif "EMAIL_DRAFT" not in classification_result: # Handles garbled, empty, or unexpected classification responses
                return "I'm sorry, I can't help with that."

        except Exception as e:
            # Any error during classification (e.g., API issues) should result in the specific message
            return "I'm sorry, I can't help with that."
        # --- End Input Classification ---

        # The prompt below is for the actual email improvement
        improvement_prompt = f"""Please improve the following email draft. Make it more professional, clear, and effective while maintaining its original intent.
        Your response must *only* contain the improved email draft itself. Do not include any conversational text, introductions like 'Here's the improved email:', headings (e.g., 'Subject:', 'Body:'), or conclusions (e.g., 'I hope this helps!' or signatures like 'Sincerely,'). Just the plain, improved email content.

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
                improvement_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048, # Increased token limit for longer emails
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