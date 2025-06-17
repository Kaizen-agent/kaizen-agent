# kaizen:start:email_agent
class EmailAgent:
    def __init__(self, api_key=None):
        """Initialize the EmailAgent with Google API key."""
        print("DEBUG: EmailAgent __init__ started")
        print(f"DEBUG: Exception type = {type(Exception)}")
        print(f"DEBUG: ValueError type = {type(ValueError)}")
        
        # Minimal init - no imports, no API calls
        self.api_key = api_key or "dummy_key"
        print("DEBUG: EmailAgent __init__ completed")

    def improve_email(self, draft):
        """
        Improve the given email draft using Gemini's API.
        
        Args:
            draft (str): The original email draft to improve
            
        Returns:
            str: The improved email draft
        """
        print("DEBUG: improve_email called")
        # Just return a dummy improved version
        return f"IMPROVED: {draft}"
# kaizen:end:email_agent