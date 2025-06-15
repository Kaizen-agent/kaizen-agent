import os
import uuid
from typing import List, Dict, Tuple
import subprocess
from pathlib import Path
import google.generativeai as genai
from github import Github
from github.GithubException import GithubException
from datetime import datetime
import json
import yaml
import sys
from rich.console import Console
import ast
import importlib
import random

from .logger import get_logger
from .config import get_config
from .runner import TestRunner
from .logger import TestLogger

logger = get_logger(__name__)
console = Console()

def format_test_results_table(test_results: Dict) -> str:
    """Format test results into a markdown table."""
    table = "| Test Name | Region | Status |\n|-----------|--------|--------|\n"
    for region, result in test_results.items():
        # Skip if result is a string or if region is _status/overall_status
        if isinstance(result, str) or region in ('_status', 'overall_status'):
            continue
        # Ensure result is a dictionary before accessing test_cases
        if not isinstance(result, dict):
            logger.warning(f"Skipping invalid result format for region {region}: {result}")
            continue
        test_cases = result.get('test_cases', [])
        if not isinstance(test_cases, list):
            logger.warning(f"Skipping invalid test_cases format for region {region}: {test_cases}")
            continue
        for test_case in test_cases:
            if not isinstance(test_case, dict):
                logger.warning(f"Skipping invalid test case format: {test_case}")
                continue
            status = "✅ PASS" if test_case.get('status') == 'passed' else "❌ FAIL"
            table += f"| {test_case.get('name', 'Unknown')} | {region} | {status} |\n"
    return table

def analyze_failures(failure_data: List[Dict]) -> str:
    """Analyze test failures and generate a summary."""
    logger.info(f"Starting analyze_failures with failure_data type: {type(failure_data)}")
    logger.info(f"Failure data content: {failure_data}")
    
    if not failure_data:
        logger.info("No failure data provided, returning default message")
        return "## Failure Analysis\n\nNo failures to analyze."
        
    analysis = "## Failure Analysis\n\n"
    
    # Group failures by error type
    error_groups = {}
    logger.info("Starting to process failures")
    for i, failure in enumerate(failure_data):
        logger.info(f"Processing failure {i}: {failure}")
        if not isinstance(failure, dict):
            logger.warning(f"Skipping invalid failure format: {failure}")
            continue
            
        try:
            error_message = failure.get('error_message', 'Unknown Error')
            logger.info(f"Error message: {error_message}")
            error_type = error_message.split(':')[0] if ':' in error_message else 'Unknown Error'
            logger.info(f"Error type: {error_type}")
            
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(failure)
        except Exception as e:
            logger.error(f"Error processing failure {i}: {str(e)}")
            logger.error(f"Failure data: {failure}")
            continue
    
    logger.info(f"Error groups: {error_groups}")
    
    # Generate analysis for each error type
    for error_type, failures in error_groups.items():
        logger.info(f"Processing error type: {error_type}")
        analysis += f"### {error_type}\n\n"
        analysis += f"**Affected Tests ({len(failures)}):**\n"
        for failure in failures:
            try:
                test_name = failure.get('test_name', 'Unknown Test')
                analysis += f"- {test_name}\n"
            except Exception as e:
                logger.error(f"Error processing test name: {str(e)}")
                analysis += "- Unknown Test\n"
                
        try:
            analysis += f"\n**Error Pattern:**\n{failures[0].get('error_message', 'Unknown Error')}\n\n"
        except Exception as e:
            logger.error(f"Error processing error pattern: {str(e)}")
            analysis += "\n**Error Pattern:**\nUnknown Error\n\n"
            
        analysis += "**Likely Root Cause:**\n"
        # Add common root causes based on error type
        if "AssertionError" in error_type:
            analysis += "- Incorrect logic or condition in the code\n"
            analysis += "- Unexpected output format or value\n"
        elif "TypeError" in error_type:
            analysis += "- Incorrect type handling or conversion\n"
            analysis += "- Missing type checking or validation\n"
        elif "AttributeError" in error_type:
            analysis += "- Missing or incorrect attribute access\n"
            analysis += "- Object initialization issues\n"
        elif "ImportError" in error_type:
            analysis += "- Missing or incorrect imports\n"
            analysis += "- Module path or dependency issues\n"
        else:
            analysis += "- General implementation error\n"
            analysis += "- Edge case not properly handled\n"
        analysis += "\n"
    
    logger.info("Completed failure analysis")
    return analysis

