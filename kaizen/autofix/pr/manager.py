import os
import logging
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, TypedDict, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
from github import Github, GithubException
from github.PullRequest import PullRequest
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)

class PRCreationError(Exception):
    """Error raised when PR creation fails."""
    pass

class GitHubConfigError(Exception):
    """Error raised when GitHub configuration is invalid."""
    pass

class GitConfigError(Exception):
    """Error raised when git configuration is invalid."""
    pass

class TestCase(TypedDict):
    name: str
    status: str
    input: Optional[str]
    expected_output: Optional[str]
    actual_output: Optional[str]
    evaluation: Optional[str]
    reason: Optional[str]

class Attempt(TypedDict):
    status: str
    test_cases: List[TestCase]

class AgentInfo(TypedDict):
    name: str
    version: str
    description: str

class TestResults(TypedDict):
    agent_info: Optional[AgentInfo]
    attempts: List[Attempt]
    additional_summary: Optional[str]

class CodeChange(TypedDict):
    description: str
    reason: Optional[str]

class PromptChange(TypedDict):
    before: str
    after: str
    reason: Optional[str]

class Changes(TypedDict):
    prompt_changes: Optional[List[PromptChange]]
    # Other file changes will be Dict[str, List[CodeChange]]

@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""
    token: str
    base_branch: str = 'main'

