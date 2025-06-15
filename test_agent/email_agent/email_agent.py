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
        Improve the given email draft using Gemini's API or provide a specific response for non-email inputs.
        
        Args:
            draft (str): The original email draft to improve or a general text input.
            
        Returns:
            str: The improved email draft, or "I'm sorry, I can't help with that." if the input is not an email draft or an issue prevents improvement.
        """
        # Rule: "if the input is not a valid email, the output should be 'I'm sorry, I can't help with that.'"
        # An empty or whitespace-only draft is not considered a valid email draft for improvement.
        if not draft or not draft.strip():
            return "I'm sorry, I can't help with that."
            
        prompt = f"""You are an AI assistant specialized in improving email drafts.
        
        Analyze the following text.
        
        IF the text provided is clearly an email draft (e.g., it contains salutations like "Hi", "Dear", "Hello", or mentions meetings, projects, scheduling, or typical professional correspondence elements), THEN:
        Improve it to be more professional, clear, and effective while maintaining its original intent.
        Your response MUST ONLY contain the improved email draft, with absolutely no additional text, remarks, introductory phrases like "Here is the improved email:", or conversational filler. Start directly with the improved email content.
        
        IF the text provided is NOT an email draft (e.g., it's a question about a hotel, a random sentence, a list of items, or content completely unrelated to an email), THEN:
        Your response MUST ONLY be the exact phrase: "I'm sorry, I can't help with that." Do not add any punctuation or extra characters.
        
        Here's the text to analyze and process:
        
        {draft}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2, # Lowered for more deterministic output and adherence to instructions
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
            
            # Check for safety issues in the prompt feedback (input blocking)
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    return "I'm sorry, I can't help with that."
            
            # Ensure candidates were generated
            if not hasattr(response, 'candidates') or not response.candidates:
                return "I'm sorry, I can't help with that."
            
            candidate = response.candidates[0]
            
            # Check for finish reasons indicating issues
            if hasattr(candidate, 'finish_reason'):
                if candidate.finish_reason == "MAX_TOKENS":
                    # This is an operational error, not related to input validity, re-raise as error for agent.
                    raise ValueError("Response was cut off due to token limit. Please try with a shorter email draft or adjust max_output_tokens.")
                elif candidate.finish_reason == "BLOCKED":
                    # If the generated content was blocked by safety filters, then the agent cannot help with that.
                    return "I'm sorry, I can't help with that."
            
            # Attempt to extract the text content from the response
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                if not candidate.content.parts:
                    return "I'm sorry, I can't help with that."
                
                generated_text = candidate.content.parts[0].text.strip()
                
                # Double-check if the model returned the specific "cannot help" phrase
                # This ensures robustness against minor prompt deviations or if the model's classification
                # results in this specific output.
                if generated_text.strip().lower() == "i'm sorry, i can't help with that.":
                    return "I'm sorry, I can't help with that."
                
                return generated_text
            
            # If text could not be extracted in the expected format (e.g., content parts missing),
            # it means the agent cannot provide the improved email.
            return "I'm sorry, I can't help with that."
            
        except ValueError as e:
            # Re-raise if it's the specific token limit error, as this indicates an operational constraint.
            if "token limit" in str(e):
                raise e
            # For any other ValueError during processing, treat as "cannot help".
            return "I'm sorry, I can't help with that."
        except Exception as e:
            # Catch any other general exceptions (e.g., network issues, unexpected API errors).
            # If a problem occurs during generation, the agent cannot fulfill the request.
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