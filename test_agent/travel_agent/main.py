#!/usr/bin/env python3
# Requires: pip install openai python-dotenv

import os
from dotenv import load_dotenv
from travel_agent import TravelAgent

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def main():
    print("Welcome to the Travel Planning Assistant!")
    print("I can help you plan your next trip. Type 'bye' or 'exit' to end the conversation.")
    print("What would you like to do?")
    
    agent = TravelAgent()
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ['bye', 'exit']:
            print("\nAssistant: Thank you for using the Travel Planning Assistant. Have a great trip!")
            break
            
        if not user_input:
            print("\nAssistant: I didn't catch that. Could you please repeat?")
            continue
            
        response = agent.reply(user_input)
        print(f"\nAssistant: {response}")

if __name__ == "__main__":
    main()
