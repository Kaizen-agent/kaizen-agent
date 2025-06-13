import os
import uuid
from typing import List, Dict
import subprocess
from pathlib import Path
import openai
from github import Github
from github.GithubException import GithubException

from .logger import get_logger
from .config import get_config

logger = get_logger(__name__)

def run_autofix_and_pr(failure_data: List[Dict], file_path: str) -> None:
    """
    Automatically fixes code based on test failures and creates a PR.
    
    Args:
        failure_data: List of dictionaries containing test failure information
        file_path: Path to the source code file to be fixed
        
    Raises:
        ValueError: If required environment variables are not set
        subprocess.CalledProcessError: If git commands fail
        GithubException: If GitHub API operations fail
    """
    try:
        config = get_config()
        logger.info(f"Starting auto-fix process for {file_path} with {len(failure_data)} failures")
        
        # Read the original code
        with open(file_path, 'r') as f:
            original_code = f.read()
        
        # Prepare the prompt for GPT-4
        system_prompt = """You are a senior software engineer. Improve the following code by fixing the issues described. 
        Make only minimal changes necessary to resolve all problems while preserving existing logic."""
        
        user_prompt = f"""original_code: |
{original_code}

failures:
{chr(10).join(f'  - test_name: {failure["test_name"]}{chr(10)}    error_message: {failure["error_message"]}' for failure in failure_data)}

task: Modify the code to resolve all listed issues and return only the full fixed file."""

        # Get the fixed code from GPT-4
        client = openai.OpenAI(api_key=config.get_api_key("openai"))
        logger.info("Requesting code fixes from GPT-4")
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        
        fixed_code = response.choices[0].message.content.strip()
        logger.info("Received fixed code from GPT-4")
        
        # Create a new branch
        branch_name = f"kaizen-fix-{uuid.uuid4().hex[:8]}"
        logger.info(f"Creating new branch: {branch_name}")
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        
        # Write the fixed code
        with open(file_path, 'w') as f:
            f.write(fixed_code)
        logger.info(f"Updated file: {file_path}")
        
        # Create commit message
        commit_body = "Fixed the following test failures:\n" + "\n".join(
            f"- {failure['test_name']}: {failure['error_message']}"
            for failure in failure_data
        )
        
        # Commit changes
        subprocess.run(["git", "add", file_path], check=True)
        subprocess.run(["git", "commit", "-m", "fix: resolved multiple Kaizen Agent test failures", 
                       "-m", commit_body], check=True)
        logger.info("Committed changes")
        
        # Push branch
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
        logger.info(f"Pushed branch: {branch_name}")
        
        # Create PR using GitHub API
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
        
        # Create PR body
        pr_body = f"""## Fixed Test Failures\n\n{commit_body}\n\n"""
        if response.choices[0].message.content:
            pr_body += f"## GPT-4 Explanation\n\n{response.choices[0].message.content}\n"
        
        # Create PR
        try:
            pr = repo.create_pull(
                title="Fix: Addressed multiple agent failures",
                body=pr_body,
                head=branch_name,
                base="main"
            )
            
            logger.info(f"Created Pull Request: {pr.html_url}")
            print(f"Pull Request created: {pr.html_url}")
            
        except GithubException as e:
            raise ValueError(f"Error creating pull request: {str(e)}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
        raise
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise 