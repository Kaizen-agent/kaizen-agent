import os
from kaizen.model_config import set_model_config

def set_kaizen_test_agent_config():
    """Set the Kaizen test_agent configuration using the current GOOGLE_API_KEY."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY environment variable is not set")
        return False
    
    try:
        set_model_config(
            component="test_agent",
            model_type="gemini-2.5-flash-preview-05-20",
            api_key=api_key,
            provider="google"
        )
        print("✅ Successfully set Kaizen test_agent configuration")
        return True
    except Exception as e:
        print(f"❌ Error setting Kaizen configuration: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nSetting Kaizen Configuration...")
    print("-" * 50)
    success = set_kaizen_test_agent_config()
    
    if success:
        print("\nConfiguration has been updated. You can verify it by running test_api_key.py again.")
    else:
        print("\nFailed to update configuration. Please check the error message above.") 