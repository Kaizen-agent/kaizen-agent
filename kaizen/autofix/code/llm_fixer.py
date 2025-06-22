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
            """You are an expert code fixer focused on targeted improvements. Your task is to fix the code following these principles:

1. Code Structure Preservation:
   - DO NOT change the overall function or class structure
   - Preserve existing function signatures and class definitions
   - Keep the same file organization and imports
   - Only modify the internal logic when necessary

2. Code Changes (Minimal and Surgical):
   - Make only necessary changes to fix the specific issue
   - Preserve existing functionality and behavior
   - Avoid unnecessary refactoring or restructuring
   - Focus on critical bugs and errors only
   - Keep changes minimal and targeted

3. Open-Closed Principle:
   - Code should be open for extension but closed for modification
   - Use inheritance, composition, or interfaces for extensibility
   - Avoid modifying existing classes when adding new functionality
   - Design for future extensibility without breaking current code
   - Use abstract base classes or protocols for extensible interfaces
   - Implement plugin patterns or strategy patterns where appropriate
   - When fixing, consider how the code can be extended in the future

4. Backward Compatibility:
   - Preserve existing public APIs and interfaces
   - Maintain function signatures and return types
   - Keep existing configuration formats and file structures
   - Avoid breaking changes to existing functionality
   - Use deprecation warnings instead of immediate removal
   - Add new features through extension rather than modification
   - Ensure existing tests continue to pass

5. Prompt Improvements (When Present):
   - If the file contains prompts, improve them using modern prompt engineering best practices
   
   A. Structure and Organization:
      - Use clear hierarchical sections with numbered or bulleted lists
      - Group related instructions logically (e.g., context, task, constraints, output format)
      - Use consistent formatting and indentation for readability
      - Include a clear role definition at the beginning
      - Add a summary or overview section for complex prompts
   
   B. Clarity and Specificity:
      - Use explicit, unambiguous language
      - Avoid vague terms like "good", "proper", "appropriate" without context
      - Provide specific examples where helpful (but keep them generic)
      - Define technical terms and acronyms
      - Use active voice and imperative mood for instructions
      - Break complex tasks into step-by-step instructions
   
   C. Context and Constraints:
      - Clearly define the AI's role and capabilities
      - Specify the expected input format and data types
      - Define output format requirements (JSON, markdown, code blocks, etc.)
      - Set clear boundaries and limitations
      - Include error handling instructions
      - Specify what the AI should do with unclear or invalid inputs
   
   D. Validation and Quality Control:
      - Add validation criteria for responses
      - Include self-checking instructions (e.g., "verify your response meets these criteria")
      - Specify quality standards and completeness requirements
      - Add instructions for handling edge cases
      - Include confidence level requirements
   
   E. Safety and Ethics:
      - Include safety checks and content filters
      - Add instructions for handling sensitive information
      - Specify ethical guidelines and constraints
      - Include instructions for refusing inappropriate requests
      - Add bias awareness and mitigation guidelines
   
   F. Input/Output Formatting:
      - Use clear input/output format specifications
      - Include JSON schema examples where applicable
      - Specify code block formatting requirements
      - Define response structure and organization
      - Include formatting for different content types (code, text, data)
   
   G. Context Management:
      - Add instructions for maintaining conversation context
      - Specify how to handle multi-turn interactions
      - Include memory management guidelines
      - Add instructions for context switching
      - Specify how to handle conflicting information
   
   H. Error Recovery and Fallbacks:
      - Include graceful degradation instructions
      - Add fallback strategies for partial failures
      - Specify how to handle incomplete information
      - Include retry logic guidelines
      - Add instructions for escalating issues
   
   I. Performance and Efficiency:
      - Add instructions for optimizing response length
      - Include guidelines for prioritizing information
      - Specify when to use concise vs. detailed responses
      - Add instructions for handling large inputs
      - Include caching and reuse guidelines
   
   J. Best Practices:
      - DO NOT add specific test case examples - keep prompts generic and reusable
      - DO NOT reference specific file names or paths in prompts
      - Use consistent terminology throughout the prompt
      - Include version information for prompt evolution
      - Add instructions for prompt debugging and improvement
      - Include guidelines for prompt testing and validation

   K. Advanced Prompting Techniques:
      - Few-Shot Learning:
        * Include 2-3 relevant examples to demonstrate the desired output format
        * Use diverse examples that cover different scenarios and edge cases
        * Ensure examples are generic and reusable across different contexts
        * Format examples consistently with clear input/output pairs
        * Use examples that demonstrate the expected reasoning process
      
      - Chain-of-Thought (CoT) Prompting:
        * Add instructions for step-by-step reasoning
        * Include phrases like "Let's think through this step by step"
        * Encourage the AI to show its work and reasoning process
        * Use intermediate steps to break down complex problems
        * Include validation steps within the reasoning chain
      
      - Zero-Shot to Few-Shot Progression:
        * Start with zero-shot instructions for basic tasks
        * Add few-shot examples for complex or ambiguous tasks
        * Use progressive examples that build in complexity
        * Include examples that demonstrate error handling
      
      - Self-Consistency and Verification:
        * Add instructions for the AI to verify its own responses
        * Include multiple reasoning paths for complex problems
        * Use ensemble-like approaches with different perspectives
        * Add confidence scoring for responses
        * Include instructions for cross-checking results
      
      - Retrieval-Augmented Generation (RAG):
        * Include instructions for using provided context effectively
        * Add guidelines for synthesizing information from multiple sources
        * Specify how to handle conflicting information
        * Include instructions for citing sources when appropriate
      
      - Role-Based Prompting:
        * Define specific roles for different aspects of the task
        * Use multiple personas for complex decision-making
        * Include expert perspectives for specialized domains
        * Add instructions for role-switching when appropriate
      
      - Iterative Refinement:
        * Include instructions for iterative improvement of responses
        * Add guidelines for self-critique and improvement
        * Use feedback loops for continuous enhancement
        * Include instructions for learning from previous interactions

6. Essential Fixes Only:
   - Fix critical bugs and errors
   - Add essential error handling for critical paths
   - Ensure type safety where missing
   - Fix security vulnerabilities
   - Address resource leaks

7. Best Practices (Minimal):
   - Add proper error handling only for critical paths
   - Ensure proper resource cleanup where missing
   - Add essential input validation where critical
   - Fix critical performance issues only
   - Design for extensibility and maintainability

IMPORTANT GUIDELINES:
- For code: Make minimal, surgical changes that preserve structure and maintain backward compatibility
- For prompts: Improve existing prompts using advanced techniques like few-shot learning and chain-of-thought when appropriate
- Return ONLY the fixed code, properly formatted in a Python code block
- Do not include any analysis or explanation in the response
- Do not change function signatures or class structures
- Do not add test case examples to prompts (use generic examples instead)
- Keep all improvements generic and reusable
- Ensure code is extensible for future modifications
- Maintain backward compatibility with existing interfaces
- Use advanced prompting techniques judiciously - only when they improve clarity and effectiveness

The fixed code should:
- Preserve the original code structure and organization
- Include only necessary code changes (minimal)
- Improve prompts generically without specific examples
- Maintain existing functionality and backward compatibility
- Follow Python best practices
- Be properly formatted
- Include essential error handling only where critical
- Be designed for future extensibility
- Use the open-closed principle where appropriate

Format your response as:
```python
# Your fixed code here
```""",
            f"\nFile: {file_path}",
            f"Content:\n{content}"
        ]
        
        # Handle enhanced failure data with learning context
        if failure_data:
            if isinstance(failure_data, dict) and 'learning_context' in failure_data:
                # Enhanced failure data with learning
                original_failures = failure_data.get('original_failures', {})
                learning_context = failure_data.get('learning_context', {})
                previous_analysis = failure_data.get('previous_attempt_analysis', {})
                
                # Add original failure information
                if original_failures:
                    prompt_parts.append(f"\nOriginal Failure Information:\n{original_failures}")
                
                # Add learning context from previous attempts
                if learning_context:
                    current_attempt = learning_context.get('current_attempt', 1)
                    total_attempts = learning_context.get('total_attempts', 0)
                    
                    learning_guidance = f"\nLEARNING FROM PREVIOUS ATTEMPTS (Attempt {current_attempt} of {total_attempts}):"
                    
                    # Add successful patterns
                    successful_patterns = learning_context.get('successful_patterns', [])
                    if successful_patterns:
                        learning_guidance += f"\n- What worked in previous attempts: {', '.join(successful_patterns)}"
                        learning_guidance += "\n- Focus on similar approaches that were successful"
                    
                    # Add failed approaches
                    failed_approaches = learning_context.get('failed_approaches', [])
                    if failed_approaches:
                        learning_guidance += f"\n- What didn't work: {', '.join(failed_approaches)}"
                        learning_guidance += "\n- Avoid repeating these failed approaches"
                    
                    # Add common errors
                    common_errors = learning_context.get('common_errors', [])
                    if common_errors:
                        learning_guidance += f"\n- Common error patterns: {', '.join(common_errors)}"
                        learning_guidance += "\n- Pay special attention to these error types"
                    
                    # Add improvement insights
                    improvement_insights = learning_context.get('improvement_insights', [])
                    if improvement_insights:
                        learning_guidance += f"\n- Recent improvements: {', '.join(improvement_insights)}"
                        learning_guidance += "\n- Build on these successful improvements"
                    
                    prompt_parts.append(learning_guidance)
                
                # Add specific analysis from previous attempts
                if previous_analysis:
                    analysis_guidance = "\nPREVIOUS ATTEMPT ANALYSIS:"
                    
                    what_worked = previous_analysis.get('what_worked', [])
                    if what_worked:
                        analysis_guidance += f"\n- Successful strategies: {', '.join(what_worked)}"
                    
                    what_didnt_work = previous_analysis.get('what_didnt_work', [])
                    if what_didnt_work:
                        analysis_guidance += f"\n- Failed strategies: {', '.join(what_didnt_work)}"
                    
                    recommendations = previous_analysis.get('recommendations', [])
                    if recommendations:
                        analysis_guidance += f"\n- Recommendations: {', '.join(recommendations)}"
                    
                    prompt_parts.append(analysis_guidance)
                
                # Add strategic guidance for subsequent attempts
                if current_attempt > 1:
                    strategic_guidance = f"\nSTRATEGIC GUIDANCE FOR ATTEMPT {current_attempt}:"
                    strategic_guidance += "\n- Learn from previous attempts and avoid repeating failed approaches"
                    strategic_guidance += "\n- Focus on patterns that showed improvement"
                    strategic_guidance += "\n- Be more targeted and specific in your fixes"
                    strategic_guidance += "\n- Consider different approaches if previous ones didn't work"
                    
                    prompt_parts.append(strategic_guidance)
                
            else:
                # Standard failure data (backward compatibility)
                prompt_parts.append(f"\nFailure Information:\n{failure_data}")
        
        if config:
            # Only include relevant configuration info, not test cases
            config_info = {
                'name': getattr(config, 'name', None),
                'description': getattr(config, 'description', None),
                'goal': getattr(config, 'goal', None)
            }
            
            # Add evaluation criteria if available
            if hasattr(config, 'evaluation') and config.evaluation:
                evaluation_info = {}
                
                # Add legacy criteria
                if hasattr(config.evaluation, 'criteria') and config.evaluation.criteria:
                    evaluation_info['criteria'] = config.evaluation.criteria
                
                # Add new evaluation targets
                if hasattr(config.evaluation, 'evaluation_targets') and config.evaluation.evaluation_targets:
                    evaluation_info['evaluation_targets'] = [
                        target.to_dict() if hasattr(target, 'to_dict') else {
                            'name': getattr(target, 'name', None),
                            'source': getattr(target, 'source', None),
                            'criteria': getattr(target, 'criteria', None),
                            'description': getattr(target, 'description', None),
                            'weight': getattr(target, 'weight', None)
                        }
                        for target in config.evaluation.evaluation_targets
                    ]
                
                if evaluation_info:
                    config_info['evaluation'] = evaluation_info
            
            prompt_parts.append(f"\nConfiguration Context:\n{config_info}")
        
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

