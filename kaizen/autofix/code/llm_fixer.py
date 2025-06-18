"""LLM-based code fixing implementation."""

import os
import logging
import json
from typing import Dict, Any, Optional, List, Set, Tuple, TypedDict, Union, TYPE_CHECKING
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum, auto
import traceback

if TYPE_CHECKING:
    from kaizen.cli.commands.models import TestConfiguration

from ..types import FixStatus

logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass

class LLMResponseError(LLMError):
    """Exception for invalid LLM responses."""
    pass

class LLMConnectionError(LLMError):
    """Exception for LLM connection issues."""
    pass

@dataclass
class FixResult:
    """Result of a fix operation."""
    status: FixStatus
    fixed_code: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    confidence: Optional[float] = None
    context_analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class BaseFixer(ABC):
    """Base class for code fixers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the fixer.
        
        Args:
            config: Configuration for the fixer
        """
        self.config = config
    
    @abstractmethod
    def get_instructions(self) -> str:
        """Get instructions for the fixer."""
        pass
    
    @abstractmethod
    def fix(self, content: str, file_path: str, **kwargs) -> FixResult:
        """Fix the content."""
        pass

class CodeFixer(BaseFixer):
    """Fixes code using LLM."""
    
    def get_instructions(self) -> str:
        return """
        You are an expert at improving code quality and robustness. Your task is to enhance the given code.
        Consider the following aspects:
        1. Code Quality:
           - Improve readability and maintainability
           - Add proper documentation and comments
           - Follow best practices and design patterns
        
        2. Error Handling:
           - Add appropriate error handling
           - Include input validation
           - Handle edge cases
        
        3. Performance:
           - Optimize where possible
           - Add caching if beneficial
           - Improve resource usage
        
        4. Testing:
           - Add or improve test coverage
           - Include edge case tests
           - Add performance tests if relevant
        
        Return the improved code while maintaining its core functionality.
        """
    
    def fix(self, content: str, file_path: str, **kwargs) -> FixResult:
        try:
            # TODO: Implement LLM-based code fixing
            return FixResult(
                status='success',
                fixed_code=content,
                changes=[],
                explanation='Code fixing not yet implemented',
                confidence=0.0
            )
        except Exception as e:
            logger.error(f"Error fixing code in {file_path}: {str(e)}")
            return FixResult(
                status='error',
                fixed_code=content,
                changes=[],
                explanation='',
                confidence=0.0,
                error=str(e)
            )

class PromptFixer(BaseFixer):
    """Improves prompts using LLM."""
    
    def get_instructions(self) -> str:
        return """
        You are an expert at improving AI prompts. Your task is to enhance the given prompt to make it more effective.
        Consider the following aspects:
        1. Clarity and Specificity:
           - Make instructions more explicit and unambiguous
           - Add specific examples where helpful
           - Remove any vague or ambiguous language
        
        2. Structure and Organization:
           - Organize instructions in a logical flow
           - Use clear section headers
           - Break down complex instructions into steps
        
        3. Context and Constraints:
           - Add relevant context about the AI's role and capabilities
           - Specify any constraints or limitations
           - Include error handling instructions
        
        4. Best Practices:
           - Follow prompt engineering best practices
           - Include clear input/output formats
           - Add validation criteria for responses
        
        Return the improved prompt while maintaining its core purpose and functionality.
        """
    
    def fix(self, content: str, file_path: str, **kwargs) -> FixResult:
        try:
            # TODO: Implement LLM-based prompt improvement
            return FixResult(
                status='success',
                fixed_code=content,
                changes=[],
                explanation='Prompt improvement not yet implemented',
                confidence=0.0
            )
        except Exception as e:
            logger.error(f"Error improving prompt in {file_path}: {str(e)}")
            return FixResult(
                status='error',
                fixed_code=content,
                changes=[],
                explanation='',
                confidence=0.0,
                error=str(e)
            )

class ContentCleaner:
    """Cleans content by removing markdown notations and other artifacts."""
    
    @staticmethod
    def clean_markdown(content: str) -> str:
        """
        Clean markdown notations from the content.
        
        Args:
            content: The content to clean
            
        Returns:
            str: Cleaned content
        """
        try:
            # Remove markdown code block notations
            content = content.replace('```python', '').replace('```', '')
            
            # Remove any remaining markdown formatting
            content = content.replace('**', '').replace('*', '')
            
            # Remove any leading/trailing whitespace
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning markdown notations: {str(e)}")
            return content  # Return original content if cleaning fails

