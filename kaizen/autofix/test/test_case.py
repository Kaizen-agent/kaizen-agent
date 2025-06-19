"""Test case and evaluation implementation for Kaizen."""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import logging
import json
import os
from pathlib import Path
import google.generativeai as genai
from pydantic import BaseModel, Field, validator
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """Enum for test status values."""
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    ERROR = 'error'
    COMPLETED = 'completed'
    UNKNOWN = 'unknown'

@dataclass
class TestCase:
    """Test case configuration."""
    name: str
    input: Dict[str, Any]
    expected_output: Any
    assertions: List[Dict[str, Any]]  # List of assertions to check
    llm_evaluation: Dict[str, Any]  # LLM evaluation criteria

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create a TestCase instance from a dictionary."""
        return cls(
            name=data['name'],
            input=data['input'],
            expected_output=data.get('expected_output'),
            assertions=data.get('assertions', []),
            llm_evaluation=data.get('evaluation', {})
        )

class EvaluationResponse(BaseModel):
    """Schema for LLM evaluation response."""
    status: str = Field(..., pattern="^(passed|failed)$")
    evaluation: str
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)

    @validator('status')
    def validate_status(cls, v):
        if v not in ['passed', 'failed']:
            raise ValueError('Status must be either "passed" or "failed"')
        return v

class LLMConfig:
    """Configuration for LLM evaluation."""
    def __init__(self, config_path: Optional[str] = None):
        self.model_name = os.getenv('LLM_MODEL_NAME', 'gemini-2.5-flash-preview-05-20')
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Load additional config if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}

class PromptBuilder:
    """Builds evaluation prompts for LLM."""
    
    @staticmethod
    def build_evaluation_prompt(test_case: TestCase, actual_output: Any) -> str:
        """Create a structured evaluation prompt.
        
        If expected_output is None, the evaluation will be based solely on the criteria
        and rules provided in the test case configuration.
        """
        criteria = test_case.llm_evaluation
        logger.info(f"EVALUATION CRITERIA: {criteria}")
        
        prompt_parts = [
            "You are an expert test evaluator. Please evaluate the following test result:",
            f"\nTest Case: {test_case.name}",
            f"\nActual Output: {json.dumps(actual_output, indent=2)}"
        ]
        
        if test_case.expected_output is not None:
            prompt_parts.append(f"\nExpected Output: {json.dumps(test_case.expected_output, indent=2)}")
        
        prompt_parts.extend([
            f"\nEvaluation Criteria:",
            f"{json.dumps(criteria, indent=2)}",
            "\nPlease provide your evaluation in the following JSON format:",
            """{
                "status": "passed" or "failed",
                "evaluation": "detailed evaluation of the output",
                "reasoning": "explanation of your decision",
                "confidence": <float between 0 and 1>
            }"""
        ])
        
        focus_points = [
            "1. If the output meets all specified criteria"
        ]
        
        if test_case.expected_output is not None:
            focus_points.insert(0, "1. Whether the actual output matches the expected output")
            # Adjust numbering for remaining points
            focus_points[1] = "2. If the output meets all specified criteria"
            focus_points.extend([
                "3. Any potential issues or improvements",
                "4. Your confidence level in the evaluation"
            ])
        else:
            focus_points.extend([
                "2. Any potential issues or improvements",
                "3. Your confidence level in the evaluation"
            ])
        
        prompt_parts.append("\nFocus on:")
        prompt_parts.extend(focus_points)
        
        return "\n".join(prompt_parts)

class LLMEvaluator:
    """Evaluates test results using LLM."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize the LLM model with proper configuration."""
        try:
            genai.configure(api_key=self.config.api_key)
            self.model = genai.GenerativeModel(self.config.model_name)
        except Exception as e:
            logger.error(f"Failed to initialize LLM model: {str(e)}")
            raise RuntimeError(f"LLM initialization failed: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def evaluate_result(self, test_case: TestCase, actual_output: Any) -> Dict[str, Any]:
        """
        Evaluate test result using LLM with retry logic.
        
        Args:
            test_case: Test case configuration
            actual_output: Actual output from the test
            
        Returns:
            Dict containing evaluation results
        """
        try:
            prompt = PromptBuilder.build_evaluation_prompt(test_case, actual_output)
            response = self.model.generate_content(prompt)
            
            evaluation_result = self._parse_llm_response(response.text)
            return self._format_evaluation_result(evaluation_result)
            
        except Exception as e:
            logger.error(f"Error in LLM evaluation: {str(e)}")
            return {
                'status': TestStatus.ERROR.value,
                'error': str(e)
            }
    
    def _parse_llm_response(self, response_text: str) -> EvaluationResponse:
        """Parse and validate the LLM response."""
        try:
            # Extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start < 0 or json_end <= json_start:
                raise ValueError("No valid JSON found in response")
                
            json_str = response_text[json_start:json_end]
            response_data = json.loads(json_str)
            
            # Validate response against schema
            return EvaluationResponse(**response_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in LLM response: {str(e)}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise
    
    def _format_evaluation_result(self, evaluation: EvaluationResponse) -> Dict[str, Any]:
        """Format the evaluation result for the response."""
        return {
            'status': evaluation.status,
            'evaluation': evaluation.evaluation,
            'reasoning': evaluation.reasoning,
            'confidence': evaluation.confidence
        }

class AssertionRunner:
    """Runs assertions on test results."""
    
    @staticmethod
    def run_assertions(assertions: List[Dict], actual_output: Any) -> List[Dict]:
        """Run assertions on the test output.
        
        Args:
            assertions: List of assertions to run
            actual_output: The actual output to test against
            
        Returns:
            List of assertion results
        """
        # If no assertions provided, return empty list
        if not assertions:
            return []
            
        results = []
        for assertion in assertions:
            try:
                assertion_type = assertion['type']
                expected = assertion['expected']
                
                if assertion_type == 'equals':
                    passed = actual_output == expected
                elif assertion_type == 'contains':
                    passed = expected in actual_output
                elif assertion_type == 'matches':
                    import re
                    passed = bool(re.match(expected, str(actual_output)))
                elif assertion_type == 'type':
                    passed = isinstance(actual_output, eval(expected))
                else:
                    raise ValueError(f"Unknown assertion type: {assertion_type}")
                    
                results.append({
                    'type': assertion_type,
                    'expected': expected,
                    'actual': actual_output,
                    'passed': passed
                })
            except Exception as e:
                results.append({
                    'type': assertion_type,
                    'error': str(e),
                    'passed': False
                })
        return results 