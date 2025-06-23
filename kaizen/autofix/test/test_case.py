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

from .variable_tracker import safe_serialize_value

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

def safe_serialize_evaluation_targets(evaluation_targets: Optional[List[Any]]) -> List[Dict[str, Any]]:
    """Safely serialize evaluation targets for logging.
    
    Args:
        evaluation_targets: List of evaluation targets (can be EvaluationTarget objects or dicts)
        
    Returns:
        List of serializable dictionaries
    """
    if not evaluation_targets:
        return []
    
    serialized = []
    for i, target in enumerate(evaluation_targets):
        try:
            if hasattr(target, 'to_dict'):  # EvaluationTarget object with to_dict method
                serialized.append(target.to_dict())
            elif hasattr(target, 'name'):  # EvaluationTarget object without to_dict method
                # Safely extract attributes with fallbacks
                name = getattr(target, 'name', f'target_{i}')
                source_obj = getattr(target, 'source', None)
                source = getattr(source_obj, 'value', 'unknown') if source_obj else 'unknown'
                criteria = getattr(target, 'criteria', '')
                description = getattr(target, 'description', '')
                weight = getattr(target, 'weight', 1.0)
                
                serialized.append({
                    'name': name,
                    'source': source,
                    'criteria': criteria,
                    'description': description,
                    'weight': weight
                })
            elif isinstance(target, dict):  # Dictionary format
                serialized.append(target)
            else:
                # Fallback: convert to string representation
                serialized.append({'raw_target': str(target)})
        except Exception as e:
            logger.warning(f"Failed to serialize evaluation target {i}: {e}")
            serialized.append({
                'error': f'Serialization failed: {str(e)}',
                'target_index': i,
                'target_type': type(target).__name__
            })
    
    return serialized

def safe_serialize_criteria(criteria: Any) -> Any:
    """Safely serialize criteria for logging.
    
    Args:
        criteria: Criteria object or value
        
    Returns:
        Serializable representation of criteria
    """
    try:
        if isinstance(criteria, dict):
            return criteria
        elif isinstance(criteria, list):
            return [str(item) if not isinstance(item, (dict, str, int, float, bool)) else item for item in criteria]
        elif hasattr(criteria, '__dict__'):
            return str(criteria)
        else:
            return criteria
    except Exception as e:
        logger.warning(f"Failed to serialize criteria: {e}")
        return f"<Serialization error: {str(e)}>"

