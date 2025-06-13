```python
import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# kaizen:start:email_agent
class EmailAgent:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the EmailAgent with OpenAI API key."""
        load_dotenv()  # Load environment variables from .env file
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set it as OPENAI_API_KEY environment variable or pass it to the constructor.")
        
        self.client = OpenAI(api_key=self.api_key)

    def improve_email(self, draft: str) -> str:
        """
        Improve the given email draft using OpenAI's API.
        
        Args:
            draft (str): The original email draft to improve
            
        Returns:
            str: The improved email draft
        """
        prompt = f"Please improve the following email draft. Make it more professional, clear, and effective while maintaining its original intent. Here's the draft:\n\n{draft}\n\nImproved version:"

        response = self.client.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].text.strip()
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
```