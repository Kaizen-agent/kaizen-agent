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
            # Removed debug print: print("Debug: EmailAgent: Successfully configured Google API")
        except Exception as e:
            raise ValueError(f"Failed to configure Google API: {str(e)}")

    def improve_email(self, draft: str) -> str:
        """
        Improve the given email draft using Gemini's API.
        
        Args:
            draft (str): The original email draft to improve
            
        Returns:
            str: The improved email draft or an error message if the input is not a valid email.
        """
        if not draft or not draft.strip():
            raise ValueError("Email draft cannot be empty or contain only whitespace.")
            
        # Step 1: Classify the input to determine if it's an email draft or a general query.
        classification_prompt = f"""Please categorize the following text.
Respond with 'EMAIL_DRAFT' if it is clearly an email draft, or 'GENERAL_QUERY' if it is a general question or statement.
Your response should contain only one of these two words, no other text or explanation.

Text:
{draft}
"""
        try:
            classification_response = self.model.generate_content(
                classification_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0, # Use low temperature for deterministic classification
                    max_output_tokens=20, # Expecting only 'EMAIL_DRAFT' or 'GENERAL_QUERY'
                )
            )
            
            # Robustly check classification response
            if not hasattr(classification_response, 'candidates') or not classification_response.candidates:
                # If LLM doesn't return candidates for classification, we cannot classify reliably.
                # Treat as a general query for safety and consistent behavior as per test requirements.
                return "I'm sorry, I can't help with that."
            
            candidate_content = classification_response.candidates[0].content
            if not hasattr(candidate_content, 'parts') or not candidate_content.parts:
                # If content parts are missing, classification is unclear.
                return "I'm sorry, I can't help with that."
                
            classification_text = candidate_content.parts[0].text.strip().upper()

            # If classified as a general query, return the specific message.
            if "GENERAL_QUERY" in classification_text:
                return "I'm sorry, I can't help with that."
                
        except Exception as e:
            # If any part of the classification process fails (API error, network issue, malformed response),
            # return the specific message as the input cannot be processed for improvement.
            return "I'm sorry, I can't help with that."

        # Step 2: If classified as an email draft, proceed with improvement.
        # Add safety instructions and strict output formatting to the prompt
        prompt = f"""Please improve the following email draft. Make it more professional, clear, and effective while maintaining its original intent.
        Focus on:
        - Professional tone and language
        - Clear and concise communication
        - Proper email etiquette
        - Maintaining the original message's intent
        
        Return ONLY the improved email draft. Do not include any introductory phrases, titles (like "Subject:"), or concluding remarks like "Here's the improved version:". Ensure the output is just the raw email body, ready to be sent.
        
        Here's the draft:
        
        {draft}
        
        Improved version:"""

        try:
            # Removed debug print: print(f"Debug: Prompt: {prompt}")
            response = self.model.generate_content(
                prompt,
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
            # Removed debug print: print(f"Debug: Response: {response}")
            
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
                # Access the text from the first part and strip whitespace
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
            # Changed to use sys.stdin.read() for more robust input handling
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