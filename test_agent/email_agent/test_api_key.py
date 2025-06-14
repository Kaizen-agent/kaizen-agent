import os
from email_agent import EmailAgent
from kaizen.model_config import get_model_config

def test_email_agent_api_key():
    """Test if the email agent can initialize with the current API key."""
    try:
        agent = EmailAgent()
        print("✅ Email Agent API Key (GOOGLE_API_KEY) is working")
        return True
    except Exception as e:
        print(f"❌ Email Agent API Key Error: {str(e)}")
        return False

def test_kaizen_config():
    """Test if the Kaizen configuration has a valid API key for test_agent."""
    try:
        config = get_model_config("test_agent")
        if config and config.api_key:
            print("✅ Kaizen test_agent configuration found")
            return True
        else:
            print("❌ Kaizen test_agent configuration missing or empty")
            return False
    except Exception as e:
        print(f"❌ Kaizen Configuration Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nChecking API Key Configuration...")
    print("-" * 50)
    
    # Check environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        print(f"GOOGLE_API_KEY is set (length: {len(api_key)})")
    else:
        print("GOOGLE_API_KEY is not set")
    
    # Test email agent
    print("\nTesting Email Agent API Key:")
    email_agent_ok = test_email_agent_api_key()
    
    # Test Kaizen config
    print("\nTesting Kaizen Configuration:")
    kaizen_config_ok = test_kaizen_config()
    
    print("\nSummary:")
    print("-" * 50)
    print(f"Email Agent API Key: {'✅ Working' if email_agent_ok else '❌ Not Working'}")
    print(f"Kaizen Configuration: {'✅ Working' if kaizen_config_ok else '❌ Not Working'}") 