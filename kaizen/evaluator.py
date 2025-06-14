"""
LLM-based evaluation module for Kaizen Agent.
"""
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from .agent_runners import TestLogger
from .config import Config
import json
import re

class LLMEvaluator:
    """Evaluates test results using LLMs."""
    
    def __init__(self, provider: str = "google", logger: Optional[TestLogger] = None):
        self.provider = provider
        self.config = Config()
        # Try both 'google' and 'gemini' as provider names for the API key
        self.api_key = self.config.get_api_key(provider) or self.config.get_api_key("google")
        if not self.api_key:
            raise ValueError(f"API key not found for provider: {provider}. Please add it to your .env file as GOOGLE_API_KEY.")
        
        self.logger = logger or TestLogger()
        self._setup_provider()
    
    def _setup_provider(self):
        """Set up the LLM provider client."""
        if self.provider in ["google", "gemini"]:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def evaluate(self, results: Dict[str, Any], criteria: List[Dict[str, str]], code: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate the results against the given criteria.
        
        Args:
            results: Dictionary containing the test results to evaluate
            criteria: List of criteria dictionaries to evaluate against
            code: Optional code string (kept for backward compatibility)
        """
        evaluation_results = {}
        total_weight = 0
        weighted_score = 0
        
        # Check if there are any outputs to evaluate
        outputs = []
        for region, result in results.items():
            if isinstance(result, dict) and 'test_cases' in result:
                for test_case in result['test_cases']:
                    if isinstance(test_case, dict) and 'output' in test_case:
                        outputs.append(test_case['output'])
        
        if not outputs:
            self.logger.logger.error("No outputs found in test results to evaluate")
            return {
                "status": "error",
                "overall_score": 0,
                "criteria": {
                    "no_outputs": {
                        "status": "error",
                        "score": 0,
                        "feedback": "No outputs found in test results to evaluate",
                        "details": [],
                        "weight": 1.0
                    }
                }
            }
        
        for criterion in criteria:
            name = criterion["name"]
            description = criterion["description"]
            weight = float(criterion.get("weight", 1.0))  # Default weight is 1.0 if not specified
            total_weight += weight
            
            self.logger.logger.debug(f"Evaluating criterion: {name} (weight: {weight})")
            self.logger.logger.debug(f"Criterion description: {description}")
            
            # Prepare the prompt for the LLM
            prompt = self._create_evaluation_prompt(results, name, description)
            self.logger.logger.debug(f"Generated prompt for {name}")
            
            # Get evaluation from LLM
            try:
                evaluation = self._get_llm_evaluation(prompt)
                self.logger.logger.debug(f"Raw LLM response for {name}: {evaluation}")
                
                if not isinstance(evaluation, dict):
                    self.logger.logger.error(f"Invalid evaluation response type for {name}: {type(evaluation)}")
                    evaluation = {
                        "status": "error",
                        "score": 0,
                        "feedback": f"Invalid evaluation response type: {type(evaluation)}",
                        "details": []
                    }
                
                evaluation_results[name] = {
                    "status": evaluation.get("status", "error"),
                    "score": evaluation.get("score", 0),
                    "feedback": evaluation.get("feedback", "No feedback provided"),
                    "details": evaluation.get("details", []),
                    "weight": weight
                }
                
                # Calculate weighted score
                weighted_score += evaluation.get("score", 0) * weight
                
                self.logger.logger.info(f"Evaluation for {name}: {evaluation_results[name]}")
                
            except Exception as e:
                self.logger.logger.error(f"Error evaluating criterion {name}: {str(e)}")
                evaluation_results[name] = {
                    "status": "error",
                    "score": 0,
                    "feedback": f"Error during evaluation: {str(e)}",
                    "details": [],
                    "weight": weight
                }
        
        # Calculate overall weighted score
        overall_score = weighted_score / total_weight if total_weight > 0 else 0
        self.logger.logger.info(f"Overall weighted score: {overall_score}")
        
        # Determine overall status
        if not evaluation_results:
            overall_status = "error"
            self.logger.logger.error("No evaluation results generated")
        elif any(r["status"] == "error" for r in evaluation_results.values()):
            overall_status = "error"
            self.logger.logger.error("Some evaluations resulted in errors")
        elif overall_score < 90:  # Fail if overall score is below 90
            overall_status = "failed"
            self.logger.logger.warning(f"Test failed with overall score: {overall_score}")
        else:
            overall_status = "passed"
            self.logger.logger.info(f"Test passed with overall score: {overall_score}")
        
        return {
            "status": overall_status,
            "overall_score": overall_score,
            "criteria": evaluation_results
        }
    
    def _create_evaluation_prompt(self, results: Dict[str, Any], 
                                criterion_name: str, criterion_description: str) -> str:
        """Create a prompt for the LLM evaluation."""
        # Extract outputs from test results
        outputs = []
        for region, result in results.items():
            if isinstance(result, dict) and 'test_cases' in result:
                for test_case in result['test_cases']:
                    if isinstance(test_case, dict) and 'output' in test_case:
                        outputs.append(test_case['output'])
        
        prompt = f"""You are an expert evaluator assessing outputs against specific criteria.

Outputs to evaluate:
{json.dumps(outputs, indent=2)}

Criterion: {criterion_name}
Description: {criterion_description}

Please evaluate the outputs against this criterion and provide:
1. A pass/fail status based on whether the outputs meet the criterion
2. A score from 0-100 indicating how well it meets the criterion
3. Detailed feedback explaining your evaluation
4. Specific examples from the outputs that support your evaluation

Format your response as a JSON object with the following structure:
{{
    "status": "passed" or "failed",
    "score": number between 0 and 100,
    "feedback": "detailed feedback",
    "details": ["specific example 1", "specific example 2", ...]
}}

IMPORTANT: Your response must be valid JSON. Do not include any additional text or explanations outside the JSON object."""

        # Log the prompt for debugging
        self.logger.logger.debug("=== LLM Evaluation Prompt ===")
        self.logger.logger.debug(f"Criterion: {criterion_name}")
        self.logger.logger.debug(f"Description: {criterion_description}")
        self.logger.logger.debug("Full prompt:")
        self.logger.logger.debug(prompt)
        self.logger.logger.debug("=== End of Prompt ===")
        
        return prompt
    
    def _get_llm_evaluation(self, prompt: str) -> Dict[str, Any]:
        """Get evaluation from the LLM provider."""
        try:
            evaluation = None
            if self.provider in ["google", "gemini"]:
                self.logger.logger.debug("Sending prompt to Gemini")
                response = self.model.generate_content(prompt)
                
                # Ensure we have a valid response
                if not response or not hasattr(response, 'text'):
                    self.logger.logger.error("Invalid response from LLM")
                    return {
                        "status": "error",
                        "score": 0,
                        "feedback": "Invalid response from LLM",
                        "details": []
                    }
                
                evaluation = response.text.strip()
                self.logger.logger.debug(f"Raw Gemini response: {evaluation}")
                
                # Try to extract JSON from the response
                try:
                    # First try parsing the entire response
                    parsed = json.loads(evaluation)
                    self.logger.logger.debug(f"Successfully parsed JSON response: {parsed}")
                    
                    # Ensure parsed is a dictionary
                    if not isinstance(parsed, dict):
                        self.logger.logger.error(f"Parsed response is not a dictionary: {type(parsed)}")
                        return {
                            "status": "error",
                            "score": 0,
                            "feedback": f"Invalid response format: expected dictionary, got {type(parsed)}",
                            "details": []
                        }
                    
                    # Validate required fields
                    required_fields = ["status", "score", "feedback"]
                    missing_fields = [field for field in required_fields if field not in parsed]
                    if missing_fields:
                        self.logger.logger.error(f"Missing required fields in response: {missing_fields}")
                        return {
                            "status": "error",
                            "score": 0,
                            "feedback": f"Missing required fields in response: {missing_fields}",
                            "details": []
                        }
                    
                    return parsed
                    
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.logger.warning(f"Failed to parse full response as JSON: {str(e)}")
                    # If that fails, try to find JSON in the response
                    json_match = re.search(r'\{.*\}', evaluation, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            if not isinstance(parsed, dict):
                                self.logger.logger.error("Extracted JSON is not a dictionary")
                                return {
                                    "status": "error",
                                    "score": 0,
                                    "feedback": "Invalid response format: extracted JSON is not a dictionary",
                                    "details": []
                                }
                            self.logger.logger.debug(f"Successfully parsed JSON from partial response: {parsed}")
                            return parsed
                        except (json.JSONDecodeError, ValueError) as e:
                            self.logger.logger.error(f"Failed to parse extracted JSON: {str(e)}")
                    
                    # If we get here, we couldn't parse any valid JSON
                    self.logger.logger.error("Could not find valid JSON in LLM response")
                    return {
                        "status": "error",
                        "score": 0,
                        "feedback": "LLM response could not be parsed as valid JSON",
                        "details": [f"Raw response: {evaluation}"]
                    }
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
            
        except Exception as e:
            self.logger.logger.error(f"Error getting LLM evaluation: {str(e)}")
            return {
                "status": "error",
                "score": 0,
                "feedback": f"Error during evaluation: {str(e)}",
                "details": []
            } 