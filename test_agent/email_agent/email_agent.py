import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv
import sys
import unittest
from unittest.mock import patch, MagicMock
import io

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
            str: The improved email draft or an error message if not a valid email.
        """
        if not draft or not draft.strip():
            raise ValueError("Email draft cannot be empty or contain only whitespace.")
            
        # Add safety instructions and strict output formatting to the prompt
        # The prompt is modified to handle two cases:
        # 1. If the input is not an email draft, return a specific error message.
        # 2. If it is an email, improve it professionally, without extra conversational text.
        prompt = f"""You are an AI assistant specialized in improving email drafts.

        Your primary goal is to take a given text and, if it is a valid email draft, improve its professionalism, clarity, and effectiveness.

        **Strict Instructions:**
        1.  **If the provided text is NOT an email draft** (e.g., it's a general question, a random sentence, a non-email-related query, etc.), you MUST respond with the EXACT phrase: "I'm sorry, I can't help with that." Do NOT add any other text, explanations, or conversational elements in this case.
        2.  **If the provided text IS an email draft**, you will improve it.
            *   Maintain the original intent of the draft.
            *   Enhance its professional tone and language.
            *   Ensure clear and concise communication.
            *   Apply proper email etiquette.
            *   Correct any grammar errors, spelling mistakes, or punctuation issues.
            *   The improved version should ONLY contain the email draft itself. Do NOT include any preambles, introductory phrases like "Improved version:", conversational text, or explanations before or after the email. Just the polished email.

        Here is the text to process:

        {draft}

        Your response:"""

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
# kaizen:end:cli_interface

# kaizen:start:test_runner
class TestRunner(unittest.TestCase):
    def setUp(self):
        """Set up environment for tests."""
        load_dotenv() # Ensure .env is loaded for tests too
        self.temp_file_name = "test_draft.txt"
        self.original_stdout = sys.stdout
        self.captured_output = io.StringIO()
        sys.stdout = self.captured_output

        # Conditionally mock EmailAgent if API key is not set
        if not os.getenv("GOOGLE_API_KEY"):
            # Mock EmailAgent and its improve_email method
            # This patch needs to be active during the main() call
            self.email_agent_patch = patch('__main__.EmailAgent')
            self.mock_email_agent_class = self.email_agent_patch.start()
            self.mock_agent_instance = MagicMock()
            self.mock_email_agent_class.return_value = self.mock_agent_instance
            self.mock_agent_instance.improve_email.return_value = "This is an improved email."
        else:
            self.email_agent_patch = None # Indicate no patch was started

    def tearDown(self):
        """Clean up after tests."""
        sys.stdout = self.original_stdout # Restore stdout
        if os.path.exists(self.temp_file_name):
            os.remove(self.temp_file_name)
        if self.email_agent_patch:
            self.email_agent_patch.stop() # Stop the patch if it was started

    def _get_output(self):
        """Helper to get and clear captured output."""
        return self.captured_output.getvalue().strip()

    def test_valid_email_from_file(self):
        """Test improving a valid email provided via file."""
        email_draft = "Hi team, Can we meat next week to discuss the project?"
        expected_output_header = "Improved Email:\n--------------------------------------------------"

        # Write draft to a temporary file
        with open(self.temp_file_name, 'w') as f:
            f.write(email_draft)

        # Simulate command-line arguments
        with patch('sys.argv', ['main.py', '--file', self.temp_file_name]):
            # Run the main function
            main()

        output = self._get_output()
        
        self.assertIn(expected_output_header, output)

        if os.getenv("GOOGLE_API_KEY"):
            # If real agent, expect a professionally improved email (not the mock one)
            self.assertNotIn("This is an improved email.", output)
            self.assertIn("meet next week", output) # Check for common correction
            self.assertIn("Hi team,", output) # Check original intent retention
        else:
            # If mocked, expect the predefined mock response
            self.assertIn("This is an improved email.", output)
            # Verify that improve_email was called with the correct content
            self.mock_agent_instance.improve_email.assert_called_once_with(email_draft)

# This part ensures the tests run when the script is executed
if __name__ == "__main__":
    # Only pass the program name to unittest.main to avoid parsing test-specific args
    unittest.main(argv=sys.argv[:1])
# kaizen:end:test_runner