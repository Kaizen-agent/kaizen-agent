import os
import google.generativeai as genai


def call_gemini_llm(prompt: str) -> str:
    """
    Call the Gemini 2.5 Flash model with the given prompt.

    Args:
        prompt (str): The prompt to send to the model

    Returns:
        str: The model's response

    Raises:
        ValueError: If GOOGLE_API_KEY is not set or if the prompt is empty/whitespace only.
        Exception: For any other API or model errors, including cases where the LLM does not generate a meaningful text response.
    """
    # AI Agent Best Practice: Validate prompt input before sending to LLM
    if not prompt or prompt.strip() == "":
        raise ValueError("Prompt cannot be empty or whitespace only for LLM call.")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "Please set it with your Google API key."
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        response = model.generate_content(prompt)

        # AI Agent Best Practice: Handle potentially empty or non-text responses from LLM.
        # If the LLM does not generate a meaningful text response (e.g., None, empty string, or blocked),
        # raise an exception to signal a failure, rather than returning a generic string.
        if response is None:
            raise Exception("LLM response object is None.")

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise Exception(
                f"LLM response was blocked: "
                f"{response.prompt_feedback.block_reason.name}"
            )

        if not hasattr(response, 'text') or not response.text:
            # This covers cases where response.text is None or an empty string
            raise Exception("LLM did not generate a meaningful text response.")

        return response.text
    except Exception as e:
        # AI Agent Best Practice: Re-raise specific exceptions or provide context
        raise Exception(f"Error calling Gemini API: {str(e)}")