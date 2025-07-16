#!/usr/bin/env python3
"""Test the enhanced code extractor functionality."""

import sys
import os
from pathlib import Path

# Add the kaizen package to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.cli.commands.utils.code_extractor import extract_relevant_functions, extract_targeted_functions

def test_enhanced_extractor():
    """Test the enhanced code extractor with agent configuration."""
    
    # Sample code with imports, classes, and functions
    sample_code = '''
import os
import sys
from typing import Dict, List, Optional
import google.generativeai as genai

def helper_function():
    """A helper function."""
    return "helper"

class EmailAgent:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        self.system_prompt = "Improve this email draft."
    
    def improve_email(self, email_draft):
        full_prompt = f"{self.system_prompt}\\n\\nEmail draft:\\n{email_draft}\\n\\nImproved version:"
        response = self.model.generate_content(full_prompt)
        return response.text

def another_helper():
    """Another helper function."""
    return "another"

class TextAnalyzer:
    def __init__(self):
        self.name = "TextAnalyzer"
    
    def analyze_text(self, text):
        return {"sentiment": "positive"}
'''

    # Test with agent configuration
    agent_config = {
        'agent': {
            'module': 'my_agent',
            'class': 'EmailAgent',
            'method': 'improve_email',
            'fallback_to_function': True
        }
    }
    
    print("Testing enhanced code extractor...")
    print("=" * 50)
    
    # Extract with agent config
    relevant_sections = extract_relevant_functions(sample_code, agent_config=agent_config)
    
    print(f"Found {len(relevant_sections)} relevant sections:")
    for name, code in relevant_sections.items():
        print(f"\\n--- {name} ---")
        print(code[:200] + "..." if len(code) > 200 else code)
    
    # Test without agent config (fallback behavior)
    print("\\n" + "=" * 50)
    print("Testing without agent config (fallback behavior):")
    
    fallback_sections = extract_relevant_functions(sample_code)
    
    print(f"Found {len(fallback_sections)} sections in fallback mode:")
    for name, code in fallback_sections.items():
        print(f"\\n--- {name} ---")
        print(code[:200] + "..." if len(code) > 200 else code)

if __name__ == "__main__":
    test_enhanced_extractor() 