import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

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
    
    def _generate_pr_description(self, changes: Dict, test_results: Dict) -> str:
        """
        Generate a description for the pull request.
        
        Args:
            changes: Dictionary containing code changes
            test_results: Dictionary containing test results
            
        Returns:
            str: PR description
        """
        try:
            description = []
            
            # Add change details
            description.append("## Changes")
            for file_path, file_changes in changes.items():
                description.append(f"\n### {file_path}")
                for change in file_changes:
                    description.append(f"- {change['description']}")
            
            # Add test results
            if test_results:
                description.append("\n## Test Results")
                description.append(f"\nOverall Status: {test_results['overall_status']}")
                
                if 'summary' in test_results:
                    summary = test_results['summary']
                    description.append(f"\n- Total Regions: {summary['total_regions']}")
                    description.append(f"- Passed Regions: {summary['passed_regions']}")
                    description.append(f"- Failed Regions: {summary['failed_regions']}")
                    description.append(f"- Error Regions: {summary['error_regions']}")
                
                # Add region details
                for region_name, region_data in test_results.items():
                    if region_name not in ('overall_status', '_status', 'summary'):
                        description.append(f"\n### {region_name}")
                        description.append(f"Status: {region_data['status']}")
                        
                        if 'summary' in region_data:
                            region_summary = region_data['summary']
                            description.append(f"\n- Total Tests: {region_summary['total']}")
                            description.append(f"- Passed Tests: {region_summary['passed']}")
                            description.append(f"- Failed Tests: {region_summary['failed']}")
                            description.append(f"- Error Tests: {region_summary['error']}")
            
            return "\n".join(description)
            
        except Exception as e:
            logger.error("Error generating PR description", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return "Code changes and test results"
    
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