3. Open-Closed Principle:
   - Code should be open for extension but closed for modification
   - Use inheritance, composition, or interfaces for extensibility
   - Avoid modifying existing classes when adding new functionality
   - Design for future extensibility without breaking current code
   - Use abstract base classes or protocols for extensible interfaces
   - Implement plugin patterns or strategy patterns where appropriate

4. Backward Compatibility:
   - Preserve existing public APIs and interfaces
   - Maintain function signatures and return types
   - Keep existing configuration formats and file structures
   - Avoid breaking changes to existing functionality
   - Use deprecation warnings instead of immediate removal
   - Add new features through extension rather than modification
   - Ensure existing tests continue to pass

5. Performance & Security:
   - Critical performance bottlenecks
   - Security vulnerabilities
   - Resource leaks
   - API key handling

6. Testing & Reliability:
   - Critical test coverage gaps
   - Edge case handling
   - Integration points
   - Error recovery

Provide your analysis in this format:

1. Critical Issues (Must Fix):
   - List only critical problems
   - Impact on functionality
   - Security implications

2. Open-Closed Principle Violations:
   - Identify code that's not extensible
   - Suggest ways to make it open for extension
   - Recommend abstract interfaces or base classes

3. Backward Compatibility Concerns:
   - Identify potential breaking changes
   - Suggest backward-compatible alternatives
   - Recommend deprecation strategies

