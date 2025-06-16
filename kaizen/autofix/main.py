import os
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from .prompt.detector import PromptDetector
from .file.dependency import collect_referenced_files, analyze_failure_dependencies
from .code.fixer import fix_common_syntax_issues, fix_aggressive_syntax_issues, apply_code_changes
from .test.runner import TestRunner
from .pr.manager import PRManager

# Configure logging
logger = logging.getLogger(__name__)

class AutoFix:
    """Main class for automatic code fixing."""
    
    def __init__(self, config_path: str):
        """
        Initialize the AutoFix system.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.prompt_detector = PromptDetector(self.config.get('prompt_detection', {}))
        self.test_runner = TestRunner(self.config.get('test', {}))
        self.pr_manager = PRManager(self.config.get('pr', {}))
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dict containing configuration
        """
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {}
    
    def fix_code(self, file_path: str, failure_data: Optional[Dict] = None) -> Dict:
        """
        Fix code in the given file.
        
        Args:
            file_path: Path to the file to fix
            failure_data: Optional dictionary containing failure information
            
        Returns:
            Dict containing fix results
        """
        try:
            # Log fix start
            logger.info("Starting code fix", extra={
                'file_path': file_path
            })
            
            # Initialize results
            results = {
                'status': 'pending',
                'changes': {},
                'test_results': None
            }
            
            # Read file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for prompts
            prompt_result = self.prompt_detector.detect_prompt(content)
            if prompt_result.get('is_prompt'):
                logger.warning("File contains prompts, skipping fix", extra={
                    'file_path': file_path,
                    'prompt_score': prompt_result.get('score', 0)
                })
                results['status'] = 'skipped'
                results['reason'] = 'file_contains_prompts'
                return results
            
            # Collect referenced files
            referenced_files = collect_referenced_files(
                file_path,
                processed_files=set(),
                base_dir=os.path.dirname(file_path),
                failure_data=failure_data
            )
            
            # Analyze dependencies
            if failure_data:
                affected_files = analyze_failure_dependencies(failure_data, referenced_files)
            else:
                affected_files = {file_path}
            
            # Fix each affected file
            for affected_file in affected_files:
                try:
                    # Read file content
                    with open(affected_file, 'r') as f:
                        file_content = f.read()
                    
                    # Apply common fixes
                    fixed_content = fix_common_syntax_issues(file_content)
                    
                    # Apply aggressive fixes if needed
                    if fixed_content == file_content:
                        fixed_content = fix_aggressive_syntax_issues(file_content)
                    
                    # Apply changes if content was modified
                    if fixed_content != file_content:
                        changes = apply_code_changes(affected_file, fixed_content)
                        results['changes'][affected_file] = changes
                    
                except Exception as e:
                    logger.error(f"Error fixing file {affected_file}", extra={
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    results['changes'][affected_file] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Run tests if configured
            if self.config.get('test', {}).get('enabled', False):
                test_results = self.test_runner.run_tests(Path(file_path))
                results['test_results'] = test_results
                
                # Update status based on test results
                if test_results.get('overall_status') == 'passed':
                    results['status'] = 'success'
                else:
                    results['status'] = 'failed'
            else:
                results['status'] = 'success'
            
            # Create PR if changes were made
            if results['changes']:
                pr_data = self.pr_manager.create_pr(results['changes'], results['test_results'])
                results['pr'] = pr_data
            
            # Log fix completion
            logger.info("Code fix completed", extra={
                'file_path': file_path,
                'status': results['status']
            })
            
            return results
            
        except Exception as e:
            logger.error("Code fix failed", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def fix_directory(self, directory_path: str, failure_data: Optional[Dict] = None) -> Dict:
        """
        Fix code in all Python files in the given directory.
        
        Args:
            directory_path: Path to the directory to fix
            failure_data: Optional dictionary containing failure information
            
        Returns:
            Dict containing fix results
        """
        try:
            # Log directory fix start
            logger.info("Starting directory fix", extra={
                'directory_path': directory_path
            })
            
            # Initialize results
            results = {
                'status': 'pending',
                'files': {},
                'test_results': None
            }
            
            # Find Python files
            directory = Path(directory_path)
            python_files = list(directory.rglob('*.py'))
            
            # Fix each file
            for file_path in python_files:
                try:
                    file_results = self.fix_code(str(file_path), failure_data)
                    results['files'][str(file_path)] = file_results
                    
                except Exception as e:
                    logger.error(f"Error fixing file {file_path}", extra={
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    results['files'][str(file_path)] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Run tests if configured
            if self.config.get('test', {}).get('enabled', False):
                test_results = self.test_runner.run_tests(directory)
                results['test_results'] = test_results
                
                # Update status based on test results
                if test_results.get('overall_status') == 'passed':
                    results['status'] = 'success'
                else:
                    results['status'] = 'failed'
            else:
                results['status'] = 'success'
            
            # Create PR if changes were made
            changes = {
                file_path: file_results['changes']
                for file_path, file_results in results['files'].items()
                if file_results.get('changes')
            }
            if changes:
                pr_data = self.pr_manager.create_pr(changes, results['test_results'])
                results['pr'] = pr_data
            
            # Log directory fix completion
            logger.info("Directory fix completed", extra={
                'directory_path': directory_path,
                'status': results['status']
            })
            
            return results
            
        except Exception as e:
            logger.error("Directory fix failed", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {
                'status': 'error',
                'error': str(e)
            } 