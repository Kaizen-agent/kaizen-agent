import os
import logging
import yaml
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, NamedTuple, Union
from dataclasses import dataclass
from enum import Enum, auto
import shutil
import tempfile

from .file.dependency import collect_referenced_files, analyze_failure_dependencies
from .code.fixer import fix_common_syntax_issues, fix_aggressive_syntax_issues, apply_code_changes
from .code.llm_fixer import LLMCodeFixer
from .test.runner import TestRunner
from .pr.manager import PRManager

# Configure logging
logger = logging.getLogger(__name__)

class CompatibilityIssue(NamedTuple):
    """Represents a compatibility issue found during code analysis."""
    file_path: str
    issue_type: str
    description: str
    line_number: Optional[int] = None

class FixStatus(Enum):
    """Status of a code fix operation."""
    SUCCESS = auto()
    ERROR = auto()
    COMPATIBILITY_ISSUE = auto()
    PENDING = auto()
    RETRY = auto()
    FAILED = auto()

@dataclass
class FixResult:
    """Result of a code fix operation."""
    status: FixStatus
    changes: Dict[str, Any]
    explanation: Optional[str] = None
    confidence: Optional[float] = None
    compatibility_issues: List[CompatibilityIssue] = None
    error: Optional[str] = None

@dataclass
class FixAttempt:
    """Data class for tracking fix attempts."""
    attempt_number: int
    status: FixStatus
    changes: Dict[str, Any]
    test_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    original_code: Optional[Dict[str, str]] = None

