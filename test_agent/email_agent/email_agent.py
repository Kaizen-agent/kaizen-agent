import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

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
            # Test the configuration
            self.model.generate_content("Test")
            print("Debug: EmailAgent: Successfully configured Google API")
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
        if not draft:
            return "Please provide either --draft or --file argument"
            
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
            print(f"Debug: Prompt: {prompt}")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,  # Increased token limit
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
            print(f"Debug: Response: {response}")
            
            # Check for safety issues
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    raise ValueError(f"Content was blocked due to: {response.prompt_feedback.block_reason}")
            
            # Check for candidates
            if not hasattr(response, 'candidates') or not response.candidates:
                raise ValueError("No response candidates were generated")
            
            # Get the first candidate
            candidate = response.candidates[0]
            
            # Check finish reason
            if hasattr(candidate, 'finish_reason'):
                if candidate.finish_reason == "MAX_TOKENS":
                    raise ValueError("Response was cut off due to token limit. Please try with a shorter email draft.")
                elif candidate.finish_reason == "BLOCKED":
                    raise ValueError("Content was blocked by safety filters")
            
            # Try to get the text content
            if hasattr(candidate, 'content'):
                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                    return candidate.content.parts[0].text.strip()
                elif hasattr(candidate.content, 'text'):
                    return candidate.content.text.strip()
            
            raise ValueError("Could not extract text from the response")
            
        except Exception as e:
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
            with open(args.file, 'r') as f:
                draft = f.read()

        if draft is None:
            print("Please enter your email draft (press Ctrl+D or Ctrl+Z on Windows when finished):")
            draft = ""
            try:
                while True:
                    line = input()
                    draft += line + "\n"
            except EOFError:
                pass

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
