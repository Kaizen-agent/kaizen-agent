import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, TypedDict, Union
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

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

class PRManager:
    """A class for managing pull requests."""
    
    def __init__(self, config: Dict):
        """
        Initialize the PR manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.pr_data = {}
        
    def create_pr(self, changes: Dict, test_results: Dict) -> Dict:
        """
        Create a pull request with the given changes and test results.
        
        Args:
            changes: Dictionary containing code changes
            test_results: Dictionary containing test results
            
        Returns:
            Dict containing PR information
        """
        try:
            # Log PR creation start
            logger.info("Starting PR creation", extra={
                'changes_count': len(changes)
            })
            
            # Initialize PR data
            self.pr_data = {
                'title': self._generate_pr_title(changes, test_results),
                'description': self._generate_pr_description(changes, test_results),
                'changes': changes,
                'test_results': test_results,
                'status': 'draft',
                'created_at': datetime.now().isoformat()
            }
            
            # Validate PR data
            self._validate_pr_data()
            
            # Create PR files
            self._create_pr_files()
            
            # Update PR status
            self.pr_data['status'] = 'ready'
            
            # Log PR creation completion
            logger.info("PR creation completed", extra={
                'pr_title': self.pr_data['title']
            })
            
            return self.pr_data
            
        except Exception as e:
            logger.error("PR creation failed", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {
                'status': 'error',
                'error': str(e)
            }
    
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
            # Get change summary
            change_summary = self._get_change_summary(changes)
            
            # Get test summary
            test_summary = self._get_test_summary(test_results)
            
            # Generate title
            title = f"Fix: {change_summary}"
            
            # Add test status if available
            if test_summary:
                title += f" ({test_summary})"
            
            return title
            
        except Exception as e:
            logger.error("Error generating PR title", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return "Fix: Code changes"
    
    def _generate_pr_description(self, changes: Dict[str, List[CodeChange]], test_results: TestResults) -> str:
        """
        Generate a description for the pull request.
        
        Args:
            changes: Dictionary containing code changes, keyed by file path
            test_results: Dictionary containing test results and agent information
            
        Returns:
            str: Formatted PR description
            
        Raises:
            ValueError: If required data is missing or malformed
        """
        try:
            description = []
            
            # Add each section
            description.extend(self._generate_agent_summary(test_results))
            description.extend(self._generate_test_results_summary(test_results))
            description.extend(self._generate_detailed_results(test_results))
            description.extend(self._generate_code_changes(changes))
            description.extend(self._generate_prompt_changes(changes))
            description.extend(self._generate_additional_summary(test_results))
            
            return "\n".join(description)
            
        except Exception as e:
            logger.error("Error generating PR description", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return "Code changes and test results"
    
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
    
    def _create_pr_files(self) -> None:
        """
        Create files for the pull request.
        """
        try:
            # Create PR directory
            pr_dir = Path(self.config.get('pr_dir', 'prs'))
            pr_dir.mkdir(parents=True, exist_ok=True)
            
            # Create PR file
            pr_file = pr_dir / f"pr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(pr_file, 'w') as f:
                json.dump(self.pr_data, f, indent=2)
            
            # Create changes directory
            changes_dir = pr_dir / 'changes'
            changes_dir.mkdir(parents=True, exist_ok=True)
            
            # Create change files
            for file_path, file_changes in self.pr_data['changes'].items():
                change_file = changes_dir / f"{Path(file_path).name}.json"
                with open(change_file, 'w') as f:
                    json.dump(file_changes, f, indent=2)
            
            # Create test results file
            test_file = pr_dir / 'test_results.json'
            with open(test_file, 'w') as f:
                json.dump(self.pr_data['test_results'], f, indent=2)
            
        except Exception as e:
            logger.error("Error creating PR files", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise 