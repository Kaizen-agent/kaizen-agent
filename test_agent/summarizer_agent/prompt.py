def get_prompt(text: str) -> str:
    """
    Generate a prompt for the Gemini model, specifically for summarization.
    
    Args:
        text (str): The text to be summarized.
        
    Returns:
        str: The formatted prompt
        
    Raises:
        ValueError: If the input text is empty or whitespace only, as it cannot be summarized.
    """
    # AI Agent Best Practice: Validate input for utility functions, even if a higher layer handles it,
    # to ensure robustness when called in isolation. (Agent handles empty input, so this protects direct calls).
    if not text or text.strip() == "":
        # Fix 1: This ValueError is a valid defense for the utility function.
        # The agent.py layer handles empty input before calling this, so this won't be hit from the agent.
        raise ValueError("Cannot generate summarization prompt for empty or whitespace-only text.")
        
    # AI Agent Best Practice: Make prompt specific to the agent's purpose (summarization).
    # Provide clear instructions for summarization, including tone, focus, and desired output format.
    # The agent.py now handles non-summarization specific responses directly.
    # Fix 2: Improve the prompt for better summarization quality and adherence to expected format.
    prompt_template = f"""
    Please provide a concise and accurate summary of the following text.
    Focus on extracting the main points and key information without adding conversational filler or extraneous details.
    The summary should be well-structured and easy to understand.

    Text to summarize:
    ---
    {text}
    ---

    Summary:
    """
    return prompt_template.strip() # .strip() to remove leading/trailing whitespace from multi-line string