class CodeAnalyzer:
    """Handles code analysis and compatibility checking."""
    
    @staticmethod
    def parse_ast(content: str, file_path: str) -> Tuple[Optional[ast.AST], Optional[str]]:
        """
        Parse Python code into AST.
        
        Args:
            content: Python code content
            file_path: Path to the file being parsed
            
        Returns:
            Tuple of (AST, error_message)
        """
        try:
            return ast.parse(content), None
        except SyntaxError as e:
            error_msg = f"Syntax error in {file_path}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Error parsing {file_path}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def extract_definitions(ast_tree: ast.AST) -> Dict[str, Set[str]]:
        """
        Extract all definitions and imports from AST.
        
        Args:
            ast_tree: Python AST
            
        Returns:
            Dictionary containing sets of imports and definitions
        """
        imports = set()
        definitions = set()
        
        for node in ast.walk(ast_tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for name in node.names:
                    imports.add(name.name)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                definitions.add(node.name)
        
        return {'imports': imports, 'definitions': definitions}

class CompatibilityChecker:
    """Handles compatibility checking between files."""
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
    
    def check_compatibility(self, file_path: str, content: str, 
                          context_files: Dict[str, str]) -> Tuple[bool, List[CompatibilityIssue]]:
        """
        Check if changes in a file are compatible with its dependencies.
        
        Args:
            file_path: Path to the file being checked
            content: Content of the file
            context_files: Dictionary of related files and their contents
            
        Returns:
            Tuple of (is_compatible, list_of_issues)
        """
        # Parse the modified file
        modified_ast, parse_error = self.analyzer.parse_ast(content, file_path)
        if parse_error:
            return False, [CompatibilityIssue(file_path, 'syntax_error', parse_error)]
        
        # Extract definitions from modified file
        modified_info = self.analyzer.extract_definitions(modified_ast)
        issues = []
        
        # Check each context file
        for context_path, context_content in context_files.items():
            context_ast, parse_error = self.analyzer.parse_ast(context_content, context_path)
            if parse_error:
                issues.append(CompatibilityIssue(context_path, 'syntax_error', parse_error))
                continue
            
            # Check for compatibility issues
            context_issues = self._check_file_compatibility(
                context_path, context_ast, modified_ast, modified_info
            )
            issues.extend(context_issues)
        
        return len(issues) == 0, issues
    
    def _check_file_compatibility(self, file_path: str, context_ast: ast.AST,
                                modified_ast: ast.AST, modified_info: Dict[str, Set[str]]) -> List[CompatibilityIssue]:
        """Check compatibility between a context file and the modified file."""
        issues = []
        
        for node in ast.walk(context_ast):
            if isinstance(node, ast.Name):
                if node.id in modified_info['definitions']:
                    if not self._check_usage_compatibility(node, modified_ast):
                        issues.append(CompatibilityIssue(
                            file_path,
                            'incompatible_usage',
                            f"Incompatible usage of {node.id}",
                            getattr(node, 'lineno', None)
                        ))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for name in node.names:
                    if name.name in modified_info['imports']:
                        if not self._check_import_compatibility(name, modified_ast):
                            issues.append(CompatibilityIssue(
                                file_path,
                                'invalid_import',
                                f"Invalid import of {name.name}",
                                getattr(node, 'lineno', None)
                            ))
        
        return issues
    
    def _check_usage_compatibility(self, usage_node: ast.Name, 
                                 modified_ast: ast.AST) -> bool:
        """Check if a usage of a definition is compatible with its modified version."""
        try:
            for node in ast.walk(modified_ast):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if node.name == usage_node.id:
                        return True
            return False
        except Exception:
            return False
    
    def _check_import_compatibility(self, import_name: ast.alias, 
                                  modified_ast: ast.AST) -> bool:
        """Check if an import is still valid in the modified file."""
        try:
            for node in ast.walk(modified_ast):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if node.name == import_name.name:
                        return True
            return False
        except Exception:
            return False

class CodeStateManager:
    """Manages code state and provides rollback functionality."""
    
    def __init__(self, file_paths: Set[str]):
        self.file_paths = file_paths
        self.backup_dir = tempfile.mkdtemp()
        self._backup_files()
    
    def _backup_files(self) -> None:
        """Create backups of all files."""
        for file_path in self.file_paths:
            backup_path = os.path.join(self.backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
    
    def restore_files(self) -> None:
        """Restore files from backup."""
        for file_path in self.file_paths:
            backup_path = os.path.join(self.backup_dir, os.path.basename(file_path))
            shutil.copy2(backup_path, file_path)
    
    def cleanup(self) -> None:
        """Clean up backup directory."""
        shutil.rmtree(self.backup_dir)

class TestResultAnalyzer:
    """Analyzes test results and determines improvement status."""
    
    @staticmethod
    def count_passed_tests(test_results: Dict) -> int:
        """Count the number of passed tests in the results."""
        if not test_results:
            return 0
            
        passed_tests = 0
        for region, result in test_results.items():
            if region == 'overall_status':
                continue
            if not isinstance(result, dict):
                continue
                
            test_cases = result.get('test_cases', [])
            passed_tests += sum(1 for tc in test_cases if tc.get('status') == 'passed')
        
        return passed_tests
    
    @staticmethod
    def is_successful(test_results: Dict) -> bool:
        """Check if all tests passed."""
        if not test_results:
            return False
            
        overall_status = test_results.get('overall_status', {})
        if isinstance(overall_status, dict):
            return overall_status.get('status') == 'passed'
        return overall_status == 'passed'
    
    @staticmethod
    def has_improvements(test_results: Dict) -> bool:
        """Check if there are any test improvements."""
        return TestResultAnalyzer.count_passed_tests(test_results) > 0
    
    @staticmethod
    def get_improvement_summary(test_results: Dict) -> Dict:
        """Get a summary of test improvements."""
        if not test_results:
            return {'total': 0, 'passed': 0, 'improved': False}
            
        total_tests = 0
        passed_tests = 0
        
        for region, result in test_results.items():
            if region == 'overall_status':
                continue
            if not isinstance(result, dict):
                continue
                
            test_cases = result.get('test_cases', [])
            total_tests += len(test_cases)
            passed_tests += sum(1 for tc in test_cases if tc.get('status') == 'passed')
        
        return {
            'total': total_tests,
            'passed': passed_tests,
            'improved': passed_tests > 0
        }

class FixAttemptTracker:
    """Tracks fix attempts and their results."""
    
    def __init__(self, max_retries: int):
        self.max_retries = max_retries
        self.attempts: List[FixAttempt] = []
        self.current_attempt: Optional[FixAttempt] = None
    
    def should_continue(self) -> bool:
        """Check if more attempts should be made."""
        return len(self.attempts) < self.max_retries
    
    def start_attempt(self) -> FixAttempt:
        """Start a new fix attempt."""
        attempt = FixAttempt(attempt_number=len(self.attempts) + 1)
        self.current_attempt = attempt
        self.attempts.append(attempt)
        return attempt
    
    def update_attempt(self, attempt: FixAttempt, status: FixStatus, 
                      changes: Dict, test_results: Dict, error: Optional[str] = None) -> None:
        """Update attempt with results."""
        attempt.status = status
        attempt.changes = changes
        attempt.test_results = test_results
        attempt.error = error
    
    def get_successful_attempt(self) -> Optional[FixAttempt]:
        """Get the first successful attempt if any."""
        return next((attempt for attempt in self.attempts if attempt.status == FixStatus.SUCCESS), None)
    
    def get_best_attempt(self) -> Optional[FixAttempt]:
        """Get the best attempt based on test results."""
        if not self.attempts:
            return None
            
        # First try to find a successful attempt
        successful = self.get_successful_attempt()
        if successful:
            return successful
            
        # If no successful attempt, find any attempt with improvements
        for attempt in self.attempts:
            if TestResultAnalyzer.has_improvements(attempt.test_results):
                return attempt
        
        return None

class PRStrategy(Enum):
    """Strategy for when to create pull requests."""
    ALL_PASSING = auto()  # Only create PR when all tests pass
    ANY_IMPROVEMENT = auto()  # Create PR when any test improves
    NONE = auto()  # Never create PR

class AutoFixError(Exception):
    """Base exception for AutoFix errors."""
    pass

class ConfigurationError(AutoFixError):
    """Error in configuration."""
    pass

class TestExecutionError(AutoFixError):
    """Error during test execution."""
    pass

class PRCreationError(AutoFixError):
    """Error during PR creation."""
    pass

@dataclass
class FixConfig:
    """Configuration for code fixing."""
    max_retries: int = 1
    create_pr: bool = False
    pr_strategy: PRStrategy = PRStrategy.ALL_PASSING
    base_branch: str = 'main'
    auto_fix: bool = True
    
    @classmethod
    def from_dict(cls, config: Dict) -> 'FixConfig':
        """Create FixConfig from dictionary."""
        return cls(
            max_retries=config.get('max_retries', 1),
            create_pr=config.get('create_pr', False),
            pr_strategy=PRStrategy[config.get('pr_strategy', 'ALL_PASSING')],
            base_branch=config.get('base_branch', 'main'),
            auto_fix=config.get('auto_fix', True)
        )

class AutoFix:
    """Handles automatic code fixing."""
    
    def __init__(self, config: Dict):
        """Initialize AutoFix with configuration."""
        try:
            self.config = FixConfig.from_dict(config)
            self.test_runner = TestRunner(config)
            self.pr_manager = PRManager(config)
            logger.info("AutoFix initialized", extra={
                'config': vars(self.config)
            })
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize AutoFix: {str(e)}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {}
    
    def _read_file_content(self, file_path: str) -> str:
        """Read file content with error handling."""
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
    
    def _get_context_files(self, target_file: str, all_files: Set[str]) -> Dict[str, str]:
        """Get content of context files."""
        context_files = {}
        for path in all_files:
            if path != target_file:
                try:
                    content = self._read_file_content(path)
                    context_files[path] = content
                except Exception as e:
                    logger.warning(f"Could not read context file {path}: {str(e)}")
        return context_files
    
    def _create_initial_results(self) -> Dict:
        """Create initial results structure."""
        return {
            'status': 'pending',
            'changes': {},
            'test_results': None,
            'processed_files': [],
            'suggested_files': set()
        }
    
    def _process_file_with_llm(self, current_file: str, file_content: str, 
                             context_files: Dict[str, str], failure_data: Optional[Dict],
                             user_goal: Optional[str]) -> FixResult:
        """
        Process a single file using LLM.
        
        Returns:
            FixResult object
        """
        try:
            fix_result = self.llm_fixer.fix_code(
                file_content,
                current_file,
                failure_data=failure_data,
                user_goal=user_goal,
                context_files=context_files
            )
            
            if fix_result['status'] == 'success':
                fixed_code = self.llm_fixer._clean_markdown_notations(fix_result['fixed_code'])
                
                # Check compatibility
                is_compatible, compatibility_issues = self.compatibility_checker.check_compatibility(
                    current_file, fixed_code, context_files
                )
                
                if is_compatible:
                    apply_code_changes(current_file, fixed_code)
                    return FixResult(
                        status=FixStatus.SUCCESS,
                        changes=fix_result['changes'],
                        explanation=fix_result['explanation'],
                        confidence=fix_result['confidence']
                    )
                else:
                    # Try to fix compatibility issues
                    logger.warning(f"Compatibility issues found in {current_file}", extra={
                        'issues': compatibility_issues
                    })
                    
                    compatibility_fix = self.llm_fixer.fix_compatibility_issues(
                        fixed_code,
                        current_file,
                        compatibility_issues,
                        context_files
                    )
                    
                    if compatibility_fix['status'] == 'success':
                        fixed_code = compatibility_fix['fixed_code']
                        apply_code_changes(current_file, fixed_code)
                        return FixResult(
                            status=FixStatus.SUCCESS,
                            changes=compatibility_fix['changes'],
                            explanation=compatibility_fix['explanation'],
                            confidence=compatibility_fix['confidence'],
                            compatibility_issues=compatibility_issues
                        )
                    else:
                        return FixResult(
                            status=FixStatus.COMPATIBILITY_ISSUE,
                            changes={},
                            error='Failed to fix compatibility issues',
                            compatibility_issues=compatibility_issues
                        )
            else:
                # Try common fixes
                fixed_content = fix_common_syntax_issues(file_content)
                if fixed_content == file_content:
                    fixed_content = fix_aggressive_syntax_issues(file_content)
                
                if fixed_content != file_content:
                    is_compatible, compatibility_issues = self.compatibility_checker.check_compatibility(
                        current_file, fixed_content, context_files
                    )
                    
                    if is_compatible:
                        apply_code_changes(current_file, fixed_content)
                        return FixResult(
                            status=FixStatus.SUCCESS,
                            changes={'type': 'common_fixes'}
                        )
                    else:
                        return FixResult(
                            status=FixStatus.COMPATIBILITY_ISSUE,
                            changes={},
                            error='Common fixes caused compatibility issues',
                            compatibility_issues=compatibility_issues
                        )
                
                return FixResult(
                    status=FixStatus.ERROR,
                    changes={},
                    error='Failed to fix code'
                )
                
        except Exception as e:
            logger.error(f"Error processing file {current_file}", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return FixResult(
                status=FixStatus.ERROR,
                changes={},
                error=str(e)
            )
    
    def _handle_file_processing_error(self, current_file: str, error: Exception) -> Dict:
        """Handle errors during file processing."""
        logger.error(f"Error fixing file {current_file}", extra={
            'error': str(error),
            'error_type': type(error).__name__
        })
        return {
            'status': 'error',
            'error': str(error)
        }
    
    def _update_results_with_file_processing(self, results: Dict, current_file: str, 
                                           changes: Dict, is_error: bool = False) -> None:
        """Update results with file processing information."""
        results['changes'][current_file] = changes
        results['processed_files'].append({
            'file_path': current_file,
            'status': 'error' if is_error else 'processed',
            **({'error': changes['error']} if is_error else {})
        })
    
    def _run_tests_and_update_status(self, results: Dict, path: Path) -> None:
        """Run tests and update results status."""
        if self.config.get('test', {}).get('enabled', False):
            test_results = self.test_runner.run_tests(path)
            results['test_results'] = test_results
            results['status'] = 'success' if test_results.get('overall_status') == 'passed' else 'failed'
        else:
            results['status'] = 'success'
    
    def _create_pr_if_needed(self, results: Dict) -> None:
        """Create PR if changes were made."""
        if results['changes']:
            pr_data = self.pr_manager.create_pr(results['changes'], results['test_results'])
            results['pr'] = pr_data
    
    def fix_code(self, file_path: str, failure_data: Optional[Dict] = None, 
                user_goal: Optional[str] = None) -> Dict:
        """Fix code in the given file with retry logic."""
        try:
            logger.info("Starting code fix", extra={
                'file_path': file_path,
                'pr_strategy': self.config.pr_strategy.name
            })
            
            # Initialize components
            affected_files = self._get_affected_files(file_path, failure_data)
            state_manager = CodeStateManager(affected_files)
            attempt_tracker = FixAttemptTracker(self.config.max_retries)
            
            try:
                while attempt_tracker.should_continue():
                    attempt = attempt_tracker.start_attempt()
                    logger.info(f"Starting attempt {attempt.attempt_number} of {self.config.max_retries}")
                    
                    try:
                        # Store original code state
                        attempt.original_code = {
                            path: self._read_file_content(path)
                            for path in affected_files
                        }
                        
                        # Apply fixes
                        fix_result = self._apply_fixes(
                            affected_files, failure_data, user_goal
                        )
                        
                        # Run tests
                        test_results = self._run_tests_and_update_status(
                            fix_result, Path(file_path)
                        )
                        
                        # Update attempt status
                        status = self._determine_attempt_status(test_results)
                        attempt_tracker.update_attempt(
                            attempt, status, fix_result, test_results
                        )
                        
                        if status == FixStatus.SUCCESS:
                            logger.info("All tests passed!")
                            break
                        
                    except Exception as e:
                        logger.error(f"Error in attempt {attempt.attempt_number}: {str(e)}")
                        attempt_tracker.update_attempt(
                            attempt, FixStatus.ERROR, {}, error=str(e)
                        )
                        state_manager.restore_files()
                
                # Create PR based on strategy
                if self.config.create_pr:
                    try:
                        best_attempt = self._get_attempt_for_pr(attempt_tracker)
                        if best_attempt and best_attempt.changes:
                            # Add improvement summary to test results
                            improvement_summary = TestResultAnalyzer.get_improvement_summary(best_attempt.test_results)
                            best_attempt.test_results['improvement_summary'] = improvement_summary
                            
                            pr_data = self.pr_manager.create_pr(
                                best_attempt.changes,
                                best_attempt.test_results
                            )
                            return {
                                'status': 'success' if best_attempt.status == FixStatus.SUCCESS else 'improved',
                                'attempts': [vars(attempt) for attempt in attempt_tracker.attempts],
                                'pr': pr_data,
                                'improvement_summary': improvement_summary
                            }
                    except Exception as e:
                        raise PRCreationError(f"Failed to create PR: {str(e)}")
                
                return {
                    'status': 'success' if attempt_tracker.get_successful_attempt() else 'failed',
                    'attempts': [vars(attempt) for attempt in attempt_tracker.attempts]
                }
                
            finally:
                state_manager.cleanup()
                
        except AutoFixError as e:
            logger.error("AutoFix error", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {'status': 'error', 'error': str(e)}
        except Exception as e:
            logger.error("Unexpected error", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {'status': 'error', 'error': str(e)}
    
    def _get_affected_files(self, file_path: str, failure_data: Optional[Dict]) -> Set[str]:
        """Get set of files affected by the fix."""
        referenced_files = collect_referenced_files(
            file_path,
            processed_files=set(),
            base_dir=os.path.dirname(file_path),
            failure_data=failure_data
        )
        return (analyze_failure_dependencies(failure_data, referenced_files) 
                if failure_data else {file_path})
    
    def _apply_fixes(self, affected_files: Set[str], failure_data: Optional[Dict],
                    user_goal: Optional[str]) -> Dict[str, Any]:
        """Apply fixes to affected files."""
        results = self._create_initial_results()
        
        for current_file in affected_files:
            try:
                file_content = self._read_file_content(current_file)
                context_files = self._get_context_files(current_file, affected_files)
                
                fix_result = self._process_file_with_llm(
                    current_file, file_content, context_files, failure_data, user_goal
                )
                
                self._update_results_with_file_processing(
                    results, current_file, fix_result.changes
                )
                
            except Exception as e:
                error_changes = self._handle_file_processing_error(current_file, e)
                self._update_results_with_file_processing(
                    results, current_file, error_changes, is_error=True
                )
        
        return results
    
    def _determine_attempt_status(self, test_results: Dict[str, Any]) -> FixStatus:
        """Determine the status of a fix attempt based on test results."""
        if not test_results:
            return FixStatus.ERROR
            
        overall_status = test_results.get('overall_status', {})
        status = overall_status.get('status', 'unknown')
        
        if status == 'passed':
            return FixStatus.SUCCESS
        elif status == 'failed':
            return FixStatus.FAILED
        else:
            return FixStatus.ERROR
    
    def _get_attempt_for_pr(self, attempt_tracker: FixAttemptTracker) -> Optional[FixAttempt]:
        """Get the appropriate attempt for PR creation based on strategy."""
        if self.config.pr_strategy == PRStrategy.NONE:
            return None
            
        if self.config.pr_strategy == PRStrategy.ALL_PASSING:
            return attempt_tracker.get_successful_attempt()
            
        # For ANY_IMPROVEMENT, return first attempt with any improvement
        for attempt in attempt_tracker.attempts:
            if TestResultAnalyzer.has_improvements(attempt.test_results):
                return attempt
                
        return None
    
    def fix_directory(self, directory_path: str, failure_data: Optional[Dict] = None) -> Dict:
        """Fix code in all Python files in the given directory."""
        try:
            logger.info("Starting directory fix", extra={'directory_path': directory_path})
            
            results = {
                'status': 'pending',
                'files': {},
                'test_results': None
            }
            
            directory = Path(directory_path)
            python_files = list(directory.rglob('*.py'))
            
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
            
            self._run_tests_and_update_status(results, directory)
            
            changes = {
                file_path: file_results['changes']
                for file_path, file_results in results['files'].items()
                if file_results.get('changes')
            }
            if changes:
                pr_data = self.pr_manager.create_pr(changes, results['test_results'])
                results['pr'] = pr_data
            
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
            return {'status': 'error', 'error': str(e)} 