"""
LLM-based evaluation module for Kaizen Agent.
"""
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from .agent_runners import TestLogger
from .config import Config

class LLMEvaluator:
    """Evaluates test results using LLMs."""
    
    def __init__(self, provider: str = "google", logger: Optional[TestLogger] = None):
        self.provider = provider
        self.config = Config()
        self.api_key = self.config.get_api_key(provider)
        if not self.api_key:
            raise ValueError(f"API key not found for provider: {provider}. Please add it to your .env file.")
        
        self.logger = logger or TestLogger()
        self._setup_provider()
    
    def _setup_provider(self):
        """Set up the LLM provider client."""
        if self.provider == "google":
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def evaluate(self, code: str, results: Dict[str, Any], criteria: List[Dict[str, str]]) -> Dict[str, Any]:
        """Evaluate the code and results against the given criteria."""
        evaluation_results = {}
        
        for criterion in criteria:
            name = criterion["name"]
            description = criterion["description"]
            
            self.logger.logger.debug(f"Evaluating criterion: {name}")
            
            # Prepare the prompt for the LLM
            prompt = self._create_evaluation_prompt(code, results, name, description)
            
            # Get evaluation from LLM
            evaluation = self._get_llm_evaluation(prompt)
            
            evaluation_results[name] = {
                "status": evaluation["status"],
                "score": evaluation["score"],
                "feedback": evaluation["feedback"],
                "details": evaluation["details"]
            }
        
        return {
            "status": "passed" if all(r["status"] == "passed" for r in evaluation_results.values()) else "failed",
            "criteria": evaluation_results
        }
    
    def _create_evaluation_prompt(self, code: str, results: Dict[str, Any], 
                                criterion_name: str, criterion_description: str) -> str:
        """Create a prompt for the LLM evaluation."""
        return f"""You are an expert code reviewer evaluating code against specific criteria.

Code to evaluate:
```python
{code}
```

Analysis results:
{results}

Criterion: {criterion_name}
Description: {criterion_description}

Please evaluate the code against this criterion and provide:
1. A pass/fail status
2. A score from 0-100
3. Detailed feedback
4. Specific examples from the code that support your evaluation

Format your response as a JSON object with the following structure:
{{
    "status": "passed" or "failed",
    "score": number between 0 and 100,
    "feedback": "detailed feedback",
    "details": ["specific example 1", "specific example 2", ...]
}}"""
    
    def _get_llm_evaluation(self, prompt: str) -> Dict[str, Any]:
        """Get evaluation from the LLM provider."""
        try:
            if self.provider == "google":
                response = self.model.generate_content(prompt)
                evaluation = response.text
            
            # Parse the JSON response
            import json
            return json.loads(evaluation)
            
        except Exception as e:
            self.logger.logger.error(f"Error getting LLM evaluation: {str(e)}")
            return {
                "status": "error",
                "score": 0,
                "feedback": f"Error during evaluation: {str(e)}",
                "details": []
            } 