@dataclass
class TestCase:
    """Test case configuration."""
    name: str
    input: Dict[str, Any]
    expected_output: Any
    assertions: List[Dict[str, Any]]  # List of assertions to check
    llm_evaluation: Dict[str, Any]  # LLM evaluation criteria
    evaluation_targets: Optional[List[Dict[str, Any]]] = None  # New flexible evaluation targets

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create a TestCase instance from a dictionary."""
        # Handle backward compatibility: convert old evaluation.criteria to evaluation_targets
        evaluation_targets = data.get('evaluation_targets', [])
        llm_evaluation = data.get('evaluation', {})
        
        # If using old format with evaluation.criteria, convert to evaluation_targets
        if not evaluation_targets and 'evaluation' in data and 'criteria' in data['evaluation']:
            logger.info("Converting old evaluation.criteria format to evaluation_targets")
            criteria_list = data['evaluation']['criteria']
            if isinstance(criteria_list, list):
                evaluation_targets = []
                for i, criteria in enumerate(criteria_list):
                    if isinstance(criteria, dict):
                        evaluation_targets.append({
                            'name': criteria.get('name', f'criteria_{i}'),
                            'criteria': criteria.get('description', ''),
                            'description': criteria.get('description', ''),
                            'source': 'return',
                            'weight': criteria.get('weight', 1.0)
                        })
                    else:
                        evaluation_targets.append({
                            'name': f'criteria_{i}',
                            'criteria': str(criteria),
                            'description': str(criteria),
                            'source': 'return',
                            'weight': 1.0
                        })
                logger.info(f"Converted {len(evaluation_targets)} evaluation targets from old format")
        
        return cls(
            name=data['name'],
            input=data['input'],
            expected_output=data.get('expected_output'),
            assertions=data.get('assertions', []),
            llm_evaluation=llm_evaluation,
            evaluation_targets=evaluation_targets
        )

class EvaluationResponse(BaseModel):
    """Schema for LLM evaluation response."""
    status: str = Field(..., pattern="^(passed|failed)$")
    evaluation: str
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    target_evaluations: Optional[Dict[str, Dict[str, Any]]] = None

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
    def build_evaluation_prompt(test_case: TestCase, actual_output: Any, tracked_values: Optional[Dict[str, Any]] = None) -> str:
        """Create a structured evaluation prompt.
        
        If expected_output is None, the evaluation will be based solely on the criteria
        and rules provided in the test case configuration.
        
        Args:
            test_case: Test case configuration
            actual_output: Actual output from the test
            tracked_values: Dictionary of tracked variable values
        """
        criteria = test_case.llm_evaluation
        evaluation_targets = test_case.evaluation_targets or []
        
        # Safely serialize for logging
        serialized_criteria = safe_serialize_criteria(criteria)
        serialized_targets = safe_serialize_evaluation_targets(evaluation_targets)
        logger.debug(f"EVALUATION CRITERIA: {serialized_criteria}")
        logger.debug(f"EVALUATION TARGETS: {serialized_targets}")
        
        prompt_parts = [
            "You are an expert test evaluator. Please evaluate the following test result:",
            f"\nTest Case: {test_case.name}",
        ]
        
        # Add tracked values if available
        if tracked_values and evaluation_targets:
            prompt_parts.append("\nTracked Output Values:")
            for target in evaluation_targets:
                try:
                    # Handle both EvaluationTarget objects and dictionaries
                    if hasattr(target, 'name'):  # EvaluationTarget object
                        target_name = target.name
                        source = target.source.value  # Get the enum value
                    else:  # Dictionary format (legacy)
                        target_name = target.get('name', 'unknown')
                        source = target.get('source', 'return')
                    
                    if source == 'return' and 'return' in tracked_values:
                        value = tracked_values['return']
                    elif source == 'variable' and target_name in tracked_values:
                        value = tracked_values[target_name]
                    else:
                        value = "Not found"
                    
                    serialized_value = safe_serialize_value(value)
                    prompt_parts.append(f"  {target_name} ({source}): {serialized_value}")
                except Exception as e:
                    logger.warning(f"Failed to process tracked value for target: {e}")
                    prompt_parts.append(f"  <Error processing target>: {str(e)}")
        else:
            # Fallback to legacy format
            serialized_output = safe_serialize_value(actual_output)
            prompt_parts.append(f"\nActual Output: {serialized_output}")
        
        if test_case.expected_output is not None:
            try:
                expected_output_json = json.dumps(test_case.expected_output, indent=2)
                prompt_parts.append(f"\nExpected Output: {expected_output_json}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize expected output: {e}")
                prompt_parts.append(f"\nExpected Output: {str(test_case.expected_output)}")
        
        # Add evaluation targets if present
        if evaluation_targets:
            prompt_parts.append("\nEvaluation Targets:")
            for i, target in enumerate(evaluation_targets, 1):
                try:
                    # Handle both EvaluationTarget objects and dictionaries
                    if hasattr(target, 'name'):  # EvaluationTarget object
                        target_name = target.name
                        criteria_text = target.criteria
                        description = target.description or ''
                    else:  # Dictionary format (legacy)
                        target_name = target.get('name', 'unknown')
                        criteria_text = target.get('criteria', 'No criteria specified')
                        description = target.get('description', '')
                    
                    prompt_parts.append(f"  {i}. {target_name}:")
                    if description:
                        prompt_parts.append(f"     Description: {description}")
                    prompt_parts.append(f"     Criteria: {criteria_text}")
                except Exception as e:
                    logger.warning(f"Failed to process evaluation target {i}: {e}")
                    prompt_parts.append(f"  {i}. <Error processing target>: {str(e)}")
        else:
            # Legacy format
            try:
                serialized_criteria_for_prompt = json.dumps(criteria, indent=2)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize criteria for prompt: {e}")
                serialized_criteria_for_prompt = str(criteria)
            
            prompt_parts.extend([
                f"\nEvaluation Criteria:",
                f"{serialized_criteria_for_prompt}"
            ])
        
        prompt_parts.extend([
            "\nPlease provide your evaluation in the following JSON format:",
            """{
                "status": "passed" or "failed",
                "evaluation": "detailed evaluation of the output",
                "reasoning": "explanation of your decision",
                "confidence": <float between 0 and 1>,
                "target_evaluations": {
                    "target_name": {
                        "status": "passed" or "failed",
                        "evaluation": "evaluation for this specific target",
                        "reasoning": "reasoning for this target"
                    }
                }
            }"""
        ])
        
        focus_points = []
        
        if evaluation_targets:
            focus_points.append("1. Evaluate each target based on its specific criteria")
            focus_points.append("2. Consider the overall quality and completeness of the output")
            focus_points.append("3. Any potential issues or improvements")
            focus_points.append("4. Your confidence level in the evaluation")
        else:
            # Legacy format
            focus_points.append("1. If the output meets all specified criteria")
            
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
    def evaluate_result(self, test_case: TestCase, actual_output: Any, tracked_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate test result using LLM with retry logic.
        
        Args:
            test_case: Test case configuration
            actual_output: Actual output from the test
            tracked_values: Dictionary of tracked variable values
            
        Returns:
            Dict containing evaluation results
        """
        try:
            prompt = PromptBuilder.build_evaluation_prompt(test_case, actual_output, tracked_values)
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
        result = {
            'status': evaluation.status,
            'evaluation': evaluation.evaluation,
            'reasoning': evaluation.reasoning,
            'confidence': evaluation.confidence
        }
        
        # Add target evaluations if present
        if evaluation.target_evaluations:
            result['target_evaluations'] = evaluation.target_evaluations
        
        return result

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