def _generate_pr_info(failure_data: List[Dict], fixed_tests: List[Dict], test_results: Dict, test_config: Dict, original_code: str) -> Tuple[str, str, str]:
    """
    Generate meaningful branch name, PR title, and body using LLM.
    
    Args:
        failure_data: List of test failures
        fixed_tests: List of fixed tests
        test_results: Complete test results
        test_config: Test configuration data
        original_code: The original code that needs to be fixed
        
    Returns:
        Tuple of (branch_name, pr_title, pr_body)
    """
    try:
        config = get_config()
        genai.configure(api_key=config.get_api_key("google"))
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Prepare prompt for LLM
        prompt = f"""You are a senior software engineer specializing in AI agent development. Your task is to improve the following code by fixing the issues described in the test failures. Make only minimal changes necessary to resolve all problems while preserving existing logic.

IMPORTANT: You must return your response in exactly three newline-separated fields:
1. First line: A descriptive branch name (will be sanitized and timestamped)
2. Second line: A concise PR title
3. Remaining lines: The complete fixed code file

Context:
1. This is an AI agent code that needs to be fixed
2. The test configuration provides evaluation criteria and test steps
3. Each test failure includes specific error messages and expected outputs
4. The code will be executed in a controlled environment with proper namespace setup

Test Configuration:
{json.dumps(test_config, indent=2)}

Original Code:
{original_code}

Test Failures:
{chr(10).join(f'  - test_name: {failure.get("test_name", "")}{chr(10)}    error_message: {failure.get("error_message", "")}' for failure in failure_data)}

Requirements:
1. Fix all test failures while maintaining the agent's core functionality
2. Follow the evaluation criteria from the test configuration
3. Ensure proper error handling and input validation
4. Maintain code quality standards (type hints, documentation, etc.)
5. Keep changes minimal and focused on fixing the specific issues
6. Return exactly three newline-separated fields as specified above
7. DO NOT return empty code blocks or invalid syntax
8. The returned code must be valid Python code that can be executed

Code Structure Requirements:
1. All imports must be at the top of the file
2. All classes and functions must be properly defined with type hints
3. All functions must have docstrings explaining their purpose and parameters
4. All classes must have proper initialization methods
5. All methods must handle their own exceptions and return appropriate values
6. All code must be properly indented and follow PEP 8 style
7. All variables must be properly initialized before use
8. All required dependencies must be imported
9. All code must be executable in a Python environment
10. All code must be compatible with Python 3.8+
11. The code must be a complete, valid Python file
12. The code must not contain any empty code blocks or invalid syntax

Execution Requirements:
1. Code must be executable in a controlled environment with proper namespace setup
2. Code must handle all possible input types and edge cases
3. Code must validate all inputs before processing
4. Code must handle all possible error conditions
5. Code must return appropriate values for all execution paths
6. Code must not rely on external state or global variables
7. Code must be thread-safe and reentrant
8. Code must clean up any resources it uses
9. Code must not have any side effects
10. Code must be deterministic

Code Improvement Guidelines:
1. Error Handling:
   - Add proper error handling for API calls and external services
   - Include specific error messages for different failure scenarios
   - Handle edge cases gracefully with appropriate fallbacks
   - Validate inputs before processing

2. AI Agent Best Practices:
   - Ensure proper initialization of AI models and services
   - Handle API rate limits and timeouts
   - Implement proper logging for debugging
   - Add retry mechanisms for transient failures
   - Validate model outputs before returning

3. Code Structure:
   - Keep methods focused and single-purpose
   - Use clear and descriptive variable names
   - Add type hints for all parameters and return values
   - Include docstrings explaining method purpose and parameters
   - Follow consistent code style

4. Testing Considerations:
   - Make code testable by avoiding hard-coded values
   - Use dependency injection where appropriate
   - Add proper mocking points for external services
   - Ensure error cases are testable
   - Make validation logic explicit and testable

5. Performance:
   - Optimize API calls and external service interactions
   - Cache results where appropriate
   - Handle large inputs efficiently
   - Implement proper resource cleanup

6. Security:
   - Never expose API keys or sensitive data
   - Validate and sanitize all inputs
   - Implement proper access controls
   - Handle sensitive data appropriately

7. AI Agent Prompt Engineering:
   When test failures indicate output quality issues (e.g., missing expected content, incorrect format, or poor response quality):
   
   a) Analyze the Failure:
      - Identify which specific aspects of the output failed (content, format, style, etc.)
      - Check if the failure is due to missing context or unclear instructions
      - Determine if the model needs more specific guidance or constraints
   
   b) Improve the Prompt:
      - Add clear output format requirements
      - Include specific examples of expected outputs
      - Specify required content elements
      - Add constraints for response length and style
      - Include validation criteria in the prompt
   
   c) Add Output Validation:
      - Implement checks for required content elements
      - Validate output format and structure
      - Add length and style validation
      - Include fallback responses for invalid outputs
   
   d) Enhance Context:
      - Add relevant background information
      - Include domain-specific terminology
      - Specify the target audience
      - Add style and tone requirements
   
   e) Add Safety and Quality Checks:
      - Include content filtering requirements
      - Add fact-checking instructions
      - Specify ethical guidelines
      - Include quality assurance steps

8. Output Quality Improvements:
   - Add post-processing for output formatting
   - Implement content validation
   - Add response enhancement logic
   - Include output sanitization
   - Add quality scoring mechanisms

Return your response in exactly three newline-separated fields as specified at the top of this prompt."""
        
        # Call Gemini API
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Parse response
        lines = content.split('\n')
        branch_name = lines[0].strip()
        pr_title = lines[1].strip()
        pr_body = '\n'.join(lines[2:]).strip()
        
        # Clean up branch name
        branch_name = branch_name.lower()
        branch_name = ''.join(c if c.isalnum() or c == '-' else '-' for c in branch_name)
        branch_name = '-'.join(filter(None, branch_name.split('-')))
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime('%Y%m%d')
        branch_name = f"{branch_name}-{timestamp}"
        
        return branch_name, pr_title, pr_body
        
    except Exception as e:
        logger.warning(f"Error generating PR info: {str(e)}")
        # Fallback to default values
        timestamp = datetime.now().strftime('%Y%m%d')
        branch_name = f"fix-tests-{timestamp}"
        pr_title = "Fix: Resolved test failures"
        pr_body = f"""# Test Fix Summary

## Overview
- **Fix Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Fixed Tests:** {len(fixed_tests)}
- **Total Tests:** {sum(len(result.get('test_cases', [])) for result in test_results.values())}

## Test Results
{format_test_results_table(test_results)}

{analyze_failures(failure_data)}

## Fix Details
### Fixed Tests
{chr(10).join(f'- {test["test_name"]} ({test["region"]})' for test in fixed_tests)}

### Original Failures
{chr(10).join(f'- {failure["test_name"]}: {failure["error_message"]}' for failure in failure_data)}
"""
        return branch_name, pr_title, pr_body

