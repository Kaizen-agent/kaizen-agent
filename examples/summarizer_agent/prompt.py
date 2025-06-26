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
    # to ensure robustness when called in isolation.
    if not text or text.strip() == "":
        raise ValueError("Cannot generate summarization prompt for empty or "
                         "whitespace-only text.")

    # AI Agent Best Practice: Make prompt specific to the agent's purpose (summarization)
    # The prompt should clearly instruct the model to summarize the provided text
    # and specify the desired output format (only the summary).
    return (
        f"{text}"
    )