def get_prompt(text: str) -> str:
    """
    Generate a prompt for the Gemini model.
    
    Args:
        text (str): The user's input text
        
    Returns:
        str: The formatted prompt
    """
    return f"Please respond to the following user message:\n\n{text}" 