class PRManager:
    """A class for managing pull requests."""
    
    def __init__(self, config: Dict):
        """
        Initialize the PR manager.
        
        Args:
            config: Configuration dictionary containing GitHub settings
        """
        self.config = config
        self.pr_data = {}
        self.github_config = self._initialize_github_config()
        self.github = Github(self.github_config.token)
        
    def _initialize_github_config(self) -> GitHubConfig:
        """
        Initialize GitHub configuration.
        
        Returns:
            GitHubConfig: Initialized GitHub configuration
            
        Raises:
            GitHubConfigError: If GitHub token is not set
        """
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise GitHubConfigError("GITHUB_TOKEN environment variable not set. Please set it with your GitHub personal access token.")
            
        return GitHubConfig(
            token=token,
            base_branch=self.config.get('base_branch', 'main')
        )
        
    def create_pr(self, changes: Dict, test_results: Dict) -> Dict:
        """
        Create a pull request with the given changes and test results.
        
        Args:
            changes: Dictionary containing code changes
            test_results: Dictionary containing test results
            
        Returns:
            Dict containing PR information
            
        Raises:
            PRCreationError: If PR creation fails
        """
        try:
            # Log PR creation start
            logger.info("Starting PR creation", extra={
                'changes_count': len(changes),
                'test_results_keys': list(test_results.keys()) if test_results else []
            })
            
            # Validate inputs
            if not changes:
                logger.warning("No changes provided for PR creation")
            
            if not test_results:
                logger.warning("No test results provided for PR creation")
            
            # Initialize PR data
            self.pr_data = {
                'title': self._generate_pr_title(changes, test_results),
                'description': self._generate_pr_description(changes, test_results),
                'changes': changes,
                'test_results': test_results,
                'status': 'draft',
                'created_at': datetime.now().isoformat()
            }
            
            # Log generated PR data
            logger.info("Generated PR data", extra={
                'title': self.pr_data['title'],
                'title_length': len(self.pr_data['title']),
                'description_length': len(self.pr_data['description']),
                'status': self.pr_data['status']
            })
            
            # Validate PR data
            self._validate_pr_data()
            
            # Check git status
            self._check_git_status()
            
            # Create actual PR on GitHub
            pr = self._create_github_pr()
            
            # Update PR data with GitHub PR information
            self.pr_data.update({
                'status': 'ready',
                'pr_number': pr.number,
                'pr_url': pr.html_url,
                'branch': pr.head.ref
            })
            
            # Log PR creation completion
            logger.info("PR creation completed successfully", extra={
                'pr_title': self.pr_data['title'],
                'pr_url': self.pr_data['pr_url'],
                'pr_number': self.pr_data['pr_number'],
                'branch': self.pr_data['branch']
            })
            
            return self.pr_data
            
        except Exception as e:
            logger.error("PR creation failed", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': str(e.__traceback__)
            })
            
            # Update status to error
            if hasattr(self, 'pr_data'):
                self.pr_data['status'] = 'error'
                self.pr_data['error'] = str(e)
            
            raise PRCreationError(f"Failed to create PR: {str(e)}")
    
    def _generate_pr_title(self, changes: Dict, test_results: Dict) -> str:
        """
        Generate a title for the pull request.
        
        Args:
            changes: Dictionary containing code changes
            test_results: Dictionary containing test results
            
        Returns:
            str: PR title
        """
        try:
            
            title = "Fix: Code changes by Kaizen Agent"
            
            return title
            
        except Exception as e:
            logger.error("Error generating PR title", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return "Fix: Code changes"
    
    def _generate_pr_description(self, changes: Dict[str, List[CodeChange]], test_results: TestResults) -> str:
        """
        Generate a description for the pull request using LLM.
        
        Args:
            changes: Dictionary containing code changes, keyed by file path
            test_results: Dictionary containing test results and agent information
            
        Returns:
            str: Formatted PR description generated by LLM
            
        Raises:
            ValueError: If required data is missing or malformed
        """
        try:
            # Initialize LLM
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("GOOGLE_API_KEY not found, using fallback description")
                return self._generate_fallback_description(changes, test_results)
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            
            # Prepare the prompt for LLM
            prompt = self._build_pr_description_prompt(changes, test_results)
            
            # Get response from LLM
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for consistent results
                    max_output_tokens=8000,
                    top_p=0.8,
                    top_k=40,
                )
            )
            
            if not response or not hasattr(response, 'text') or not response.text:
                logger.warning("Empty response from LLM, using fallback description")
                return self._generate_fallback_description(changes, test_results)
            
            description = response.text.strip()
            
            # Validate the description
            if len(description) < 50:  # Too short
                logger.warning("LLM generated description too short, using fallback")
                return self._generate_fallback_description(changes, test_results)
            
            logger.info("Successfully generated PR description using LLM", extra={
                'description_length': len(description)
            })
            
            return description
            
        except Exception as e:
            logger.error("Error generating PR description with LLM", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return self._generate_fallback_description(changes, test_results)
    
    def _build_pr_description_prompt(self, changes: Dict[str, List[CodeChange]], test_results: TestResults) -> str:
        """
        Build a comprehensive prompt for LLM to generate PR description.
        
        Args:
            changes: Dictionary containing code changes
            test_results: Dictionary containing test results
            
        Returns:
            str: Formatted prompt for LLM
        """
        prompt = """You are an expert software developer creating a pull request description. 
Generate a comprehensive, well-structured PR description based on the provided test results and code changes.

The description should include the following sections in this exact order:

1. **Summary** - A concise overview of what was accomplished, including agent information if available
2. **Test Results Summary** - A markdown table showing test case results across all attempts
3. **Detailed Results** - For each attempt, show detailed input/output/evaluation for each test case
4. **Code Changes** - Summary of code modifications made
5. **Additional Summary** - Any additional insights or notes

## Format Requirements:

### Test Results Summary Table:
Create a markdown table with these exact columns:
| Test Case | Attempt 1 | Attempt 2 | Attempt 3 | Final Status | Reason |

- Use the status values from the test data (PASS, FAIL, ERROR, etc.)
- Show "N/A" for attempts that don't exist
- Use the reason from the final attempt for each test case

### Detailed Results Section:
For each attempt, create subsections like:
#### Attempt 1
**Status:** [overall status]

For each test case in the attempt:
**Test Case:** [name]
- **Input:** [input value or description]
- **Expected Output:** [expected output]
- **Actual Output:** [actual output]
- **Result:** [PASS/FAIL/ERROR]
- **Evaluation:** [evaluation details if available]
- **Reason:** [reason for result if available]

### Code Changes Section:
List each file that was modified with a brief description of changes made.

Here is the data to work with:

## Test Results Data:
"""
        
        # Add test results data
        prompt += f"\n{json.dumps(test_results, indent=2, default=str)}"
        
        # Add changes data
        prompt += "\n\n## Code Changes Data:\n"
        prompt += f"\n{json.dumps(changes, indent=2, default=str)}"
        
        prompt += """

## Instructions:
- Make the summary clear and actionable, mentioning the agent if available
- Create the exact table format specified above for test results
- For detailed results, clearly show input, expected output, actual output, and evaluation for each test case in each attempt
- Highlight any patterns or improvements across attempts
- Make the code changes section concise but informative
- Ensure all sections are properly formatted with markdown
- Keep the overall description professional and informative
- If any data is missing or null, use "N/A" or "Not available"
- Make sure the input/output/evaluation for each test case is very clear and readable

Generate the complete PR description now:"""
        
        return prompt
    
    def _generate_fallback_description(self, changes: Dict[str, List[CodeChange]], test_results: TestResults) -> str:
        """
        Generate a fallback description when LLM is not available.
        
        Args:
            changes: Dictionary containing code changes
            test_results: Dictionary containing test results
            
        Returns:
            str: Fallback PR description
        """
        try:
            description = []
            
            # Add each section using existing methods
            description.extend(self._generate_agent_summary(test_results))
            description.extend(self._generate_test_results_summary(test_results))
            description.extend(self._generate_detailed_results(test_results))
            description.extend(self._generate_code_changes(changes))
            description.extend(self._generate_prompt_changes(changes))
            description.extend(self._generate_additional_summary(test_results))
            
            return "\n".join(description)
            
        except Exception as e:
            logger.error("Error generating fallback description", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return "Code changes and test results"
    
    def test_llm_description_generation(self, changes: Dict[str, List[CodeChange]], test_results: TestResults) -> Dict[str, Any]:
        """
        Test the LLM description generation independently.
        
        Args:
            changes: Dictionary containing code changes
            test_results: Dictionary containing test results
            
        Returns:
            Dict containing test results with generated description and metadata
        """
        try:
            logger.info("Testing LLM description generation")
            
            # Generate description using LLM
            description = self._generate_pr_description(changes, test_results)
            
            # Check if LLM was used
            api_key = os.environ.get("GOOGLE_API_KEY")
            used_llm = bool(api_key)
            
            result = {
                'success': True,
                'description': description,
                'description_length': len(description),
                'used_llm': used_llm,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("LLM description generation test completed", extra={
                'used_llm': used_llm,
                'description_length': len(description)
            })
            
            return result
            
        except Exception as e:
            logger.error("LLM description generation test failed", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_agent_summary(self, test_results: TestResults) -> List[str]:
        """Generate the agent summary section."""
        description = ["## Agent Summary"]
        
        if not test_results.get('agent_info'):
            description.append("\nNo agent information available")
            return description
        
        agent_info = test_results['agent_info']
        description.extend([
            f"\nAgent: {agent_info.get('name', 'Unknown')}",
            f"Version: {agent_info.get('version', 'Unknown')}",
            f"Description: {agent_info.get('description', 'No description available')}"
        ])
        
        return description
    
    def _generate_test_results_summary(self, test_results: TestResults) -> List[str]:
        """Generate the test results summary table."""
        description = ["\n## Test Results Summary"]
        
        if not test_results.get('attempts'):
            description.append("\nNo test results available")
            return description
        
        # Create table header
        description.extend([
            "\n| Test Case | Attempt 1 | Attempt 2 | Attempt 3 | Reason |",
            "|-----------|-----------|-----------|-----------|--------|"
        ])
        
        # Add test cases
        for test_case in test_results['attempts'][0]['test_cases']:
            case_name = test_case['name']
            row = [case_name]
            
            # Add results for each attempt
            for attempt in test_results['attempts']:
                result = next((tc['status'] for tc in attempt['test_cases'] if tc['name'] == case_name), 'N/A')
                row.append(result)
            
            # Add reason from the last attempt
            reason = next((tc['reason'] for tc in test_results['attempts'][-1]['test_cases'] if tc['name'] == case_name), 'N/A')
            row.append(reason)
            
            description.append(f"| {' | '.join(row)} |")
        
        return description
    
    def _generate_detailed_results(self, test_results: TestResults) -> List[str]:
        """Generate detailed test results for each attempt."""
        description = ["\n## Detailed Results"]
        
        if not test_results.get('attempts'):
            return description
        
        for i, attempt in enumerate(test_results['attempts'], 1):
            description.extend([
                f"\n### Attempt {i}",
                f"Status: {attempt['status']}"
            ])
            
            for test_case in attempt['test_cases']:
                description.extend([
                    f"\n#### {test_case['name']}",
                    f"Input: {test_case.get('input', 'N/A')}",
                    f"Expected Output: {test_case.get('expected_output', 'N/A')}",
                    f"Actual Output: {test_case.get('actual_output', 'N/A')}",
                    f"Result: {test_case['status']}",
                    f"Evaluation: {test_case.get('evaluation', 'N/A')}"
                ])
        
        return description
    
    def _generate_code_changes(self, changes: Dict[str, List[CodeChange]]) -> List[str]:
        """Generate the code changes section."""
        description = ["\n## Code Changes"]
        
        for file_path, file_changes in changes.items():
            if file_path == 'prompt_changes':
                continue
            
            description.append(f"\n### {file_path}")
            for change in file_changes:
                description.append(f"- {change['description']}")
                if change.get('reason'):
                    description.append(f"  Reason: {change['reason']}")
        
        return description
    
    def _generate_prompt_changes(self, changes: Dict[str, List[CodeChange]]) -> List[str]:
        """Generate the prompt changes section."""
        description = []
        
        if 'prompt_changes' not in changes:
            return description
        
        description.append("\n## Prompt Changes")
        for prompt_change in changes['prompt_changes']:
            description.extend([
                "\n### Before",
                f"```\n{prompt_change['before']}\n```",
                "\n### After",
                f"```\n{prompt_change['after']}\n```"
            ])
            if prompt_change.get('reason'):
                description.append(f"\nReason: {prompt_change['reason']}")
        
        return description
    
    def _generate_additional_summary(self, test_results: TestResults) -> List[str]:
        """Generate the additional summary section."""
        description = []
        
        if test_results.get('additional_summary'):
            description.extend([
                "\n## Additional Summary",
                test_results['additional_summary']
            ])
        
        return description
    
    def _get_change_summary(self, changes: Dict) -> str:
        """
        Get a summary of the changes.
        
        Args:
            changes: Dictionary containing code changes
            
        Returns:
            str: Change summary
        """
        try:
            # Count changes by type
            change_types = {}
            for file_changes in changes.values():
                for change in file_changes:
                    change_type = change.get('type', 'unknown')
                    change_types[change_type] = change_types.get(change_type, 0) + 1
            
            # Generate summary
            summary_parts = []
            for change_type, count in change_types.items():
                summary_parts.append(f"{count} {change_type}")
            
            return ", ".join(summary_parts)
            
        except Exception as e:
            logger.error("Error getting change summary", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return "Code changes"
    
    def _get_test_summary(self, test_results: Dict) -> str:
        """
        Get a summary of the test results.
        
        Args:
            test_results: Dictionary containing test results
            
        Returns:
            str: Test summary
        """
        try:
            if not test_results:
                return ""
            
            # Get overall status
            status = test_results.get('overall_status', 'unknown')
            
            # Get summary if available
            if 'summary' in test_results:
                summary = test_results['summary']
                return f"{status} ({summary['passed_regions']}/{summary['total_regions']} regions passed)"
            
            return status
            
        except Exception as e:
            logger.error("Error getting test summary", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return ""
    
    def _validate_pr_data(self) -> None:
        """
        Validate the PR data.
        
        Raises:
            ValueError: If PR data is invalid
        """
        try:
            # Check required fields
            required_fields = ['title', 'description', 'changes', 'test_results', 'status']
            for field in required_fields:
                if field not in self.pr_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate changes
            if not isinstance(self.pr_data['changes'], dict):
                raise ValueError("Changes must be a dictionary")
            
            # Validate test results
            if not isinstance(self.pr_data['test_results'], dict):
                raise ValueError("Test results must be a dictionary")
            
            # Validate status
            valid_statuses = ['draft', 'ready', 'error']
            if self.pr_data['status'] not in valid_statuses:
                raise ValueError(f"Invalid status: {self.pr_data['status']}")
            
        except Exception as e:
            logger.error("PR data validation failed", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise
    
    def _get_repository_info(self) -> Tuple[str, str]:
        """
        Get repository owner and name from git config.
        
        Returns:
            Tuple[str, str]: Repository owner and name
            
        Raises:
            GitConfigError: If repository information cannot be determined
        """
        try:
            logger.info("Getting git remote origin URL")
            repo_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
            logger.info(f"Git remote URL: {repo_url}")
            
            if not repo_url:
                raise GitConfigError("No remote origin URL found. Please ensure you have a remote origin configured.")
            
            # Handle different URL formats
            if repo_url.endswith('.git'):
                repo_url = repo_url[:-4]
            
            # Handle SSH format (git@github.com:owner/repo.git)
            if repo_url.startswith('git@'):
                parts = repo_url.split(':')
                if len(parts) != 2:
                    raise GitConfigError(f"Invalid SSH URL format: {repo_url}")
                repo_path = parts[1]
                path_parts = repo_path.split('/')
                if len(path_parts) != 2:
                    raise GitConfigError(f"Invalid repository path in SSH URL: {repo_path}")
                repo_owner, repo_name = path_parts
            # Handle HTTPS format (https://github.com/owner/repo.git)
            elif repo_url.startswith('https://'):
                path_parts = repo_url.split('/')
                if len(path_parts) < 5:
                    raise GitConfigError(f"Invalid HTTPS URL format: {repo_url}")
                repo_owner = path_parts[-2]
                repo_name = path_parts[-1]
            else:
                raise GitConfigError(f"Unsupported URL format: {repo_url}")
            
            logger.info(f"Parsed repository info - Owner: {repo_owner}, Name: {repo_name}")
            return repo_owner, repo_name
            
        except subprocess.CalledProcessError as e:
            logger.error("Failed to get git remote URL", extra={
                'return_code': e.returncode,
                'output': e.output,
                'cmd': e.cmd
            })
            raise GitConfigError("Could not determine repository information. Please ensure you're in a git repository with a remote origin.")
        except Exception as e:
            logger.error("Unexpected error parsing repository URL", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise GitConfigError(f"Error parsing repository URL: {str(e)}")
            
    def _get_current_branch(self) -> str:
        """
        Get current git branch.
        
        Returns:
            str: Current branch name
            
        Raises:
            GitConfigError: If branch information cannot be determined
        """
        try:
            logger.info("Getting current git branch")
            current_branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
            
            if not current_branch:
                logger.error("Current branch is empty")
                raise GitConfigError("Could not determine current branch - branch name is empty.")
            
            logger.info(f"Current branch: {current_branch}")
            return current_branch
            
        except subprocess.CalledProcessError as e:
            logger.error("Failed to get current branch", extra={
                'return_code': e.returncode,
                'output': e.output,
                'cmd': e.cmd
            })
            raise GitConfigError("Could not determine current branch. Please ensure you're in a git repository.")
        except Exception as e:
            logger.error("Unexpected error getting current branch", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise GitConfigError(f"Error getting current branch: {str(e)}")
            
    def _check_git_status(self) -> None:
        """
        Check git status to ensure we can create a PR.
        
        Raises:
            GitConfigError: If git status is not suitable for PR creation
        """
        try:
            logger.info("Checking git status")
            
            # Check if we have unpushed commits
            unpushed = subprocess.check_output(
                ["git", "log", "--oneline", f"origin/{self._get_current_branch()}..HEAD"], 
                text=True
            ).strip()
            
            if not unpushed:
                logger.warning("No unpushed commits found - PR may be empty")
            else:
                commit_count = len(unpushed.split('\n'))
                logger.info(f"Found {commit_count} unpushed commit(s)")
            
            # Check if working directory is clean
            status = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
            if status:
                logger.warning("Working directory has uncommitted changes", extra={
                    'uncommitted_files': status.split('\n')
                })
            else:
                logger.info("Working directory is clean")
                
        except subprocess.CalledProcessError as e:
            logger.error("Failed to check git status", extra={
                'return_code': e.returncode,
                'output': e.output,
                'cmd': e.cmd
            })
            # Don't raise here as this is just a warning
        except Exception as e:
            logger.error("Unexpected error checking git status", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            # Don't raise here as this is just a warning

    def _create_github_pr(self) -> PullRequest:
        """
        Create a pull request on GitHub.
        
        Returns:
            PullRequest: Created GitHub pull request
            
        Raises:
            GitHubConfigError: If GitHub repository access fails
            GitConfigError: If git configuration is invalid
        """
        try:
            logger.info("Starting GitHub PR creation process")
            
            # Get repository information
            logger.info("Getting repository information from git config")
            repo_owner, repo_name = self._get_repository_info()
            logger.info(f"Repository info - Owner: {repo_owner}, Name: {repo_name}")
            
            # Get repository
            logger.info(f"Connecting to GitHub repository: {repo_owner}/{repo_name}")
            repo = self.github.get_repo(f"{repo_owner}/{repo_name}")
            logger.info("Successfully connected to repository", extra={
                'repo': f"{repo_owner}/{repo_name}",
                'repo_id': repo.id,
                'repo_full_name': repo.full_name
            })
            
            # Get current branch
            logger.info("Getting current branch")
            current_branch = self._get_current_branch()
            logger.info(f"Current branch: {current_branch}")
            
            # Validate branch exists on remote
            logger.info("Validating branch exists on remote")
            try:
                branch = repo.get_branch(current_branch)
                logger.info(f"Branch validation successful - Branch: {branch.name}, SHA: {branch.commit.sha}")
            except GithubException as e:
                logger.error(f"Branch {current_branch} not found on remote", extra={
                    'error': str(e),
                    'status_code': e.status
                })
                raise GitConfigError(f"Branch {current_branch} not found on remote repository. Please push your changes first.")
            
            # Validate base branch exists
            logger.info(f"Validating base branch: {self.github_config.base_branch}")
            try:
                base_branch = repo.get_branch(self.github_config.base_branch)
                logger.info(f"Base branch validation successful - Branch: {base_branch.name}, SHA: {base_branch.commit.sha}")
            except GithubException as e:
                logger.error(f"Base branch {self.github_config.base_branch} not found", extra={
                    'error': str(e),
                    'status_code': e.status
                })
                raise GitHubConfigError(f"Base branch {self.github_config.base_branch} not found in repository.")
            
            # Check if PR already exists
            logger.info("Checking for existing PRs")
            existing_prs = repo.get_pulls(state='open', head=f"{repo_owner}:{current_branch}")
            existing_pr_list = list(existing_prs)
            if existing_pr_list:
                logger.warning(f"Found {len(existing_pr_list)} existing open PR(s) for this branch", extra={
                    'existing_prs': [pr.html_url for pr in existing_pr_list]
                })
            
            # Log PR creation parameters
            logger.info("PR creation parameters", extra={
                'title': self.pr_data['title'],
                'title_length': len(self.pr_data['title']),
                'body_length': len(self.pr_data['description']),
                'head': current_branch,
                'base': self.github_config.base_branch,
                'repo_full_name': repo.full_name
            })
            
            # Validate title length (GitHub limit is 256 characters)
            if len(self.pr_data['title']) > 256:
                logger.warning(f"PR title is too long ({len(self.pr_data['title'])} chars), truncating to 256")
                self.pr_data['title'] = self.pr_data['title'][:253] + "..."
            
            # Create PR
            logger.info("Creating pull request on GitHub")
            pr = repo.create_pull(
                title=self.pr_data['title'],
                body=self.pr_data['description'],
                head=current_branch,
                base=self.github_config.base_branch
            )
            
            logger.info("PR created successfully", extra={
                'pr_number': pr.number,
                'pr_url': pr.html_url,
                'pr_state': pr.state,
                'pr_merged': pr.merged,
                'pr_mergeable': pr.mergeable
            })
            
            return pr
            
        except GithubException as e:
            logger.error("GitHub API error during PR creation", extra={
                'error': str(e),
                'status_code': e.status,
                'data': getattr(e, 'data', None),
                'headers': getattr(e, 'headers', None)
            })
            
            # Provide more specific error messages based on status code
            if e.status == 422:
                logger.error("422 error typically means validation failed - check if PR already exists or branch issues")
            elif e.status == 404:
                logger.error("404 error - repository or branch not found")
            elif e.status == 403:
                logger.error("403 error - insufficient permissions to create PR")
            elif e.status == 401:
                logger.error("401 error - authentication failed, check GitHub token")
                
            raise GitHubConfigError(f"GitHub API error: {str(e)} (Status: {e.status})")
        except Exception as e:
            logger.error("Unexpected error during PR creation", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': str(e.__traceback__)
            })
            raise 