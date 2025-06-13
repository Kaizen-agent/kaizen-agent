from typing import Dict, Optional
from datetime import datetime
from base_agent import BaseLLMAgent

class ConfirmationHandler(BaseLLMAgent):
    """Handles the final confirmation and summary of the travel plan using LLM."""
    
    def __init__(self, api_key: str):
        system_prompt = """You are a travel planning assistant helping users finalize their travel plans.
        Your role is to:
        1. Summarize the complete travel plan in a clear, organized way
        2. Help users make final adjustments
        3. Confirm all details are correct
        4. Provide next steps and recommendations
        
        Be thorough but concise, and always maintain a helpful, professional tone."""
        
        super().__init__(api_key, system_prompt)
    
    def generate_summary(self,
                        destination: str,
                        start_date: datetime,
                        end_date: datetime,
                        preferences: list,
                        budget: str,
                        itinerary: Optional[str] = None) -> str:
        """
        Generate a summary of the travel plan.
        Returns a formatted string with the complete summary.
        """
        prompt = f"""Please summarize this travel plan and ask for confirmation:
        
        Destination: {destination}
        Dates: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}
        Duration: {(end_date - start_date).days + 1} days
        Budget: {budget}
        Interests: {', '.join(preferences)}
        
        Detailed Itinerary:
        {itinerary if itinerary else 'Not yet created'}
        
        Please:
        1. Summarize the key points
        2. Highlight any potential concerns
        3. Ask if the user wants to:
           - Confirm the plan
           - Make adjustments
           - Start over
           - Save for later
        4. Provide next steps based on their choice"""
        
        return self._call_llm(prompt)
    
    def handle_confirmation(self, response: str) -> Dict[str, str]:
        """
        Process the user's confirmation response.
        Returns a dictionary with the action and any additional information.
        """
        prompt = f"""Based on this user response:
        "{response}"
        
        Determine their intent and respond in JSON format:
        {{
            "action": "confirm|adjust|restart|save|unknown",
            "message": "appropriate response message",
            "details": "any additional information or clarification needed"
        }}"""
        
        try:
            import json
            result = json.loads(self._call_llm(prompt))
            return result
        except Exception as e:
            return {
                'action': 'unknown',
                'message': 'I\'m not sure what you\'d like to do. Could you please clarify?',
                'details': str(e)
            } 