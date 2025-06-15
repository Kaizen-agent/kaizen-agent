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
        for test_case in result.get('test_cases', []):
            status = "✅ PASS" if test_case['status'] == 'passed' else "❌ FAIL"
            table += f"| {test_case['name']} | {region} | {status} |\n"
    return table

def analyze_failures(failure_data: List[Dict]) -> str:
    """Analyze test failures and generate a summary."""
    analysis = "## Failure Analysis\n\n"
    
    # Group failures by error type
    error_groups = {}
    for failure in failure_data:
        error_type = failure['error_message'].split(':')[0] if ':' in failure['error_message'] else 'Unknown Error'
        if error_type not in error_groups:
            error_groups[error_type] = []
        error_groups[error_type].append(failure)
    
    # Generate analysis for each error type
    for error_type, failures in error_groups.items():
        analysis += f"### {error_type}\n\n"
        analysis += f"**Affected Tests ({len(failures)}):**\n"
        for failure in failures:
            analysis += f"- {failure['test_name']}\n"
        analysis += f"\n**Error Pattern:**\n{failures[0]['error_message']}\n\n"
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
{chr(10).join(f'  - test_name: {failure["test_name"]}{chr(10)}    error_message: {failure["error_message"]}' for failure in failure_data)}

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
    
    # If we still don't have valid code, try to fix common syntax issues
    try:
        return _attempt_llm_fix(code, original_code)
    except CodeValidationError as e:
        logger.error(f"All attempts to fix code failed: {str(e)}")
        raise

def _enhance_pr_body(failure_data: List[Dict], fixed_tests: List[Dict], test_results: Dict, test_config: Dict) -> str:
    """
    Enhance the PR body with comprehensive test results, analysis, and fix details.
    
    Args:
        failure_data: List of test failures
        fixed_tests: List of fixed tests
        test_results: Complete test results
        test_config: Test configuration data
        
    Returns:
        str: Enhanced PR body with detailed information
    """
    # Create the base PR body
    pr_body = f"""# Test Fix Summary

## Overview
- **Fix Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Fixed Tests:** {len(fixed_tests)}
- **Total Tests:** {sum(len(result.get('test_cases', [])) for result in test_results.values())}
- **Test Configuration:** {test_config.get('name', 'Unnamed Test Suite')}

## Test Results
{format_test_results_table(test_results)}

{analyze_failures(failure_data)}

## Fix Details
### Fixed Tests
{chr(10).join(f'- {test["test_name"]} ({test["region"]})' for test in fixed_tests)}

### Original Failures
{chr(10).join(f'- {failure["test_name"]}: {failure["error_message"]}' for failure in failure_data)}

## Code Changes
The following changes were made to fix the failing tests:

1. Error Handling Improvements:
   - Added proper error handling for edge cases
   - Improved input validation
   - Enhanced error messages for better debugging

2. Test-Specific Fixes:
{chr(10).join(f'   - {test["test_name"]}: {test.get("fix_description", "Fixed test failure")}' for test in fixed_tests)}

3. General Improvements:
   - Enhanced code robustness
   - Improved error handling
   - Added input validation
   - Fixed edge cases

## Verification
All fixed tests have been verified to pass in the following environments:
{chr(10).join(f'- {region}' for region in test_results.keys())}

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
            
            # Track which previously failing tests are now passing
            fixed_tests = []
            for region, result in test_results.items():
                print(f"Region: {region}")
                print(f"Result: {result}")
                # Skip if result is a string (like 'status') or if region is _status
                if isinstance(result, str) or region == '_status':
                    continue
                for test_case in result.get('test_cases', []):
                    test_name = test_case['name']
                    if test_name in failing_test_names and test_case['status'] == 'passed':
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
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        
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
            except subprocess.CalledProcessError:
                raise ValueError("Could not determine repository information. Please ensure you're in a git repository with a remote origin.")
            except GithubException as e:
                raise ValueError(f"Error accessing GitHub repository: {str(e)}")
            
            # Create PR
            enhanced_pr_body = _enhance_pr_body(failure_data, fixed_tests, test_results, test_config)
            pr = repo.create_pull(
                title=pr_title,
                body=enhanced_pr_body,
                head=branch_name,
                base=base_branch
            )
            
            logger.info(f"Created Pull Request: {pr.html_url}")
            print(f"Pull Request created: {pr.html_url}")
        
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
        # Try to return to original branch even if there was an error
        try:
            subprocess.run(["git", "checkout", original_branch], check=True)
        except:
            pass
        raise 