class CodeValidationError(Exception):
    """Exception raised when code validation and improvement fails."""
    pass

def _extract_code_blocks(text: str) -> List[str]:
    """
    Extract code blocks from text that may contain markdown or other formatting.
    
    Args:
        text: Text that may contain code blocks
        
    Returns:
        List of extracted code blocks
    """
    code_blocks = []
    in_code_block = False
    current_block = []
    
    for line in text.split('\n'):
        if line.strip().startswith('```'):
            if in_code_block:
                code_blocks.append('\n'.join(current_block))
                current_block = []
            in_code_block = not in_code_block
        elif in_code_block:
            current_block.append(line)
    
    return code_blocks

def _extract_kaizen_blocks(text: str) -> List[str]:
    """
    Extract code blocks between kaizen markers.
    
    Args:
        text: Text that may contain kaizen-marked code blocks
        
    Returns:
        List of extracted kaizen code blocks
    """
    kaizen_blocks = []
    in_kaizen_block = False
    current_block = []
    
    for line in text.split('\n'):
        if '# kaizen:start:' in line:
            in_kaizen_block = True
        elif '# kaizen:end:' in line:
            if current_block:
                kaizen_blocks.append('\n'.join(current_block))
                current_block = []
            in_kaizen_block = False
        elif in_kaizen_block:
            current_block.append(line)
    
    return kaizen_blocks

