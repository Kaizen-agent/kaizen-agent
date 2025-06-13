import os
from typing import Optional
from state import ConversationState
from intent_recognizer import IntentRecognizer
from destination_advisor import DestinationAdvisor
from itinerary_builder import ItineraryBuilder
from confirmation_handler import ConfirmationHandler

class TravelAgent:
    """Main travel planning agent that coordinates all components."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the travel agent with all its components."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set it as OPENAI_API_KEY environment variable or pass it to the constructor.")
            
        self.state = ConversationState()
        self.intent_recognizer = IntentRecognizer(self.api_key)
        self.destination_advisor = DestinationAdvisor(self.api_key)
        self.itinerary_builder = ItineraryBuilder(self.api_key)
        self.confirmation_handler = ConfirmationHandler(self.api_key)
        
    def reply(self, user_input: str) -> str:
        """Process user input and generate a response."""
        try:
            # Check if we're in confirmation state
            if self.state.is_complete():
                confirmation = self.confirmation_handler.handle_confirmation(user_input, self.state)
                if confirmation['action'] == 'confirm':
                    return "Great! I'll save your travel plan. Have a wonderful trip!"
                elif confirmation['action'] == 'adjust':
                    self.state = ConversationState()  # Reset state for new planning
                    return "Let's plan your trip again. What would you like to do?"
                elif confirmation['action'] == 'restart':
                    self.state = ConversationState()  # Reset state
                    return "Let's start over. What would you like to do?"
                elif confirmation['action'] == 'save':
                    return "I'll save your travel plan. Have a wonderful trip!"
                else:
                    return "I'm not sure what you'd like to do. Would you like to confirm, adjust, or start over?"
            
            # Recognize intents from user input
            intents = self.intent_recognizer.recognize(user_input, self.state.to_dict())
            
            # Update state with recognized intents
            if intents['destination']:
                self.state.update_destination(intents['destination'])
            if intents['start_date']:
                self.state.update_start_date(intents['start_date'])
            if intents['end_date']:
                self.state.update_end_date(intents['end_date'])
            if intents['preferences']:
                self.state.update_preferences(intents['preferences'])
            if intents['budget']:
                self.state.update_budget(intents['budget'])
            
            # Generate response based on state completeness
            if not self.state.destination:
                return "Where would you like to go?"
            elif not self.state.start_date:
                return f"When would you like to start your trip to {self.state.destination}? Please provide the start date in MM/DD/YYYY format."
            elif not self.state.end_date:
                return f"And when would you like to return from {self.state.destination}? Please provide the end date in MM/DD/YYYY format."
            elif not self.state.preferences:
                return f"What kind of activities do you enjoy? For example: sightseeing, food, shopping, nature, etc."
            elif not self.state.budget:
                return "What's your budget for this trip?"
            else:
                # Generate recommendations and itinerary
                recommendations = self.destination_advisor.get_recommendations(
                    self.state.destination,
                    self.state.preferences,
                    self.state.budget
                )
                
                itinerary = self.itinerary_builder.build_itinerary(
                    self.state.destination,
                    self.state.start_date,
                    self.state.end_date,
                    self.state.preferences,
                    self.state.budget
                )
                
                # Generate confirmation summary
                summary = self.confirmation_handler.generate_summary(self.state, itinerary)
                return summary
                
        except Exception as e:
            print(f"Error in travel agent: {str(e)}")
            return "I apologize, but I encountered an error. Could you please try again?" 