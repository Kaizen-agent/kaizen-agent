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
        Improve the given email draft using Gemini's API or indicate if it's not an email improvement request.
        
        Args:
            draft (str): The original text to process. It can be an email draft or another query.
            
        Returns:
            str: The improved email draft if applicable, or "I'm sorry, I can't help with that."
                 if the input is not related to email improvement.
        """
        if not draft or not draft.strip():
            raise ValueError("Input draft cannot be empty or contain only whitespace.")
            
        # Combine instructions for classification and improvement in one prompt
        # This prompt guides the model to either improve the email or return a specific refusal message.
        prompt = f"""
        You are an AI assistant specialized in improving email drafts. Your goal is to provide a refined email draft if the input is an email, or a specific refusal message otherwise.
        
        Task:
        1. Carefully evaluate if the provided text is a genuine email draft that needs improvement. Look for salutations, closings, common email phrases, and a clear message intent.
        2. If it is a legitimate email draft, improve it by making it more professional, clear, and effective while maintaining its original intent. The output must be *only* the improved email draft, with no additional conversational text, headings, or formatting beyond the email itself.
        3. If the provided text is *not* an email draft (e.g., a general question like "Are you chatgpt?", a random statement, a list, or something entirely unrelated to email composition), you *must* respond with the exact phrase: "I'm sorry, I can't help with that." Do not say anything else.
        
        Focus areas for email improvement (if applicable):
        - Professional tone and language
        - Clear and concise communication
        - Proper email etiquette
        - Maintaining the original message's intent
        
        Here is the text to process:
        
        {draft}
        
        Your response (must be *either* the improved email draft *or* the exact phrase "I'm sorry, I can't help with that."):
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2, # Lower temperature for more deterministic output, especially for classification
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
                    # If response was cut off, it could be a partial email or other content.
                    # For a robust solution, we should indicate a problem.
                    raise ValueError("Model response was cut off due to token limit.")
                elif candidate.finish_reason == "BLOCKED":
                    raise ValueError("Content was blocked by safety filters during generation.")
            
            # Attempt to extract the text content from the response
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                if not candidate.content.parts:
                    raise ValueError("Model response contained no content parts.")
                
                model_output = candidate.content.parts[0].text.strip()
                
                # Check if the output matches the refusal message for non-email inputs
                # Using a case-insensitive check and then returning the exact required string
                if "i'm sorry, i can't help with that" in model_output.lower():
                    return "I'm sorry, I can't help with that."
                
                # Otherwise, it should be the improved email draft.
                return model_output
            
            # If text could not be extracted, raise an error
            raise ValueError("Could not extract text from the model's response.")
            
        except Exception as e:
            # Catch any other exceptions during content generation and re-raise as ValueError
            # This includes API errors, network issues, etc.
            raise ValueError(f"Failed to generate response: {str(e)}")
# kaizen:end:email_agent

# kaizen:start:cli_interface exclude
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
            print("Please enter your text (Ctrl+D or Ctrl+Z on Windows when finished):")
            draft = sys.stdin.read()

        if not draft.strip():
            print("No input provided.")
            return

        improved_email = agent.improve_email(draft)
        print("\nAgent Response:")
        print("-" * 50)
        print(improved_email)
        print("-" * 50)

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
# kaizen:end:cli_interface