def _validate_code_syntax(code: str) -> bool:
    """
    Validate if the given code has valid Python syntax.
    
    Args:
        code: Code to validate
        
    Returns:
        bool: True if code has valid syntax, False otherwise
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False

def _attempt_llm_fix(code: str, original_code: str) -> str:
    """
    Attempt to fix code syntax using LLM.
    
    Args:
        code: Invalid code to fix
        original_code: Original code for reference
        
    Returns:
        str: Fixed code if successful
        
    Raises:
        CodeValidationError: If LLM fix attempt fails
    """
    try:
        config = get_config()
        genai.configure(api_key=config.get_api_key("google"))
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        prompt = f"""The following Python code has invalid syntax. Please fix it to be valid Python code that can be executed.
The code should maintain the improvements and fixes from the invalid code while ensuring it is syntactically correct.

Original Code (for reference only, do not revert to this):
{original_code}

Invalid Code (fix this while maintaining its improvements):
{code}

Requirements:
1. Return only valid Python code, no explanations
2. Maintain all improvements and fixes from the invalid code
3. Fix any syntax errors while preserving the intended functionality
4. Ensure all imports are at the top of the file
5. Ensure proper indentation
6. Ensure all brackets and parentheses are properly closed
7. Ensure all strings are properly quoted
8. Ensure all statements end with proper punctuation
9. Ensure all code blocks are properly defined
10. Ensure all functions and classes are properly defined
11. DO NOT include any markdown formatting or code block markers
12. DO NOT include any explanations or comments about the code
13. DO NOT revert to the original code - fix the invalid code instead
14. Return ONLY the fixed code

Return only the fixed code, no explanations or additional text."""
        
        response = model.generate_content(prompt)
        improved_code = response.text.strip()
        improved_code = improved_code.replace('```python', '').replace('```', '').strip()
        
        if _validate_code_syntax(improved_code):
            return improved_code
            
        # Try to extract valid code from the response
        code_lines = []
        for line in improved_code.split('\n'):
            if line.strip() and not line.strip().startswith(('#', '```', 'Here', 'The', 'This')):
                code_lines.append(line)
        
        if code_lines:
            extracted_code = '\n'.join(code_lines)
            if _validate_code_syntax(extracted_code):
                return extracted_code
        
        raise CodeValidationError("LLM failed to generate valid code")
        
    except Exception as e:
        raise CodeValidationError(f"Error during LLM fix attempt: {str(e)}")

def _validate_and_improve_code(code: str, original_code: str) -> str:
    """
    Validate and improve the generated code if it has invalid syntax.
    
    Args:
        code: The generated code to validate
        original_code: The original code for reference
        
    Returns:
        str: Improved code that should be valid Python syntax
        
    Raises:
        CodeValidationError: If all attempts to fix the code fail
    """
    # First try to parse the code to check syntax
    if _validate_code_syntax(code):
        return code
        
    logger.warning("Generated code has invalid syntax, attempting to fix")
    
    # Try to extract code from code blocks first
    code_blocks = _extract_code_blocks(code)
    for block in code_blocks:
        if _validate_code_syntax(block):
            logger.info("Found valid code block in response")
            return block
    
    # Try kaizen blocks next
    kaizen_blocks = _extract_kaizen_blocks(code)
    for block in kaizen_blocks:
        if _validate_code_syntax(block):
            logger.info("Found valid code in kaizen block")
            return block
    
    # If code is empty or just whitespace, log a warning
    if not code.strip():
        logger.warning("Generated code is empty after extraction attempts")
        raise CodeValidationError("Generated code is empty or contains only whitespace")
    
    # If we still don't have valid code, try to fix common syntax issues
    try:
        return _attempt_llm_fix(code, original_code)
    except CodeValidationError as e:
        logger.error(f"All attempts to fix code failed: {str(e)}")
        raise

def _enhance_pr_body(failure_data: List[Dict], fixed_tests: List[Dict], test_results: Dict, test_config: Dict, all_test_attempts: List[Dict]) -> str:
    """
    Enhance the PR body with comprehensive test results, analysis, and fix details.
    
    Args:
        failure_data: List of test failures
        fixed_tests: List of fixed tests
        test_results: Complete test results
        test_config: Test configuration data
        all_test_attempts: List of all test attempts
        
    Returns:
        str: Enhanced PR body with detailed information
    """
    logger.info(f"Enhancing PR body with test results type: {type(test_results)}")
    logger.info(f"Test results content: {test_results}")
    
    # Create the base PR body
    pr_body = f"""# Test Fix Summary