class PromptBuilder:
    """Handles prompt construction for LLM interactions."""
    
    @staticmethod
    def build_fix_prompt(content: str, file_path: str, failure_data: Optional[Dict],
                        config: Optional['TestConfiguration'], context_files: Optional[Dict[str, str]]) -> str:
        """Build prompt for code fixing in AI agent development context."""
        prompt_parts = [
            """You are an expert code fixer focused on minimal, targeted improvements. Your task is to fix the code following these principles:

1. Minimal Changes:
   - Make only necessary changes to fix the issue
   - Preserve existing functionality
   - Avoid unnecessary refactoring
   - Focus on critical fixes first

2. Essential Fixes:
   - Fix critical bugs and errors
   - Add essential error handling
   - Ensure type safety
   - Fix security vulnerabilities

3. Best Practices (Only When Relevant):
   - Add proper error handling for critical paths
   - Ensure proper resource cleanup
   - Add essential input validation
   - Fix critical performance issues

4. Prompt Engineering (Critical):
   - Structure prompts with clear sections and hierarchy
   - Use explicit instructions and constraints
   - Include examples where helpful
   - Add validation criteria for responses
   - Use system messages to set context
   - Include error handling instructions
   - Add fallback strategies
   - Use clear input/output formats
   - Include token usage optimization
   - Add context management guidelines
   - Use proper prompt templates
   - Include safety checks and filters
   - Add proper error messages
   - Use proper prompt versioning
   - Include proper documentation

IMPORTANT: Return ONLY the fixed code, properly formatted in a Python code block. Do not include any analysis or explanation in the response.

The fixed code should:
- Include only necessary changes
- Maintain existing functionality
- Follow Python best practices
- Be properly formatted
- Include essential error handling
- Fix critical issues only
- Follow prompt engineering best practices

Format your response as:
```python
# Your fixed code here
```""",
            f"\nFile: {file_path}",
            f"Content:\n{content}"
        ]
        
        if failure_data:
            prompt_parts.append(f"\nFailure Information:\n{failure_data}")
        
        if config:
            prompt_parts.append(f"\nUser Goal:\n{config}")
        
        if context_files:
            prompt_parts.append("\nRelated Files (for context and dependencies):")
            for path, file_content in context_files.items():
                prompt_parts.append(f"\n{path}:\n{file_content}")
        
        return "\n\n".join(prompt_parts)
    
    @staticmethod
    def build_analysis_prompt(content: str, file_path: str, failure_data: Optional[Dict],
                            user_goal: Optional[str], context_files: Optional[Dict[str, str]]) -> str:
        """Build prompt for code analysis."""
        prompt_parts = [
            """You are an expert code reviewer focused on minimal, targeted improvements. Analyze the code and provide a focused review following these principles:

1. Minimal Changes:
   - Make only necessary changes
   - Preserve existing functionality
   - Avoid unnecessary refactoring
   - Focus on critical issues first

2. Code Quality (Essential):
   - Type safety and validation
   - Error handling for critical paths
   - Clear documentation for public APIs
   - Consistent code style

3. Performance & Security:
   - Critical performance bottlenecks
   - Security vulnerabilities
   - Resource leaks
   - API key handling

4. Testing & Reliability:
   - Critical test coverage gaps
   - Edge case handling
   - Integration points
   - Error recovery

Provide your analysis in this format:

1. Critical Issues (Must Fix):
   - List only critical problems
   - Impact on functionality
   - Security implications

2. Minimal Changes Required:
   - Specific, targeted improvements
   - Focus on critical paths
   - Avoid unnecessary refactoring

3. Implementation Priority:
   - High: Security, crashes, data loss
   - Medium: Performance, reliability
   - Low: Style, documentation

Remember: Focus on minimal, necessary changes that follow best practices. Avoid unnecessary refactoring or style changes unless they impact functionality.""",
            f"\nFile: {file_path}",
            f"Content:\n{content}"
        ]
        
        if failure_data:
            prompt_parts.append(f"\nFailure Information:\n{failure_data}")
        
        if user_goal:
            prompt_parts.append(f"\nUser Goal:\n{user_goal}")
        
        if context_files:
            prompt_parts.append("\nRelated Files (for context and dependencies):")
            for path, file_content in context_files.items():
                prompt_parts.append(f"\n{path}:\n{file_content}")
        
        return "\n\n".join(prompt_parts)

    @staticmethod
    def build_compatibility_prompt(content: str, file_path: str,
                                 compatibility_issues: List[str],
                                 context_files: Dict[str, str]) -> str:
        """Build prompt for compatibility fixing."""
        prompt_parts = [
            f"File: {file_path}",
            f"Content:\n{content}",
            "Compatibility Issues:",
            *[f"- {issue}" for issue in compatibility_issues],
            "\nRelated Files:"
        ]
        
        for path, file_content in context_files.items():
            prompt_parts.append(f"\n{path}:\n{file_content}")
        
        return "\n\n".join(prompt_parts)

