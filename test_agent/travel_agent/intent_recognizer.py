from typing import Dict, Optional
from datetime import datetime
from base_agent import BaseLLMAgent
import json
import re

class IntentRecognizer(BaseLLMAgent):
    """Recognizes user intents using LLM."""
    
    def __init__(self, api_key: str):
        system_prompt = """You are an intent recognition system for a travel planning assistant.
        Your task is to identify the following information from user messages:
        - Destination (where they want to go)
        - Dates (when they want to travel)
        - Preferences (what they like to do)
        - Budget (how much they want to spend)
        
        You MUST respond with a valid JSON object in this exact format:
        {
            "destination": "extracted destination or null",
            "start_date": "MM/DD/YYYY or null",
            "end_date": "MM/DD/YYYY or null",
            "preferences": ["list", "of", "preferences"] or [],
            "budget": "budget amount or null"
        }
        
        Rules:
        1. Always return valid JSON
        2. Use null for missing information
        3. For preferences, return an array even if empty
        4. For dates, use MM/DD/YYYY format
        5. If the message is just a location name, set it as the destination
        6. If the message is unclear, return all fields as null except preferences as empty array
        7. For dates, understand various formats and convert them to MM/DD/YYYY
        8. If a date is provided without context, assume it's the start date if no start date exists, or the end date if a start date exists"""
        
        super().__init__(api_key, system_prompt)
    
    def _is_date(self, text: str) -> bool:
        """Check if the text is a date in various formats."""
        # Try different date formats
        date_formats = [
            '%m/%d/%Y', '%m-%d-%Y',  # MM/DD/YYYY or MM-DD-YYYY
            '%d/%m/%Y', '%d-%m-%Y',  # DD/MM/YYYY or DD-MM-YYYY
            '%Y/%m/%d', '%Y-%m-%d',  # YYYY/MM/DD or YYYY-MM-DD
            '%m%d%Y', '%d%m%Y', '%Y%m%d'  # MMDDYYYY, DDMMYYYY, YYYYMMDD
        ]
        
        for fmt in date_formats:
            try:
                datetime.strptime(text, fmt)
                return True
            except ValueError:
                continue
        return False
    
    def _parse_date(self, text: str) -> Optional[str]:
        """Parse date from text in various formats to MM/DD/YYYY."""
        date_formats = [
            ('%m/%d/%Y', '%m/%d/%Y'),
            ('%m-%d-%Y', '%m/%d/%Y'),
            ('%d/%m/%Y', '%m/%d/%Y'),
            ('%d-%m-%Y', '%m/%d/%Y'),
            ('%Y/%m/%d', '%m/%d/%Y'),
            ('%Y-%m-%d', '%m/%d/%Y'),
            ('%m%d%Y', '%m/%d/%Y'),
            ('%d%m%Y', '%m/%d/%Y'),
            ('%Y%m%d', '%m/%d/%Y')
        ]
        
        for input_fmt, output_fmt in date_formats:
            try:
                date = datetime.strptime(text, input_fmt)
                return date.strftime(output_fmt)
            except ValueError:
                continue
        return None
    
    def recognize(self, message: str, current_state: Optional[Dict] = None) -> Dict[str, Optional[str]]:
        """
        Recognize intents from the user message using LLM.
        Returns a dictionary of intent types and their values.
        """
        try:
            message = message.strip()
            
            # Prepare context for LLM
            context = ""
            if current_state:
                context = f"""Current state:
                Destination: {current_state.get('destination', 'Not set')}
                Start Date: {current_state.get('start_date', 'Not set')}
                End Date: {current_state.get('end_date', 'Not set')}
                Preferences: {', '.join(current_state.get('preferences', []))}
                Budget: {current_state.get('budget', 'Not set')}
                
                User message: {message}
                
                Please update the state based on the user's message, maintaining any existing valid information."""
            
            # For simple date inputs, use LLM to determine if it's start or end date
            if self._is_date(message):
                prompt = f"""Given this date input: {message}
                And the current state: {context if context else 'No existing state'}
                
                Determine if this is a start date or end date and respond with a JSON object containing only the relevant date field."""
                
                response = self._call_llm(prompt)
                try:
                    date_intent = json.loads(response)
                    parsed_date = self._parse_date(message)
                    if parsed_date:
                        if 'start_date' in date_intent:
                            return {"start_date": parsed_date, "destination": None, "end_date": None, "preferences": [], "budget": None}
                        elif 'end_date' in date_intent:
                            return {"end_date": parsed_date, "destination": None, "start_date": None, "preferences": [], "budget": None}
                except json.JSONDecodeError:
                    pass
            
            # For simple destination inputs
            if message and not any(word in message.lower() for word in ['when', 'date', 'budget', 'like', 'prefer']):
                # Check if it's not a date before treating as destination
                if not self._is_date(message):
                    return {
                        "destination": message,
                        "start_date": None,
                        "end_date": None,
                        "preferences": [],
                        "budget": None
                    }
            
            # For complex inputs, use LLM with context
            prompt = f"{context}\n\nUser message: {message}"
            response = self._call_llm(prompt)
            
            # Try to parse the response as JSON
            try:
                intents = json.loads(response)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    try:
                        intents = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        return self._get_empty_intents()
                else:
                    return self._get_empty_intents()
            
            # Convert dates to datetime objects if present
            if intents.get('start_date') and intents['start_date'] != 'null':
                try:
                    intents['start_date'] = datetime.strptime(intents['start_date'], '%m/%d/%Y')
                except ValueError:
                    intents['start_date'] = None
                    
            if intents.get('end_date') and intents['end_date'] != 'null':
                try:
                    intents['end_date'] = datetime.strptime(intents['end_date'], '%m/%d/%Y')
                except ValueError:
                    intents['end_date'] = None
            
            # Ensure all required fields are present
            return {
                "destination": intents.get('destination'),
                "start_date": intents.get('start_date'),
                "end_date": intents.get('end_date'),
                "preferences": intents.get('preferences', []),
                "budget": intents.get('budget')
            }
            
        except Exception as e:
            print(f"Error in intent recognition: {str(e)}")
            return self._get_empty_intents()
    
    def _get_empty_intents(self) -> Dict[str, Optional[str]]:
        """Return empty intents structure."""
        return {
            "destination": None,
            "start_date": None,
            "end_date": None,
            "preferences": [],
            "budget": None
        } 