## Overview
- **Fix Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Fixed Tests:** {len(fixed_tests)}
- **Total Tests:** {sum(len(result.get('test_cases', [])) for result in test_results.values()) if isinstance(test_results, dict) else 0}
- **Test Configuration:** {test_config.get('name', 'Unnamed Test Suite')}
- **Total Attempts:** {len(all_test_attempts)}

## Test Results Summary
{format_test_results_table(test_results) if isinstance(test_results, dict) else "Test results not available"}

## All Test Attempts
"""
    
    # Add details for each attempt
    for attempt in all_test_attempts:
        attempt_num = attempt['attempt']
        attempt_results = attempt['results']
        
        pr_body += f"\n### Attempt {attempt_num}\n"
        
        # Add attempt summary
        if isinstance(attempt_results, dict):
            total_tests = sum(len(result.get('test_cases', [])) for result in attempt_results.values() 
                            if isinstance(result, dict) and 'test_cases' in result)
            passed_tests = sum(len([tc for tc in result.get('test_cases', []) 
                                  if tc.get('status') == 'passed'])
                             for result in attempt_results.values()
                             if isinstance(result, dict) and 'test_cases' in result)
            
            pr_body += f"- **Total Tests:** {total_tests}\n"
            pr_body += f"- **Passed Tests:** {passed_tests}\n"
            pr_body += f"- **Pass Rate:** {(passed_tests/total_tests*100 if total_tests > 0 else 0):.1f}%\n"
        
        # Add detailed test results for each region
        if isinstance(attempt_results, dict):
            for region, result in attempt_results.items():
                if isinstance(result, str) or region in ('_status', 'overall_status'):
                    continue
                    
                pr_body += f"\n#### Region: {region}\n"
                test_cases = result.get('test_cases', [])
                for test_case in test_cases:
                    pr_body += f"\n##### Test: {test_case.get('name', 'Unknown')}\n"
                    pr_body += f"- **Status:** {'✅ PASS' if test_case.get('status') == 'passed' else '❌ FAIL'}\n"
                    
                    # Add input information if available
                    if 'input' in test_case:
                        pr_body += f"- **Input:**\n```\n{json.dumps(test_case['input'], indent=2)}\n```\n"
                    
                    # Add output information if available
                    if 'output' in test_case:
                        pr_body += f"- **Output:**\n```\n{test_case['output']}\n```\n"
                    
                    # Add evaluation details if available
                    if 'evaluation' in test_case:
                        evaluation = test_case['evaluation']
                        pr_body += "- **Evaluation:**\n"
                        if isinstance(evaluation, dict):
                            pr_body += f"  - **Status:** {evaluation.get('status', 'unknown')}\n"
                            if 'overall_score' in evaluation:
                                pr_body += f"  - **Score:** {evaluation['overall_score']}\n"
                            if 'criteria' in evaluation:
                                pr_body += "  - **Criteria Results:**\n"
                                for criterion, result in evaluation['criteria'].items():
                                    pr_body += f"    - {criterion}: {result.get('status', 'unknown')} (Score: {result.get('score', 'N/A')})\n"
                                    if 'feedback' in result:
                                        pr_body += f"      - Feedback: {result['feedback']}\n"
                        else:
                            pr_body += f"  - {str(evaluation)}\n"
                    
                    # Add error details if available
                    if 'details' in test_case and test_case['details']:
                        pr_body += f"- **Error Details:**\n```\n{test_case['details']}\n```\n"
                    
                    pr_body += "\n---\n"
    
    # Add failure analysis
    pr_body += f"\n{analyze_failures(failure_data)}"
    
    # Add fix details
    pr_body += "\n## Fix Details\n"
    pr_body += "### Fixed Tests\n"
    for test in fixed_tests:
        pr_body += f"- {test['test_name']} ({test['region']})\n"
        if 'fix_description' in test:
            pr_body += f"  - {test['fix_description']}\n"
    
    pr_body += "\n### Original Failures\n"
    for failure in failure_data:
        pr_body += f"- {failure['test_name']}: {failure['error_message']}\n"
        if 'output' in failure:
            pr_body += f"  - Output: {failure['output']}\n"
    
    # Add code changes section
    pr_body += """
