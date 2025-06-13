from typing import List
from datetime import datetime
from base_agent import BaseLLMAgent

class ItineraryBuilder(BaseLLMAgent):
    """Builds detailed travel itineraries using LLM."""
    
    def __init__(self, api_key: str):
        system_prompt = """You are a professional travel planner with expertise in creating detailed, personalized itineraries.
        Your role is to create comprehensive day-by-day travel plans that consider:
        - Opening hours and best times to visit attractions
        - Travel time between locations
        - Local transportation options
        - Meal times and restaurant recommendations
        - Cultural events and seasonal activities
        - Budget constraints
        - Physical activity levels and rest periods
        
        Format your responses with clear sections for each day, including:
        1. Morning activities
        2. Afternoon activities
        3. Evening activities
        4. Restaurant recommendations
        5. Transportation details
        6. Estimated costs
        7. Tips and considerations"""
        
        super().__init__(api_key, system_prompt)
    
    def build_itinerary(self,
                       destination: str,
                       start_date: datetime,
                       end_date: datetime,
                       preferences: List[str],
                       budget: str) -> str:
        """
        Build a detailed day-by-day itinerary.
        Returns a formatted string with the complete itinerary.
        """
        duration = (end_date - start_date).days + 1
        
        prompt = f"""Create a detailed {duration}-day itinerary for {destination} with these details:
        - Travel dates: {start_date.strftime('%B %d')} to {end_date.strftime('%B %d')}
        - Interests: {', '.join(preferences)}
        - Budget: {budget}
        
        For each day, provide:
        1. Morning activities (with timing)
        2. Afternoon activities (with timing)
        3. Evening activities (with timing)
        4. Restaurant recommendations for each meal
        5. Transportation between locations
        6. Estimated costs for each activity
        
        Also include:
        - Packing suggestions based on the season
        - Local customs and etiquette to be aware of
        - Emergency contact information
        - Weather considerations
        - Tips for avoiding crowds
        - Backup activities in case of bad weather
        
        Format the response in a clear, day-by-day structure with timing details."""
        
        return self._call_llm(prompt)
    
    def adjust_itinerary(self, current_itinerary: str, feedback: str) -> str:
        """
        Modify an existing itinerary based on feedback.
        Returns the updated itinerary.
        """
        prompt = f"""Please modify this itinerary based on the following feedback:
        
        Current itinerary:
        {current_itinerary}
        
        Feedback:
        {feedback}
        
        Provide the complete updated itinerary, maintaining the same format but incorporating the requested changes.
        Explain any major changes you made and why they improve the plan."""
        
        return self._call_llm(prompt) 