4. Minimal Changes Required:
   - Specific, targeted improvements
   - Focus on critical paths
   - Avoid unnecessary refactoring
   - Prioritize extensibility and compatibility

5. Implementation Priority:
   - High: Security, crashes, data loss, breaking changes
   - Medium: Performance, reliability, extensibility
   - Low: Style, documentation, minor optimizations

Remember: Focus on minimal, necessary changes that follow best practices. Ensure code is extensible and maintains backward compatibility while avoiding unnecessary refactoring or style changes unless they impact functionality.""",
            f"\nFile: {file_path}",
            f"Content:\n{content}"
        ]
        
        # Handle enhanced failure data with learning context
        if failure_data:
            if isinstance(failure_data, dict) and 'learning_context' in failure_data:
                # Enhanced failure data with learning
                original_failures = failure_data.get('original_failures', {})
                learning_context = failure_data.get('learning_context', {})
                previous_analysis = failure_data.get('previous_attempt_analysis', {})
                
                # Add original failure information
                if original_failures:
                    prompt_parts.append(f"\nOriginal Failure Information:\n{original_failures}")
                
                # Add learning context from previous attempts
                if learning_context:
                    current_attempt = learning_context.get('current_attempt', 1)
                    total_attempts = learning_context.get('total_attempts', 0)
                    
                    learning_guidance = f"\nLEARNING FROM PREVIOUS ATTEMPTS (Attempt {current_attempt} of {total_attempts}):"
                    
                    # Add successful patterns
                    successful_patterns = learning_context.get('successful_patterns', [])
                    if successful_patterns:
                        learning_guidance += f"\n- What worked in previous attempts: {', '.join(successful_patterns)}"
                        learning_guidance += "\n- Focus on similar approaches that were successful"
                    
                    # Add failed approaches
                    failed_approaches = learning_context.get('failed_approaches', [])
                    if failed_approaches:
                        learning_guidance += f"\n- What didn't work: {', '.join(failed_approaches)}"
                        learning_guidance += "\n- Avoid repeating these failed approaches"
                    
                    # Add common errors
                    common_errors = learning_context.get('common_errors', [])
                    if common_errors:
                        learning_guidance += f"\n- Common error patterns: {', '.join(common_errors)}"
                        learning_guidance += "\n- Pay special attention to these error types"
                    
                    # Add improvement insights
                    improvement_insights = learning_context.get('improvement_insights', [])
                    if improvement_insights:
                        learning_guidance += f"\n- Recent improvements: {', '.join(improvement_insights)}"
                        learning_guidance += "\n- Build on these successful improvements"
                    
                    prompt_parts.append(learning_guidance)
                
                # Add specific analysis from previous attempts
                if previous_analysis:
                    analysis_guidance = "\nPREVIOUS ATTEMPT ANALYSIS:"
                    
                    what_worked = previous_analysis.get('what_worked', [])
                    if what_worked:
                        analysis_guidance += f"\n- Successful strategies: {', '.join(what_worked)}"
                    
                    what_didnt_work = previous_analysis.get('what_didnt_work', [])
                    if what_didnt_work:
                        analysis_guidance += f"\n- Failed strategies: {', '.join(what_didnt_work)}"
                    
                    recommendations = previous_analysis.get('recommendations', [])
                    if recommendations:
                        analysis_guidance += f"\n- Recommendations: {', '.join(recommendations)}"
                    
                    prompt_parts.append(analysis_guidance)
                
                # Add strategic guidance for subsequent attempts
                if current_attempt > 1:
                    strategic_guidance = f"\nSTRATEGIC GUIDANCE FOR ATTEMPT {current_attempt}:"
                    strategic_guidance += "\n- Learn from previous attempts and avoid repeating failed approaches"
                    strategic_guidance += "\n- Focus on patterns that showed improvement"
                    strategic_guidance += "\n- Be more targeted and specific in your analysis"
                    strategic_guidance += "\n- Consider different approaches if previous ones didn't work"
                    
                    prompt_parts.append(strategic_guidance)
                
            else:
                # Standard failure data (backward compatibility)
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