from test_agent.summarizer_agent.agent import SummarizerAgent

def main():
    try:
        # Get user input
        user_input = input("You: ").strip()
        
        # Get agent response
        response = SummarizerAgent.run(user_input)
        
        # Print response
        print(f"Agent: {response}")
        
    except ValueError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
