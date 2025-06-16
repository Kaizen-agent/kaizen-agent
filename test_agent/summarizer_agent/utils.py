import os
import google.generativeai as genai
from typing import Optional

def call_gemini_llm(prompt: str) -> str:
    """
    Call the Gemini 2.5 Flash model with the given prompt.
    
    Args:
        prompt (str): The prompt to send to the model
        
    Returns:
        str: The model's response
        
    Raises:
        ValueError: If GOOGLE_API_KEY is not set
        Exception: For any other API or model errors
    """
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
        return response.text
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {str(e)}")