class ResponseProcessor:
    """Handles processing and analysis of LLM responses."""
    
    @staticmethod
    def clean_markdown_notations(code: str) -> str:
        """Clean markdown notations from code."""
        if code.startswith('```'):
            code = code.split('\n', 1)[1]
        if code.endswith('```'):
            code = code.rsplit('\n', 1)[0]
        return code.strip()
    
    @staticmethod
    def analyze_changes(original: str, fixed: str) -> Dict[str, Any]:
        """Analyze changes between original and fixed code."""
        # Implement change analysis logic
        return {
            'type': 'code_changes',
            'details': 'Changes analyzed'  # Add more detailed analysis
        }
    
    @staticmethod
    def extract_explanation(response: str) -> str:
        """Extract explanation from LLM response."""
        # Implement explanation extraction logic
        return "Code changes explained"  # Add actual explanation extraction
    
    @staticmethod
    def calculate_confidence(response: str) -> float:
        """Calculate confidence score for the fix."""
        # Implement confidence calculation logic
        return 0.8  # Add actual confidence calculation
    
    @staticmethod
    def analyze_context(content: str, fixed_code: str,
                       context_files: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze context and suggest related changes."""
        if not context_files:
            return {}
            
        # Implement context analysis logic
        return {
            'suggestions': [],  # Add actual suggestions
            'related_changes': []  # Add related changes
        }

class LLMCodeFixer:
    """Unified LLM-based code and prompt fixer."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM code fixer.
        
        Args:
            config: Configuration dictionary for the LLM fixer
        """
        self.config = config
        self.model = self._initialize_model()
        self.prompt_builder = PromptBuilder()
        self.response_processor = ResponseProcessor()
    
    def _initialize_model(self) -> Any:
        """Initialize the LLM model."""
        try:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise LLMError("GOOGLE_API_KEY environment variable not set")
                
            genai.configure(api_key=api_key)
            return genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        except Exception as e:
            raise LLMError(f"Failed to initialize LLM model: {str(e)}")
    
    def fix_code(self, content: str, file_path: str, failure_data: Optional[Dict] = None,
                config: Optional['TestConfiguration'] = None, context_files: Optional[Dict[str, str]] = None) -> FixResult:
        """
        Fix code using LLM.
        
        Args:
            content: Content to fix
            file_path: Path to the file
            failure_data: Optional failure information
            user_goal: Optional user goal
            context_files: Optional dictionary of related files
            
        Returns:
            FixResult object containing fix results
        """
        try:
            # Prepare the prompt
            prompt = self.prompt_builder.build_fix_prompt(
                content, file_path, failure_data, config, context_files
            )
            # logger.info(f"Prompt: {prompt}")
            # Get fix from LLM
            response = self._get_llm_response(prompt)
            # logger.info(f"Response: {response}")
            # Process the response
            fixed_code = self.response_processor.clean_markdown_notations(response)
            logger.info(f"Markdown clean success")

            try:
                logger.info("Starting to create FixResult", extra={
                    'has_fixed_code': bool(fixed_code),
                    'has_content': bool(content),
                    'has_response': bool(response),
                    'has_context_files': bool(context_files)
                })

                # Safely analyze changes
                try:
                    changes = self.response_processor.analyze_changes(content, fixed_code)
                    logger.info("Successfully analyzed changes", extra={'changes_type': type(changes)})
                except Exception as e:
                    logger.error("Failed to analyze changes", extra={
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    changes = {}

                # Safely extract explanation
                try:
                    explanation = self.response_processor.extract_explanation(response)
                    logger.info("Successfully extracted explanation", extra={'has_explanation': bool(explanation)})
                except Exception as e:
                    logger.error("Failed to extract explanation", extra={
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    explanation = None

                # Safely calculate confidence
                try:
                    confidence = self.response_processor.calculate_confidence(response)
                    logger.info("Successfully calculated confidence", extra={'confidence': confidence})
                except Exception as e:
                    logger.error("Failed to calculate confidence", extra={
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    confidence = 0.0

                # Safely analyze context
                try:
                    context_analysis = self.response_processor.analyze_context(
                        content, fixed_code, context_files
                    )
                    logger.info("Successfully analyzed context", extra={'has_context_analysis': bool(context_analysis)})
                except Exception as e:
                    logger.error("Failed to analyze context", extra={
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    context_analysis = {}

                logger.info("Creating FixResult with processed data")
                return FixResult(
                    status=FixStatus.SUCCESS,
                    fixed_code=fixed_code,
                    changes=changes,
                    explanation=explanation,
                    confidence=confidence,
                    context_analysis=context_analysis
                )

            except Exception as e:
                logger.error("Failed to create FixResult", extra={
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc()
                })
                # Return a minimal FixResult with just the essential information
                return FixResult(
                    status=FixStatus.SUCCESS,
                    fixed_code=fixed_code,
                    changes={},
                    explanation=None,
                    confidence=0.0,
                    context_analysis={}
                )
            
        except LLMResponseError as e:
            logger.error(f"Invalid LLM response: {str(e)}", extra={
                'file_path': file_path,
                'error_type': type(e).__name__
            })
            return FixResult(status=FixStatus.INVALID_RESPONSE, error=str(e))
            
        except LLMConnectionError as e:
            logger.error(f"LLM connection error: {str(e)}", extra={
                'file_path': file_path,
                'error_type': type(e).__name__
            })
            return FixResult(status=FixStatus.ERROR, error=str(e))
            
        except Exception as e:
            logger.error(f"Error fixing code with LLM: {str(e)}", extra={
                'file_path': file_path,
                'error_type': type(e).__name__
            })
            return FixResult(status=FixStatus.ERROR, error=str(e))
    
    def fix_compatibility_issues(self, content: str, file_path: str,
                               compatibility_issues: List[str],
                               context_files: Dict[str, str]) -> FixResult:
        """
        Fix compatibility issues using LLM.
        
        Args:
            content: Content to fix
            file_path: Path to the file
            compatibility_issues: List of compatibility issues
            context_files: Dictionary of related files
            
        Returns:
            FixResult object containing fix results
        """
        try:
            # Prepare the prompt
            prompt = self.prompt_builder.build_compatibility_prompt(
                content, file_path, compatibility_issues, context_files
            )
            
            # Get fix from LLM
            response = self._get_llm_response(prompt)
            
            # Process the response
            fixed_code = self.response_processor.clean_markdown_notations(response)
            
            return FixResult(
                status=FixStatus.SUCCESS,
                fixed_code=fixed_code,
                changes=self.response_processor.analyze_changes(content, fixed_code),
                explanation=self.response_processor.extract_explanation(response),
                confidence=self.response_processor.calculate_confidence(response)
            )
            
        except LLMResponseError as e:
            logger.error(f"Invalid LLM response: {str(e)}", extra={
                'file_path': file_path,
                'error_type': type(e).__name__
            })
            return FixResult(status=FixStatus.INVALID_RESPONSE, error=str(e))
            
        except LLMConnectionError as e:
            logger.error(f"LLM connection error: {str(e)}", extra={
                'file_path': file_path,
                'error_type': type(e).__name__
            })
            return FixResult(status=FixStatus.ERROR, error=str(e))
            
        except Exception as e:
            logger.error(f"Error fixing compatibility issues: {str(e)}", extra={
                'file_path': file_path,
                'error_type': type(e).__name__
            })
            return FixResult(status=FixStatus.ERROR, error=str(e))
    
    def _get_llm_response(self, prompt: str) -> str:
        """
        Get response from LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response
            
        Raises:
            LLMResponseError: If the response is invalid
            LLMConnectionError: If there's a connection issue
        """
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for more focused results
                    max_output_tokens=20000,
                    top_p=0.8,
                    top_k=40,
                )
            )
            
            # Check if response is None
            if response is None:
                raise LLMResponseError("Empty response from LLM")
            
            # Check if response has a valid finish reason
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = response.candidates[0].finish_reason
                if finish_reason == 2:  # Safety or other constraint
                    raise LLMResponseError("Model stopped due to safety constraints or other limitations")
            
            # Check if response has text
            if not hasattr(response, 'text') or not response.text:
                raise LLMResponseError("No text content in LLM response")
                
            return response.text
            
        except ConnectionError as e:
            raise LLMConnectionError(f"Failed to connect to LLM: {str(e)}")
        except Exception as e:
            raise LLMError(f"Error getting LLM response: {str(e)}") 