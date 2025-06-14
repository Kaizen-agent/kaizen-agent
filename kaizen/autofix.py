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

def _generate_pr_info(failure_data: List[Dict], fixed_tests: List[Dict], test_results: Dict) -> Tuple[str, str, str]:
    """
    Generate meaningful branch name, PR title, and body using LLM.
    
    Args:
        failure_data: List of test failures
        fixed_tests: List of fixed tests
        test_results: Complete test results
        
    Returns:
        Tuple of (branch_name, pr_title, pr_body)
    """
    try:
        config = get_config()
        genai.configure(api_key=config.get_api_key("google"))
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Prepare prompt for LLM
        prompt = f"""Based on the following test failures and fixes, generate:
1. A short, descriptive branch name (max 50 chars, use hyphens)
2. A clear PR title (max 100 chars)
3. A detailed PR body explaining the changes

Test Failures:
{json.dumps(failure_data, indent=2)}

Fixed Tests:
{json.dumps(fixed_tests, indent=2)}

Test Results:
{json.dumps(test_results, indent=2)}

Requirements:
- Branch name should reflect the main purpose of the fixes
- PR title should be clear and concise
- PR body should explain what was fixed and why
- Focus on the most important changes
"""
        
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

def run_autofix_and_pr(failure_data: List[Dict], file_path: str, test_config_path: str, max_retries: int = 1, create_pr: bool = True) -> None:
    """
    Automatically fixes code based on test failures and optionally creates a PR.
    
    Args:
        failure_data: List of dictionaries containing test failure information
        file_path: Path to the source code file to be fixed
        test_config_path: Path to the test configuration file
        max_retries: Maximum number of retry attempts for fixing tests (default: 1)
        create_pr: Whether to create a pull request with the fixes (default: True)
        
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
        
        # Read the original code
        with open(file_path, 'r') as f:
            original_code = f.read()
        
        # Prepare the prompt for Gemini
        system_prompt = """You are a senior software engineer. Improve the following code by fixing the issues described. 
        Make only minimal changes necessary to resolve all problems while preserving existing logic."""
        
        user_prompt = f"""original_code: |
{original_code}

failures:
{chr(10).join(f'  - test_name: {failure["test_name"]}{chr(10)}    error_message: {failure["error_message"]}' for failure in failure_data)}

task: Modify the code to resolve all listed issues and return only the full fixed file."""

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
            response = model.generate_content(user_prompt)
            fixed_code = response.text.strip()
            logger.info("Received fixed code from Gemini")
            
            # Write the fixed code to disk before running tests
            with open(file_path, 'w') as f:
                f.write(fixed_code)
            logger.info(f"Updated file: {file_path}")
            
            # Run tests again to verify fixes
            logger.info("Running tests to verify fixes")
            
            # Load test configuration
            with open(test_config_path, 'r') as f:
                test_config = yaml.safe_load(f)
                
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
        branch_name, pr_title, pr_body = _generate_pr_info(failure_data, fixed_tests, test_results)
        logger.info(f"Updated branch name: {branch_name}")
        
        # Create a new branch
        logger.info(f"Creating new branch: {branch_name}")
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        
        # Commit changes (file is already updated from earlier)
        subprocess.run(["git", "add", file_path], check=True)
        subprocess.run(["git", "commit", "-m", pr_title, "-m", pr_body], check=True)
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
            try:
                pr = repo.create_pull(
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base="main"
                )
                
                logger.info(f"Created Pull Request: {pr.html_url}")
                print(f"Pull Request created: {pr.html_url}")
                
            except GithubException as e:
                raise ValueError(f"Error creating pull request: {str(e)}")
        
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