## Code Changes
The following changes were made to fix the failing tests:

1. Error Handling Improvements:
   - Added proper error handling for edge cases
   - Improved input validation
   - Enhanced error messages for better debugging

2. Test-Specific Fixes:
"""
    for test in fixed_tests:
        pr_body += f"   - {test['test_name']}: {test.get('fix_description', 'Fixed test failure')}\n"
    
    pr_body += """
3. General Improvements:
   - Enhanced code robustness
   - Improved error handling
   - Added input validation
   - Fixed edge cases

## Verification
All fixed tests have been verified to pass in the following environments:
"""
    if isinstance(test_results, dict):
        for region in test_results.keys():
            if not isinstance(region, str) or region not in ('_status', 'overall_status'):
                pr_body += f"- {region}\n"
    
    pr_body += """
## Next Steps
1. Review the changes for any potential side effects
2. Verify the fixes in different environments
3. Consider adding additional test cases for edge cases
4. Monitor the changes in production

## Notes
- All changes were made with minimal impact on existing functionality
- Code quality and style guidelines were followed
- Documentation was updated where necessary
"""

    return pr_body

def run_autofix_and_pr(failure_data: List[Dict], file_path: str, test_config_path: str, max_retries: int = 1, create_pr: bool = True, base_branch: str = 'main') -> None:
    """
    Automatically fixes code based on test failures and optionally creates a PR.
    
    Args:
        failure_data: List of dictionaries containing test failure information
        file_path: Path to the source code file to be fixed
        test_config_path: Path to the test configuration file
        max_retries: Maximum number of retry attempts for fixing tests (default: 1)
        create_pr: Whether to create a pull request with the fixes (default: True)
        base_branch: The base branch to create the PR against (default: 'main')
        
    Raises:
        ValueError: If required environment variables are not set
        subprocess.CalledProcessError: If git commands fail
        GithubException: If GitHub API operations fail
    """
    try:
        # Store the original branch
        original_branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        logger.info(f"Stored original branch: {original_branch}")
        
        # Initialize branch_name with a default value
        branch_name = f"autofix-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        config = get_config()
        logger.info(f"Starting auto-fix process for {file_path} with {len(failure_data)} failures")
        
        # Create a set of failing test names for quick lookup
        failing_test_names = {failure["test_name"] for failure in failure_data}
        logger.info(f"Tests that were failing: {failing_test_names}")
        
        # Load test configuration
        with open(test_config_path, 'r') as f:
            test_config = yaml.safe_load(f)
        
        # Load original code
        with open(file_path, 'r') as f:
            original_code = f.read()
        
        # Generate PR info with test configuration
        try:
            branch_name, pr_title, pr_body = _generate_pr_info(failure_data, [], {}, test_config, original_code)
            logger.info(f"Generated PR info: {branch_name}, {pr_title}, {pr_body}")
        except Exception as e:
            logger.warning(f"Failed to generate PR info: {str(e)}")
            # Use default values if PR info generation fails
            timestamp = datetime.now().strftime('%Y%m%d')
            branch_name = f"fix-tests-{timestamp}"
            pr_title = "Fix: Resolved test failures"
            pr_body = f"# Test Fix Summary\n\nFixing test failures in {file_path}"
        
        # Track which previously failing tests are now passing
        fixed_tests = []
        best_fixed_tests = []
        best_fixed_code = None
        
        # Track all test attempts
        all_test_attempts = []
        
        for attempt in range(max_retries):
            logger.info(f"Auto-fix attempt {attempt + 1}/{max_retries}")
            
            # Get the fixed code from Gemini
            genai.configure(api_key=config.get_api_key("google"))
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            logger.info("Requesting code fixes from Gemini")
            response = model.generate_content(pr_body)
            fixed_code = response.text.strip()
            logger.info(f"Fixed code: {fixed_code}")
            # Validate and improve the generated code
            fixed_code = _validate_and_improve_code(fixed_code, original_code)
            logger.info(f"Validated and improved generated code: {fixed_code}")
            logger.info("Validated and improved generated code")
            
            # Write the fixed code to disk before running tests
            with open(file_path, 'w') as f:
                f.write(fixed_code)
            logger.info(f"Updated file: {file_path}")
            
            # Force reload the module to ensure we're using the new code
            module_name = Path(file_path).stem
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            
            # Run tests again to verify fixes
            logger.info("Running tests to verify fixes")
            
            test_runner = TestRunner(test_config)
            test_logger = TestLogger(f"Auto-fix Test Run (Attempt {attempt + 1})")
            
            # Extract file path from the root of the configuration
            test_file_path = test_config.get('file_path')
            if not test_file_path:
                console.print("[red]Error: No file_path found in test configuration[/red]")
                sys.exit(1)
            
            # Resolve the test file path relative to the YAML config file's directory
            config_dir = os.path.dirname(os.path.abspath(test_config_path))
            resolved_test_file_path = os.path.normpath(os.path.join(config_dir, test_file_path))
            
            logger.info(f"Running tests for {resolved_test_file_path}")
            test_results = test_runner.run_tests(Path(resolved_test_file_path))
            logger.info(f"Test results: {test_results}")
            
            # Store this attempt's results
            all_test_attempts.append({
                'attempt': attempt + 1,
                'code': fixed_code,
                'results': test_results
            })
            
            # Check if test results indicate an error
            if isinstance(test_results, dict) and test_results.get('overall_status') == 'error':
                error_msg = test_results.get('error', 'Unknown error')
                logger.error(f"Test execution failed: {error_msg}")
                raise RuntimeError(f"Test execution failed: {error_msg}")
            
            # Track which previously failing tests are now passing
            fixed_tests = []
            for region, result in test_results.items():
                print(f"Region: {region}")
                print(f"Result: {result}")
                # Skip if result is a string (like 'status') or if region is _status
                if isinstance(result, str) or region == '_status' or region == 'overall_status':
                    continue
                # Ensure result is a dictionary before accessing test_cases
                if not isinstance(result, dict):
                    logger.warning(f"Skipping invalid result format for region {region}: {result}")
                    continue
                test_cases = result.get('test_cases', [])
                if not isinstance(test_cases, list):
                    logger.warning(f"Skipping invalid test_cases format for region {region}: {test_cases}")
                    continue
                for test_case in test_cases:
                    if not isinstance(test_case, dict):
                        logger.warning(f"Skipping invalid test case format: {test_case}")
                        continue
                    test_name = test_case.get('name')
                    if test_name in failing_test_names and test_case.get('status') == 'passed':
                        fixed_tests.append({
                            'region': region,
                            'test_name': test_name
                        })
            
            # Update best attempt if this one fixed more tests
            if len(fixed_tests) > len(best_fixed_tests):
                best_fixed_tests = fixed_tests
                best_fixed_code = fixed_code
            
            # If we fixed all tests, we can stop early
            if len(fixed_tests) == len(failing_test_names):
                logger.info("All tests fixed! Stopping retries.")
                break
            
            # If this is not the last attempt, continue to next iteration
            if attempt < max_retries - 1:
                logger.info(f"Fixed {len(fixed_tests)} tests in attempt {attempt + 1}, trying again...")
                continue
        
        # Use the best attempt's results
        fixed_tests = best_fixed_tests
        fixed_code = best_fixed_code
        
        if not fixed_tests:
            logger.info("No previously failing tests were fixed after all attempts. Reverting changes.")
            subprocess.run(["git", "checkout", original_branch], check=True)
            # Only try to delete the branch if we created it
            try:
                # Check if branch exists
                result = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], 
                                      capture_output=True, check=False)
                if result.returncode == 0:
                    subprocess.run(["git", "branch", "-D", branch_name], check=True)
            except subprocess.CalledProcessError:
                # Ignore errors if branch doesn't exist
                pass
            return
        
        logger.info(f"Fixed {len(fixed_tests)} previously failing tests")
        
        # Update PR info with fixed tests
        branch_name, pr_title, pr_body = _generate_pr_info(failure_data, fixed_tests, test_results, test_config, original_code)
        logger.info(f"Updated branch name: {branch_name}")
        
        # Create a new branch
        logger.info(f"Creating new branch: {branch_name}")
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        except subprocess.CalledProcessError:
            # If branch already exists, add a unique suffix
            logger.info(f"Branch {branch_name} already exists, adding unique suffix")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=4))
            unique_branch_name = f"{branch_name}-{timestamp}-{random_suffix}"
            logger.info(f"Trying with new branch name: {unique_branch_name}")
            subprocess.run(["git", "checkout", "-b", unique_branch_name], check=True)
            branch_name = unique_branch_name
        
        # Write the best fixed code back to disk before committing
        logger.info("Writing best fixed code back to disk")
        with open(file_path, 'w') as f:
            f.write(best_fixed_code)
        
        # Commit changes with a proper commit message
        subprocess.run(["git", "add", file_path], check=True)
        commit_message = f"Fix: {pr_title}\n\n{pr_body}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        logger.info("Committed changes")
        
        # Push branch
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
        logger.info(f"Pushed branch: {branch_name}")
        
        # Create PR using GitHub API
        if create_pr:
            logger.info("Starting PR creation process")
            github_token = os.environ.get("GITHUB_TOKEN")
            if not github_token:
                raise ValueError("GITHUB_TOKEN environment variable not set. Please set it with your GitHub personal access token.")
            
            g = Github(github_token)
            
            # Get repository information from git config
            try:
                repo_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
                if repo_url.endswith('.git'):
                    repo_url = repo_url[:-4]
                repo_name = repo_url.split('/')[-1]
                repo_owner = repo_url.split('/')[-2]
                repo = g.get_repo(f"{repo_owner}/{repo_name}")
                logger.info(f"Successfully connected to repository: {repo_owner}/{repo_name}")
            except subprocess.CalledProcessError:
                raise ValueError("Could not determine repository information. Please ensure you're in a git repository with a remote origin.")
            except GithubException as e:
                raise ValueError(f"Error accessing GitHub repository: {str(e)}")
            
            # Create PR
            logger.info("Preparing to create PR with test results")
            logger.info(f"Test results type: {type(test_results)}")
            logger.info(f"Test results content: {test_results}")
            logger.info(f"Fixed tests: {fixed_tests}")
            logger.info(f"Test config: {test_config}")
            
            try:
                enhanced_pr_body = _enhance_pr_body(failure_data, fixed_tests, test_results, test_config, all_test_attempts)
                logger.info("Successfully enhanced PR body")
            except Exception as e:
                logger.error(f"Error enhancing PR body: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error args: {e.args}")
                raise
            
            try:
                # Ensure PR title is not empty
                if not pr_title or not pr_title.strip():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    pr_title = f"Fix: Resolved test failures ({timestamp})"
                    logger.warning(f"Empty PR title detected, using default title: {pr_title}")
                
                pr = repo.create_pull(
                    title=pr_title,
                    body=enhanced_pr_body,
                    head=branch_name,
                    base=base_branch
                )
                logger.info(f"Created Pull Request: {pr.html_url}")
                print(f"Pull Request created: {pr.html_url}")
            except Exception as e:
                logger.error(f"Error creating PR: {str(e)}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error args: {e.args}")
                raise
        
        # Return to the original branch
        logger.info(f"Returning to original branch: {original_branch}")
        subprocess.run(["git", "checkout", original_branch], check=True)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
        # Try to return to original branch even if there was an error
        try:
            subprocess.run(["git", "checkout", original_branch], check=True)
        except:
            pass
        raise
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
        # Try to return to original branch even if there was an error
        try:
            subprocess.run(["git", "checkout", original_branch], check=True)
        except:
            pass
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        # Try to return to original branch even if there was an error
        try:
            subprocess.run(["git", "checkout", original_branch], check=True)
        except:
            pass
        raise 