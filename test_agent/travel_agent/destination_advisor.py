from typing import List, Optional
from base_agent import BaseLLMAgent

class DestinationAdvisor(BaseLLMAgent):
    """Provides destination recommendations using LLM."""
    
    def __init__(self, api_key: str):
        system_prompt = """You are a knowledgeable travel advisor with expertise in global destinations.
        Your role is to provide personalized travel recommendations based on user preferences and constraints.
        Be specific, practical, and consider factors like:
        - Season and weather
        - Cultural events and festivals
        - Local customs and etiquette
        - Safety considerations
        - Budget implications
        - Accessibility and transportation
        
        Format your responses in a clear, structured way with sections for:
        1. Why this destination matches their preferences
        2. Best time to visit
        3. Estimated budget range
        4. Key attractions and activities
        5. Practical tips and considerations"""
        
        super().__init__(api_key, system_prompt)
    
    def get_recommendations(self, 
                          preferences: List[str],
                          budget: Optional[str] = None,
                          time_of_year: Optional[str] = None) -> str:
        """
        Get destination recommendations based on preferences and constraints.
        Returns a formatted string with recommendations.
        """
        prompt = f"""Based on these preferences:
        - Interests: {', '.join(preferences)}
        - Budget: {budget if budget else 'Not specified'}
        - Time of year: {time_of_year if time_of_year else 'Not specified'}
        
        Suggest 3 destinations that would be perfect for this traveler.
        For each destination, explain why it matches their preferences and provide practical details."""
        
        return self._call_llm(prompt)
    
    def refine_destination(self, destination: str, preferences: List[str]) -> str:
        """
        Provide specific information about a chosen destination.
        Returns a formatted string with destination details.
        """
        prompt = f"""Provide detailed information about {destination} for a traveler with these interests:
        {', '.join(preferences)}
        
        Include specific recommendations for:
        1. Best neighborhoods/areas to stay
        2. Must-see attractions
        3. Local cuisine and restaurants
        4. Transportation options
        5. Cultural considerations
        6. Hidden gems and local secrets
        7. Safety tips
        8. Best times to visit specific attractions"""
        
        return self._call_llm(prompt) 