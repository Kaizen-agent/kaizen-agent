from datetime import datetime
import os
import logging
import re
import subprocess
import yaml
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, NamedTuple, Union, TYPE_CHECKING, TypedDict
from dataclasses import dataclass
from enum import Enum, auto
import shutil
import tempfile
import traceback
import google.generativeai as genai

from kaizen.cli.commands.models import TestExecutionHistory
from kaizen.utils.test_utils import get_failed_tests_dict_from_unified

if TYPE_CHECKING:
    from kaizen.cli.commands.models import TestConfiguration

from .file.dependency import collect_referenced_files, analyze_failure_dependencies
from .code.fixer import fix_common_syntax_issues, fix_aggressive_syntax_issues, apply_code_changes
from .code.llm_fixer import LLMCodeFixer
from .test.runner import TestRunner
from .pr.manager import PRManager, TestCase, Attempt, AgentInfo, TestResults
from .types import FixStatus, CompatibilityIssue

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class FixResult:
    """Result of a code fix operation."""
    status: FixStatus
    changes: Dict[str, Any] = None
    explanation: Optional[str] = None
    confidence: Optional[float] = None
    compatibility_issues: List[CompatibilityIssue] = None
    error: Optional[str] = None

@dataclass
class FixAttempt:
    """Data class for tracking fix attempts."""
    attempt_number: int
    status: FixStatus = FixStatus.PENDING
    changes: Dict[str, Any] = None
    test_results: Optional[Dict[str, Any]] = None
    test_execution_result: Optional[Any] = None  # Store unified TestExecutionResult
    error: Optional[str] = None
    original_code: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.changes is None:
            self.changes = {}

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

class LearningManager:
    """Manages learning between fix attempts to improve subsequent fixes."""
    
    def __init__(self):
        self.attempt_history: List[Dict[str, Any]] = []
        self.learned_patterns: Dict[str, List[str]] = {
            'successful_fixes': [],
            'failed_approaches': [],
            'common_errors': [],
            'improvement_insights': []
        }
        self.baseline_failures: Optional[Dict] = None
    
    def set_baseline_failures(self, failure_data: Optional[Dict]) -> None:
        """Set the baseline failure data from the initial test run."""
        self.baseline_failures = failure_data
        logger.debug("Set baseline failures for learning", extra={
            'has_failures': bool(failure_data)
        })
    
    def record_attempt(self, attempt_number: int, changes: Dict[str, Any], 
                      test_results: Dict[str, Any], status: FixStatus) -> None:
        """Record an attempt and its results for learning."""
        attempt_record = {
            'attempt_number': attempt_number,
            'changes': changes,
            'test_results': test_results,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        self.attempt_history.append(attempt_record)
        self._analyze_attempt_for_learning(attempt_record)
        
        logger.debug(f"Recorded attempt {attempt_number} for learning", extra={
            'status': status,
            'has_changes': bool(changes)
        })
    
    def _analyze_attempt_for_learning(self, attempt_record: Dict[str, Any]) -> None:
        """Analyze an attempt to extract learning patterns."""
        changes = attempt_record.get('changes', {})
        test_results = attempt_record.get('test_results', {})
        status = attempt_record.get('status')
        
        # Analyze what worked
        if status == FixStatus.SUCCESS:
            self._extract_successful_patterns(changes, test_results)
        else:
            self._extract_failure_patterns(changes, test_results)
        
        # Analyze improvements even if not fully successful
        if TestResultAnalyzer.has_improvements(test_results):
            self._extract_improvement_insights(changes, test_results)
    
    def _extract_successful_patterns(self, changes: Dict[str, Any], test_results: Dict[str, Any]) -> None:
        """Extract patterns from successful fixes."""
        for file_path, file_changes in changes.items():
            if isinstance(file_changes, dict) and 'fixed_code' in file_changes:
                # Analyze the type of fix that worked
                fix_type = self._classify_fix_type(file_changes)
                if fix_type:
                    self.learned_patterns['successful_fixes'].append(fix_type)
    
    def _extract_failure_patterns(self, changes: Dict[str, Any], test_results: Dict[str, Any]) -> None:
        """Extract patterns from failed attempts."""
        for file_path, file_changes in changes.items():
            if isinstance(file_changes, dict) and 'fixed_code' in file_changes:
                # Analyze what didn't work
                failed_approach = self._classify_failed_approach(file_changes, test_results)
                if failed_approach:
                    self.learned_patterns['failed_approaches'].append(failed_approach)
        
        # Extract common errors from test results
        common_errors = self._extract_common_errors(test_results)
        self.learned_patterns['common_errors'].extend(common_errors)
    
    def _extract_improvement_insights(self, changes: Dict[str, Any], test_results: Dict[str, Any]) -> None:
        """Extract insights from partial improvements."""
        improvement_summary = TestResultAnalyzer.get_improvement_summary(test_results)
        if improvement_summary['improved']:
            insight = f"Attempt improved {improvement_summary['passed']}/{improvement_summary['total']} tests"
            self.learned_patterns['improvement_insights'].append(insight)
    
    def _classify_fix_type(self, file_changes: Dict[str, Any]) -> Optional[str]:
        """Classify the type of fix that was applied."""
        fixed_code = file_changes.get('fixed_code', '')
        if not fixed_code:
            return None
        
        # Simple heuristics to classify fix types
        if 'try:' in fixed_code and 'except' in fixed_code:
            return 'error_handling_added'
        elif 'if ' in fixed_code and 'is None' in fixed_code:
            return 'null_check_added'
        elif 'import ' in fixed_code:
            return 'import_fixed'
        elif 'def ' in fixed_code and '->' in fixed_code:
            return 'type_hints_added'
        elif 'class ' in fixed_code:
            return 'class_structure_fixed'
        
        return 'general_code_fix'
    
    def _classify_failed_approach(self, file_changes: Dict[str, Any], test_results: Dict[str, Any]) -> Optional[str]:
        """Classify what approach failed."""
        # Analyze test results to understand what failed
        failed_tests = []
        for region, result in test_results.items():
            if region == 'overall_status':
                continue
            if isinstance(result, dict):
                test_cases = result.get('test_cases', [])
                for tc in test_cases:
                    if tc.get('status') == 'failed':
                        failed_tests.append(tc.get('name', 'Unknown'))
        
        if failed_tests:
            return f"failed_to_fix_tests: {', '.join(failed_tests[:3])}"  # Limit to first 3
        
        return 'general_fix_failed'
    
    def _extract_common_errors(self, test_results: Dict[str, Any]) -> List[str]:
        """Extract common error patterns from test results."""
        errors = []
        for region, result in test_results.items():
            if region == 'overall_status':
                continue
            if isinstance(result, dict):
                test_cases = result.get('test_cases', [])
                for tc in test_cases:
                    if tc.get('status') == 'failed':
                        error_msg = tc.get('details', '')
                        if error_msg:
                            # Extract error type
                            if 'SyntaxError' in error_msg:
                                errors.append('syntax_error')
                            elif 'ImportError' in error_msg:
                                errors.append('import_error')
                            elif 'AttributeError' in error_msg:
                                errors.append('attribute_error')
                            elif 'TypeError' in error_msg:
                                errors.append('type_error')
                            elif 'NameError' in error_msg:
                                errors.append('name_error')
        
        return list(set(errors))  # Remove duplicates
    
    def get_enhanced_failure_data(self, current_attempt: int) -> Dict[str, Any]:
        """Get enhanced failure data that includes learning from previous attempts."""
        if not self.baseline_failures:
            return {}
        
        enhanced_data = {
            'original_failures': self.baseline_failures,
            'learning_context': {
                'current_attempt': current_attempt,
                'total_attempts': len(self.attempt_history),
                'successful_patterns': self.learned_patterns['successful_fixes'][-3:],  # Last 3
                'failed_approaches': self.learned_patterns['failed_approaches'][-3:],  # Last 3
                'common_errors': list(set(self.learned_patterns['common_errors'])),  # Unique
                'improvement_insights': self.learned_patterns['improvement_insights'][-2:]  # Last 2
            }
        }
        
        # Add specific guidance based on previous attempts
        if current_attempt > 1:
            enhanced_data['previous_attempt_analysis'] = self._analyze_previous_attempts()
        
        logger.debug(f"Generated enhanced failure data for attempt {current_attempt}", extra={
            'has_learning_context': bool(enhanced_data['learning_context']),
            'successful_patterns_count': len(enhanced_data['learning_context']['successful_patterns']),
            'failed_approaches_count': len(enhanced_data['learning_context']['failed_approaches'])
        })
        
        return enhanced_data
    
    def _analyze_previous_attempts(self) -> Dict[str, Any]:
        """Analyze previous attempts to provide specific guidance."""
        if len(self.attempt_history) < 2:
            return {}
        
        analysis = {
            'what_worked': [],
            'what_didnt_work': [],
            'recommendations': []
        }
        
        # Analyze recent attempts
        recent_attempts = self.attempt_history[-3:]  # Last 3 attempts
        
        for attempt in recent_attempts:
            if attempt['status'] == FixStatus.SUCCESS:
                analysis['what_worked'].append(f"Attempt {attempt['attempt_number']}: Complete success")
            elif TestResultAnalyzer.has_improvements(attempt['test_results']):
                improvement = TestResultAnalyzer.get_improvement_summary(attempt['test_results'])
                analysis['what_worked'].append(
                    f"Attempt {attempt['attempt_number']}: Improved {improvement['passed']}/{improvement['total']} tests"
                )
            else:
                analysis['what_didnt_work'].append(f"Attempt {attempt['attempt_number']}: No improvement")
        
        # Generate recommendations based on patterns
        if self.learned_patterns['successful_fixes']:
            analysis['recommendations'].append(
                f"Focus on: {', '.join(set(self.learned_patterns['successful_fixes']))}"
            )
        
        if self.learned_patterns['failed_approaches']:
            analysis['recommendations'].append(
                f"Avoid: {', '.join(set(self.learned_patterns['failed_approaches']))}"
            )
        
        return analysis
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of all learning accumulated."""
        return {
            'total_attempts': len(self.attempt_history),
            'successful_patterns': list(set(self.learned_patterns['successful_fixes'])),
            'failed_approaches': list(set(self.learned_patterns['failed_approaches'])),
            'common_errors': list(set(self.learned_patterns['common_errors'])),
            'improvement_insights': self.learned_patterns['improvement_insights'],
            'learning_progress': self._calculate_learning_progress()
        }
    
    def _calculate_learning_progress(self) -> Dict[str, Any]:
        """Calculate learning progress metrics."""
        if not self.attempt_history:
            return {'progress': 0, 'trend': 'no_data'}
        
        # Calculate success rate trend
        recent_attempts = self.attempt_history[-3:]
        success_count = sum(1 for a in recent_attempts if a['status'] == FixStatus.SUCCESS)
        success_rate = success_count / len(recent_attempts)
        
        # Determine trend
        if len(self.attempt_history) >= 2:
            first_half = self.attempt_history[:len(self.attempt_history)//2]
            second_half = self.attempt_history[len(self.attempt_history)//2:]
            
            first_success_rate = sum(1 for a in first_half if a['status'] == FixStatus.SUCCESS) / len(first_half)
            second_success_rate = sum(1 for a in second_half if a['status'] == FixStatus.SUCCESS) / len(second_half)
            
            if second_success_rate > first_success_rate:
                trend = 'improving'
            elif second_success_rate < first_success_rate:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'recent_success_rate': success_rate,
            'trend': trend,
            'patterns_learned': len(set(self.learned_patterns['successful_fixes']))
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
        logger.info(f"Starting new attempt")
        attempt = FixAttempt(attempt_number=len(self.attempts) + 1)
        logger.info(f"Attempt: {attempt}")
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
    
    def update_attempt_with_unified_result(self, attempt: FixAttempt, status: FixStatus, 
                                          changes: Dict, test_execution_result: Any, error: Optional[str] = None) -> None:
        """Update attempt with unified TestExecutionResult."""
        attempt.status = status
        attempt.changes = changes
        attempt.test_execution_result = test_execution_result
        attempt.test_results = test_execution_result.to_legacy_format() if test_execution_result else None
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
    
    def get_last_attempt(self) -> Optional[FixAttempt]:
        """Get the last attempt."""
        return self.attempts[-1]

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
    preserve_partial_improvements: bool = True  # New option for onboarding scenarios
    
    @classmethod
    def from_dict(cls, config: Dict) -> 'FixConfig':
        """Create FixConfig from dictionary."""
        return cls(
            max_retries=config.get('max_retries', 1),
            create_pr=config.get('create_pr', False),
            pr_strategy=PRStrategy[config.get('pr_strategy', 'ALL_PASSING')],
            base_branch=config.get('base_branch', 'main'),
            auto_fix=config.get('auto_fix', True),
            preserve_partial_improvements=config.get('preserve_partial_improvements', True)
        )

class FixResultDict(TypedDict):
    """Type definition for fix result dictionary."""
    fixed_code: str
    changes: Dict[str, Any]
    explanation: Optional[str]
    confidence: Optional[float]



class CodeFormatter:
    """Handles code formatting and syntax fixes for multiple languages."""
    
    def __init__(self, language: str = 'python'):
        """Initialize CodeFormatter with language support.
        
        Args:
            language: Programming language ('python' or 'typescript')
        """
        self.language = language.lower()
        self.logger = logging.getLogger(__name__)
        
        # Only initialize Gemini for Python formatting (LLM-based)
        if self.language == 'python':
            try:
                api_key = os.environ.get("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY environment variable not set")
                    
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
                self.logger.debug("Gemini model initialized successfully for Python formatting")
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini model: {str(e)}")
                raise
        else:
            self.model = None
            self.logger.debug(f"Initialized formatter for {self.language} (no LLM support)")
    
    def _format_with_llm(self, code: str) -> str:
        """Format code using LLM (Python only).
        
        Args:
            code: The code to format
            
        Returns:
            Formatted code string
        """
        if self.language != 'python':
            self.logger.warning(f"LLM formatting not supported for {self.language}")
            return code
            
        try:
            # Prepare prompt for LLM
            prompt = f"""You are a Python code formatter. Your task is to format the following Python code according to PEP 8 style guidelines.

Key formatting rules to follow:
1. Use 4 spaces for indentation
2. Maximum line length of 88 characters
3. Add proper spacing around operators and after commas
4. Use proper blank lines between functions and classes
5. Follow naming conventions (snake_case for functions/variables, PascalCase for classes)
6. Organize imports (standard library, third-party, local)
7. Add proper docstrings where missing
8. Fix any obvious syntax issues while maintaining functionality

Important:
- Return ONLY the formatted code without any explanations
- Do not add or remove any functionality
- Do not include markdown formatting
- Keep all comments and docstrings
- Preserve all imports and their order

Code to format:
{code}"""
            
            # Call LLM for formatting
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
                    self.logger.warning("Empty response from LLM, using original code")
                    return code
                
                # Check if response has text
                if not hasattr(response, 'text') or not response.text:
                    self.logger.warning("No text content in LLM response, using original code")
                    return code
                    
                formatted_code = response.text.strip()
                
            except Exception as e:
                self.logger.warning(f"LLM formatting failed: {str(e)}")
                return code
            
            # Remove any markdown code blocks if present
            formatted_code = re.sub(r'^```python\s*', '', formatted_code)
            formatted_code = re.sub(r'\s*```$', '', formatted_code)
            
            # Validate the formatted code
            is_valid, _ = self._validate_syntax(formatted_code)
            if not is_valid:
                self.logger.warning("LLM returned invalid Python code, using original")
                return code
                
            return formatted_code
            
        except Exception as e:
            self.logger.warning(f"LLM formatting failed: {str(e)}")
            return code

    def format_code(self, code: str) -> str:
        """Format code using a progressive approach.
        
        Args:
            code: The code to format
            
        Returns:
            Formatted code string
            
        Raises:
            ValueError: If formatting fails
        """
        try:
            self.logger.info("Starting code formatting", extra={
                'code_length': len(code),
                'language': self.language
            })
            
            if self.language == 'python':
                return self._format_python_code(code)
            elif self.language == 'typescript':
                return self._format_typescript_code(code)
            else:
                self.logger.warning(f"Unsupported language: {self.language}, returning original code")
                return code
            
        except Exception as e:
            self.logger.error("Error formatting code", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'language': self.language
            })
            # Return original code instead of raising exception
            return code
    
    def _format_python_code(self, code: str) -> str:
        """Format Python code using progressive approach."""
        # First try LLM-based formatting
        try:
            llm_formatted = self._format_with_llm(code)
            if llm_formatted and llm_formatted != code:
                self.logger.info("LLM formatting successful")
                code = llm_formatted
                self.logger.info(f"LLM formatted code: {code}")
        except Exception as e:
            self.logger.warning(f"LLM formatting failed, falling back to standard formatting: {str(e)}")
        
        # Check if code is already valid
        is_valid, _ = self._validate_syntax(code)
        self.logger.info(f"Code is valid: {is_valid}")
        if is_valid:
            self.logger.info("Code already valid, applying basic formatting")
            return self._basic_formatting(code)
        
        # First try common syntax fixes
        self.logger.info("Starting common syntax fixes")
        formatted_code = self.fix_common_syntax_issues(code)
        self.logger.info(f"Common syntax fixes completed: {formatted_code}")
        
        # Validate after common fixes
        self.logger.info("Validating after common fixes")
        is_valid, error = self._validate_syntax(formatted_code)
        if is_valid:
            self.logger.debug("Common fixes successful")
            return self._basic_formatting(formatted_code)
        self.logger.info(f"Common fixes successful")
        # If common fixes don't work, try aggressive fixes
        if formatted_code == code:
            self.logger.info("Common fixes had no effect, trying aggressive fixes")
            formatted_code = self.fix_aggressive_syntax_issues(code)
        else:
            self.logger.info("Common fixes changed code but still invalid, trying aggressive fixes")
            formatted_code = self.fix_aggressive_syntax_issues(formatted_code)
        
        # Final validation
        is_valid, error = self._validate_syntax(formatted_code)
        if not is_valid:
            self.logger.error("Formatted code has syntax errors", extra={
                'error': str(error),
                'error_type': 'SyntaxError'
            })
            # Return original code instead of raising exception
            self.logger.warning("Returning original code due to failed formatting")
            return code
        
        self.logger.info("Code formatting completed", extra={
            'original_length': len(code),
            'formatted_length': len(formatted_code)
        })
        
        return self._basic_formatting(formatted_code)
    
    def _format_typescript_code(self, code: str) -> str:
        """Format TypeScript code using progressive approach."""
        self.logger.info("Starting TypeScript code formatting")
        
        # Clean markdown first
        code = self._clean_markdown_notations(code)
        
        # Check if code is already valid
        is_valid, _ = self._validate_typescript_syntax(code)
        if is_valid:
            self.logger.info("TypeScript code already valid, applying basic formatting")
            return self._basic_typescript_formatting(code)
        
        # Apply TypeScript-specific fixes
        formatted_code = self._fix_typescript_syntax_issues(code)
        
        # Final validation
        is_valid, error = self._validate_typescript_syntax(formatted_code)
        if not is_valid:
            self.logger.error("Formatted TypeScript code has syntax errors", extra={
                'error': str(error),
                'error_type': 'TypeScriptSyntaxError'
            })
            self.logger.warning("Returning original TypeScript code due to failed formatting")
            return code
        
        self.logger.info("TypeScript code formatting completed", extra={
            'original_length': len(code),
            'formatted_length': len(formatted_code)
        })
        
        return self._basic_typescript_formatting(formatted_code)
    
    def _validate_typescript_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate TypeScript syntax using basic checks for MVP."""
        try:
            # For MVP, just do basic syntax validation without external dependencies
            # Check for balanced brackets, parentheses, and braces
            brackets = {'(': ')', '[': ']', '{': '}', '<': '>'}
            stack = []
            
            for char in code:
                if char in brackets:
                    stack.append(char)
                elif char in brackets.values():
                    if not stack:
                        return False, f"Unmatched closing bracket: {char}"
                    opening = stack.pop()
                    if brackets[opening] != char:
                        return False, f"Mismatched brackets: {opening} and {char}"
            
            if stack:
                return False, f"Unclosed brackets: {stack}"
            
            # Check for basic TypeScript syntax patterns
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped:
                    # Check for unclosed strings
                    if stripped.count('"') % 2 == 1 or stripped.count("'") % 2 == 1:
                        return False, f"Unclosed string on line {i}"
                    
                    # Check for unclosed template literals
                    if stripped.count('`') % 2 == 1:
                        return False, f"Unclosed template literal on line {i}"
            
            # For MVP, if we get here, assume it's valid
            return True, None
            
        except Exception as e:
            return False, f"Error in basic TypeScript validation: {str(e)}"
    
    def _fix_typescript_syntax_issues(self, code: str) -> str:
        """Fix common TypeScript syntax issues."""
        try:
            self.logger.debug("Starting TypeScript syntax fixes", extra={'code_length': len(code)})
            
            original_code = code
            
            # Fix 1: Missing semicolons
            lines = code.split('\n')
            fixed_lines = []
            
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('}') and not stripped.endswith(':') and not stripped.startswith('//') and not stripped.startswith('/*') and not stripped.startswith('*'):
                    # Don't add semicolon if line ends with certain characters
                    if not any(stripped.endswith(char) for char in ['(', '[', '{', ':', ',', ';', '}', ']', ')']):
                        line = line.rstrip() + ';'
                fixed_lines.append(line)
            
            code = '\n'.join(fixed_lines)
            
            # Fix 2: Basic indentation
            code = self._fix_typescript_indentation(code)
            
            # Fix 3: Unclosed strings and template literals
            code = self._fix_typescript_strings(code)
            
            # Fix 4: Missing imports for common modules
            code = self._add_typescript_imports(code)
            
            self.logger.debug("TypeScript syntax fixes completed", extra={
                'fixed_code_length': len(code),
                'changes_made': code != original_code
            })
            
            return code
            
        except Exception as e:
            self.logger.error(f"Error in TypeScript syntax fixes: {str(e)}")
            return code
    
    def _fix_typescript_indentation(self, code: str) -> str:
        """Fix TypeScript indentation issues."""
        lines = code.split('\n')
        fixed_lines = []
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if not stripped:
                fixed_lines.append('')
                continue
            
            # Get previous line for context
            prev_line = lines[i-1].strip() if i > 0 else ''
            
            # Decrease indent for dedent keywords
            if stripped.startswith(('else', 'catch', 'finally')):
                indent_level = max(0, indent_level - 1)
            
            # Apply current indentation
            proper_indent = '    ' * indent_level
            fixed_lines.append(proper_indent + stripped)
            
            # Increase indent after control structures
            if stripped.endswith('{') or any(keyword in stripped for keyword in 
                ['if', 'else', 'for', 'while', 'function', 'class', 'try', 'catch', 'finally']):
                indent_level += 1
        
        return '\n'.join(fixed_lines)
    
    def _fix_typescript_strings(self, code: str) -> str:
        """Fix TypeScript string and template literal issues."""
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Count unescaped quotes and backticks
            double_quotes = line.count('"') - line.count('\\"')
            single_quotes = line.count("'") - line.count("\\'")
            backticks = line.count('`') - line.count('\\`')
            
            # Fix unclosed double quotes
            if double_quotes % 2 == 1 and not line.strip().startswith('//'):
                line = line + '"'
            # Fix unclosed single quotes
            elif single_quotes % 2 == 1 and not line.strip().startswith('//'):
                line = line + "'"
            # Fix unclosed backticks (template literals)
            elif backticks % 2 == 1 and not line.strip().startswith('//'):
                line = line + '`'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _add_typescript_imports(self, code: str) -> str:
        """Add missing imports for commonly used TypeScript modules."""
        import_map = {
            'console.': 'import { console } from "console";',
            'process.': 'import { process } from "process";',
            'Buffer.': 'import { Buffer } from "buffer";',
            'setTimeout': 'import { setTimeout } from "timers";',
            'setInterval': 'import { setInterval } from "timers";',
            'clearTimeout': 'import { clearTimeout } from "timers";',
            'clearInterval': 'import { clearInterval } from "timers";',
        }
        
        needed_imports = []
        for pattern, import_stmt in import_map.items():
            if pattern in code and import_stmt not in code:
                needed_imports.append(import_stmt)
        
        if needed_imports:
            imports = '\n'.join(needed_imports) + '\n\n'
            code = imports + code
        
        return code
    
    def _basic_typescript_formatting(self, code: str) -> str:
        """Apply basic TypeScript formatting rules."""
        # For now, return the code as-is since TypeScript has its own formatter (prettier)
        # In a production environment, you might want to integrate with prettier
        return code

    def fix_common_syntax_issues(self, code: str) -> str:
        """
        Fix common syntax issues in the code with improved logic.
        
        Args:
            code (str): The code to fix
            
        Returns:
            str: The fixed code
        """
        try:
            self.logger.debug("Starting common syntax fixes", extra={'code_length': len(code)})
            
            # Clean markdown first
            code = self._clean_markdown_notations(code)
            
            # Check if already valid
            is_valid, _ = self._validate_syntax(code)
            if is_valid:
                return code
            
            original_code = code
            
            # Fix 1: Missing colons after control structures
            lines = code.split('\n')
            fixed_lines = []
            
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.endswith(':'):
                    # More precise pattern matching for control structures
                    if re.match(r'^(if|elif|else|for|while|def|class|try|except|finally|with)\s+', stripped):
                        # Don't add colon if line already has statement terminators
                        if not any(char in stripped for char in [';', ')', ']', '}']) or stripped.startswith('def ') or stripped.startswith('class '):
                            line = line.rstrip() + ':'
                fixed_lines.append(line)
            
            code = '\n'.join(fixed_lines)
            
            # Fix 2: Print statements (Python 2 to 3)
            code = re.sub(r'\bprint\s+([^(].+)', r'print(\1)', code)
            
            # Fix 3: Basic indentation
            code = self._fix_basic_indentation(code)
            
            # Fix 4: Unclosed strings (basic cases)
            code = self._fix_unclosed_strings(code)
            
            # Fix 5: Missing imports for common modules
            code = self._add_common_imports(code)
            
            self.logger.debug("Common syntax fixes completed", extra={
                'fixed_code_length': len(code),
                'changes_made': code != original_code
            })
            
            return code
            
        except Exception as e:
            self.logger.error(f"Error in common syntax fixes: {str(e)}")
            return code
    
    def fix_aggressive_syntax_issues(self, code: str) -> str:
        """
        Apply more aggressive syntax fixes when common fixes fail.
        
        Args:
            code (str): The code to fix
            
        Returns:
            str: The fixed code
        """
        try:
            self.logger.debug("Starting aggressive syntax fixes", extra={'code_length': len(code)})
            
            # Start with common fixes if not already applied
            code = self.fix_common_syntax_issues(code)
            
            # Check if already valid after common fixes
            is_valid, error = self._validate_syntax(code)
            if is_valid:
                return code
            
            original_code = code
            
            # Aggressive fix 1: Handle specific syntax errors
            if error:
                code = self._fix_specific_syntax_error(code, error)
                is_valid, _ = self._validate_syntax(code)
                if is_valid:
                    return code
            
            # Aggressive fix 2: Remove non-printable characters
            code = ''.join(char for char in code if char.isprintable() or char in ['\n', '\t'])
            
            # Aggressive fix 3: Fix malformed brackets and parentheses
            code = self._fix_brackets_and_parentheses(code)
            
            # Aggressive fix 4: Handle incomplete statements
            code = self._fix_incomplete_statements(code)
            
            # Aggressive fix 5: Advanced indentation fixing
            code = self._fix_advanced_indentation(code)
            
            self.logger.debug("Aggressive syntax fixes completed", extra={
                'fixed_code_length': len(code),
                'changes_made': code != original_code
            })
            
            return code
            
        except Exception as e:
            self.logger.error(f"Error in aggressive syntax fixes: {str(e)}")
            return code
    
    def _validate_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax using AST parsing."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)
    
    def _clean_markdown_notations(self, code: str) -> str:
        """Remove markdown notations from code based on language."""
        if self.language == 'python':
            return self._clean_markdown_notations_python(code)
        elif self.language == 'typescript':
            return self._clean_markdown_notations_typescript(code)
        else:
            # Fallback to generic cleaning for other languages
            return self._clean_markdown_notations_generic(code)
    
    def _clean_markdown_notations_generic(self, code: str) -> str:
        """Remove common markdown notations that work across languages."""
        # Remove markdown code block notations
        code = re.sub(r'^```\w*\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n?\s*```\s*$', '', code, flags=re.MULTILINE)
        
        # Remove markdown headers at start of lines
        code = re.sub(r'^#+\s+', '', code, flags=re.MULTILINE)
        
        # Remove basic markdown formatting (be careful not to break code)
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove markdown formatting only if not in string literals
            if not self._is_in_string_literal(line):
                # Remove markdown formatting
                line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Bold
                line = re.sub(r'\*(.*?)\*', r'\1', line)      # Italic
                line = re.sub(r'`(.*?)`', r'\1', line)        # Inline code
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _clean_markdown_notations_python(self, code: str) -> str:
        """Remove markdown notations from Python code."""
        # Remove Python-specific markdown code block notations
        code = re.sub(r'^```(?:python|py)?\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n?\s*```\s*$', '', code, flags=re.MULTILINE)
        
        # Remove markdown headers at start of lines
        code = re.sub(r'^#+\s+', '', code, flags=re.MULTILINE)
        
        # Remove markdown formatting (be careful not to break Python code)
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip if line appears to be in a Python string literal
            if not self._is_in_python_string_literal(line):
                # Remove markdown formatting
                line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Bold
                line = re.sub(r'\*(.*?)\*', r'\1', line)      # Italic
                # Be extra careful with backticks in Python (could be f-strings)
                if not line.strip().startswith('f'):
                    line = re.sub(r'`(.*?)`', r'\1', line)    # Inline code
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _clean_markdown_notations_typescript(self, code: str) -> str:
        """Remove markdown notations from TypeScript code."""
        # Remove TypeScript-specific markdown code block notations
        code = re.sub(r'^```(?:typescript|ts|tsx)?\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n?\s*```\s*$', '', code, flags=re.MULTILINE)
        
        # Remove markdown headers at start of lines
        code = re.sub(r'^#+\s+', '', code, flags=re.MULTILINE)
        
        # Remove markdown formatting (be careful not to break TypeScript code)
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip if line appears to be in a TypeScript string literal
            if not self._is_in_typescript_string_literal(line):
                # Remove markdown formatting
                line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Bold
                line = re.sub(r'\*(.*?)\*', r'\1', line)      # Italic
                # Be careful with backticks in TypeScript (could be template literals)
                if not self._is_template_literal_context(line):
                    line = re.sub(r'`(.*?)`', r'\1', line)    # Inline code
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _is_in_string_literal(self, line: str) -> bool:
        """Check if a line appears to be in a string literal (generic)."""
        # Simple heuristic: check for unescaped quotes
        double_quotes = line.count('"') - line.count('\\"')
        single_quotes = line.count("'") - line.count("\\'")
        backticks = line.count('`') - line.count('\\`')
        
        # If we have an odd number of any quote type, we might be in a string
        return (double_quotes % 2 == 1 or single_quotes % 2 == 1 or backticks % 2 == 1)
    
    def _is_in_python_string_literal(self, line: str) -> bool:
        """Check if a line appears to be in a Python string literal."""
        stripped = line.strip()
        
        # Check for Python-specific string indicators
        if (stripped.startswith(('"""', "'''", '"', "'")) or 
            '"""' in line or "'''" in line):
            return True
        
        # Check for f-strings and other Python string patterns
        if stripped.startswith('f"') or stripped.startswith("f'"):
            return True
        
        return self._is_in_string_literal(line)
    
    def _is_in_typescript_string_literal(self, line: str) -> bool:
        """Check if a line appears to be in a TypeScript string literal."""
        stripped = line.strip()
        
        # Check for TypeScript-specific string indicators
        if (stripped.startswith(('"', "'", '`')) or 
            '"' in line or "'" in line or '`' in line):
            return True
        
        # Check for template literals
        if self._is_template_literal_context(line):
            return True
        
        return self._is_in_string_literal(line)
    
    def _is_template_literal_context(self, line: str) -> bool:
        """Check if line is in a TypeScript template literal context."""
        # Look for template literal patterns
        if '${' in line and '}' in line:
            return True
        
        # Check if line starts with backtick or contains template literal syntax
        if line.strip().startswith('`') or '`${' in line:
            return True
        
        return False
    
    def _fix_basic_indentation(self, code: str) -> str:
        """Fix basic indentation issues."""
        lines = code.split('\n')
        fixed_lines = []
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if not stripped:
                fixed_lines.append('')
                continue
            
            # Get previous line for context
            prev_line = lines[i-1].strip() if i > 0 else ''
            
            # Decrease indent for dedent keywords
            if stripped.startswith(('else:', 'elif', 'except', 'finally:')):
                indent_level = max(0, indent_level - 1)
            
            # Apply current indentation
            proper_indent = '    ' * indent_level
            fixed_lines.append(proper_indent + stripped)
            
            # Increase indent after control structures
            if stripped.endswith(':') and any(keyword in stripped for keyword in 
                ['if', 'elif', 'else', 'for', 'while', 'def', 'class', 'try', 'except', 'finally', 'with']):
                indent_level += 1
        
        return '\n'.join(fixed_lines)
    
    def _fix_unclosed_strings(self, code: str) -> str:
        """Fix basic unclosed string issues."""
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Count unescaped quotes
            double_quotes = line.count('"') - line.count('\\"')
            single_quotes = line.count("'") - line.count("\\'")
            
            # Fix unclosed double quotes
            if double_quotes % 2 == 1 and not line.strip().startswith('#'):
                line = line + '"'
            # Fix unclosed single quotes
            elif single_quotes % 2 == 1 and not line.strip().startswith('#'):
                line = line + "'"
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _add_common_imports(self, code: str) -> str:
        """Add missing imports for commonly used modules."""
        import_map = {
            'os.': 'import os',
            'sys.': 'import sys',
            'json.': 'import json',
            'datetime.': 'import datetime',
            'random.': 'import random',
            'math.': 'import math',
            're.': 'import re'
        }
        
        needed_imports = []
        for pattern, import_stmt in import_map.items():
            if pattern in code and import_stmt not in code:
                needed_imports.append(import_stmt)
        
        if needed_imports:
            imports = '\n'.join(needed_imports) + '\n\n'
            code = imports + code
        
        return code
    
    def _fix_specific_syntax_error(self, code: str, error_msg: str) -> str:
        """Fix specific syntax errors based on error message."""
        lines = code.split('\n')
        
        # Extract line number
        line_match = re.search(r'line (\d+)', error_msg)
        line_num = int(line_match.group(1)) if line_match else None
        
        if "EOL while scanning string literal" in error_msg and line_num:
            if line_num <= len(lines):
                line = lines[line_num - 1]
                double_quotes = line.count('"') - line.count('\\"')
                single_quotes = line.count("'") - line.count("\\'")
                
                if double_quotes % 2 == 1:
                    lines[line_num - 1] = line + '"'
                elif single_quotes % 2 == 1:
                    lines[line_num - 1] = line + "'"
        
        elif "unexpected EOF while parsing" in error_msg:
            code_stripped = code.strip()
            if code_stripped.endswith('('):
                return code + ')'
            elif code_stripped.endswith('['):
                return code + ']'
            elif code_stripped.endswith('{'):
                return code + '}'
            elif code_stripped.endswith(':'):
                return code + '\n    pass'
        
        return '\n'.join(lines)
    
    def _fix_brackets_and_parentheses(self, code: str) -> str:
        """Fix malformed brackets and parentheses."""
        # Count and balance brackets
        open_parens = code.count('(') - code.count(')')
        open_brackets = code.count('[') - code.count(']')
        open_braces = code.count('{') - code.count('}')
        
        # Add missing closing brackets
        if open_parens > 0:
            code += ')' * open_parens
        if open_brackets > 0:
            code += ']' * open_brackets
        if open_braces > 0:
            code += '}' * open_braces
        
        return code
    
    def _fix_incomplete_statements(self, code: str) -> str:
        """Fix incomplete statements."""
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.endswith(':') and not any(keyword in stripped for keyword in 
                ['if', 'for', 'while', 'def', 'class', 'try', 'except', 'finally', 'with', 'else', 'elif']):
                # Add pass for incomplete blocks
                fixed_lines.append(line)
                fixed_lines.append(line.replace(stripped, '    pass'))
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_advanced_indentation(self, code: str) -> str:
        """Apply advanced indentation fixes."""
        lines = code.split('\n')
        fixed_lines = []
        indent_stack = [0]
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                fixed_lines.append('')
                continue
            
            current_indent = len(indent_stack) - 1
            
            # Handle dedent keywords
            if stripped.startswith(('else:', 'elif', 'except', 'finally:')):
                if len(indent_stack) > 1:
                    indent_stack.pop()
                    current_indent = len(indent_stack) - 1
            
            # Apply indentation
            proper_indent = '    ' * current_indent
            fixed_lines.append(proper_indent + stripped)
            
            # Handle indent increase
            if stripped.endswith(':'):
                indent_stack.append(current_indent + 1)
        
        return '\n'.join(fixed_lines)
    
    def _basic_formatting(self, code: str) -> str:
        """Apply basic formatting rules."""
        return code

class AutoFix:
    """Handles automatic code fixing."""
    
    # Constants for logging and error messages
    LOG_LEVEL_INFO = "info"
    LOG_LEVEL_ERROR = "error"
    ERROR_MSG_FIX_FAILED = "Failed to fix code"
    
    def __init__(self, config: Union[Dict, 'TestConfiguration'], runner_config: Dict[str, Any]):
        """Initialize AutoFix with configuration.
        
        Args:
            config: Either a dictionary or TestConfiguration object containing configuration
        """
        try:
            if not isinstance(config, dict):
                config = self._convert_test_config_to_dict(config)
            self.config = FixConfig.from_dict(config)
            self.test_runner = TestRunner(runner_config)
            self.pr_manager = None  # Initialize lazily when needed
            self.llm_fixer = LLMCodeFixer(config)  # Initialize LLM fixer
            logger.info("AutoFix initialized", extra={
                'config': vars(self.config)
            })
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize AutoFix: {str(e)}")
    
    def _convert_test_config_to_dict(self, config: 'TestConfiguration') -> Dict:
        """Convert TestConfiguration object to dictionary.
        
        Args:
            config: TestConfiguration object to convert
            
        Returns:
            Dictionary containing configuration
        """
        return {
            'name': config.name,
            'file_path': str(config.file_path),
            'max_retries': config.max_retries,
            'create_pr': config.create_pr,
            'pr_strategy': config.pr_strategy,
            'base_branch': config.base_branch,
            'auto_fix': config.auto_fix,
            'tests': []  # Add empty tests list as it's required by TestRunner
        }
    
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
    
    def _process_file_with_llm(self, current_file_path: str, file_content: str, 
                             context_files: Dict[str, str], failure_data: Optional[Dict],
                             config: Optional['TestConfiguration']) -> FixResult:
        """Process a single file using LLM.
        
        Args:
            current_file_path: Path to the file being processed
            file_content: Content of the file
            context_files: Dictionary of related files and their contents
            failure_data: Data about test failures
            config: Test configuration
            
        Returns:
            FixResult object
            
        Raises:
            ConfigurationError: If there's an issue with the configuration
            FileNotFoundError: If the file cannot be found
            PermissionError: If there are permission issues
        """
        try:
            return self._handle_llm_fix(current_file_path, file_content, context_files, failure_data, config)
        except (ConfigurationError, FileNotFoundError, PermissionError) as e:
            logger.error(f"Error processing file {current_file_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            })
            return FixResult(
                status=FixStatus.ERROR,
                changes={},
                error=str(e)
            )

    def _handle_llm_fix(self, current_file_path: str, file_content: str,
                       context_files: Dict[str, str], failure_data: Optional[Dict],
                       config: Optional['TestConfiguration']) -> FixResult:
        """Handle LLM-based code fixing.
        
        Args:
            current_file_path: Path to the file being processed
            file_content: Content of the file
            context_files: Dictionary of related files and their contents
            failure_data: Data about test failures
            config: Test configuration
            
        Returns:
            FixResult object
        """
        try:
            fix_result = self.llm_fixer.fix_code(
                file_content,
                current_file_path,
                failure_data=failure_data,
                config=config,
                context_files=context_files
            )
            logger.debug("LLM fix result", extra={
                'file_path': current_file_path,
                'status': fix_result.status
            })

            # Format the fixed code
            # Get language from config
            language = 'python'  # default
            if config and hasattr(config, 'language') and config.language:
                if hasattr(config.language, 'value'):
                    language = config.language.value
                else:
                    language = str(config.language)
            
            formatter = CodeFormatter(language=language)
            fixed_code = formatter.format_code(fix_result.fixed_code)

            
            if fix_result.status == FixStatus.SUCCESS:
                return self._handle_successful_fix(current_file_path, fixed_code, language)
            else: 
                fixed_code = formatter.format_code(fixed_code)
                return self._handle_successful_fix(current_file_path, fixed_code, language)
            
        except ValueError as e:
            logger.error(f"Error formatting fixed code for {current_file_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return FixResult(
                status=FixStatus.ERROR,
                changes={},
                error=f"Failed to format fixed code: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in LLM fix for {current_file_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return FixResult(
                status=FixStatus.ERROR,
                changes={},
                error=f"Unexpected error: {str(e)}"
            )

    def _handle_successful_fix(self, current_file_path: str, fixed_code: str, language: str = 'python') -> FixResult:
        """Handle successful LLM fix.
        
        Args:
            current_file_path: Path to the file being processed
            fixed_code: The fixed code string
            language: Programming language ('python' or 'typescript')
            
        Returns:
            FixResult object
            
        Raises:
            ValueError: If the fix result is invalid
            IOError: If there are issues writing to the file
        """
        try:
            # Validate syntax based on language
            if language == 'python':
                ast.parse(fixed_code)
                logger.info(f"Successfully parsed fixed Python code with ast")
            elif language == 'typescript':
                # For TypeScript, we'll skip AST validation since we don't have a TypeScript AST parser
                # The syntax validation is already done in the formatter
                logger.info(f"Fixed TypeScript code validated by formatter")
            else:
                logger.warning(f"Unknown language {language}, skipping syntax validation")
            
            self._apply_code_changes(current_file_path, fixed_code)
            return self._create_success_result(fixed_code)
        except (ValueError, IOError) as e:
            logger.error(f"Failed to apply successful fix to {current_file_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'fix_result': fixed_code,
                'language': language
            })
            raise

    def _clean_markdown_notations(self, fix_result: FixResultDict) -> str:
        """Clean markdown notations from fixed code.
        
        Args:
            fix_result: Dictionary containing fix results
            
        Returns:
            Cleaned code string
        """
        logger.info("Cleaning markdown notations", extra={'file_path': fix_result.get('file_path')})
        return self.llm_fixer._clean_markdown_notations(fix_result['fixed_code'])

    def _apply_code_changes(self, current_file_path: str, fixed_code: str) -> None:
        """Apply code changes to file.
        
        Args:
            current_file_path: Path to the file being processed
            fixed_code: The fixed code to apply
            
        Raises:
            IOError: If there are issues writing to the file
        """
        logger.info("Applying code changes", extra={'file_path': current_file_path})
        apply_code_changes(current_file_path, fixed_code)

    def _create_success_result(self, fixed_code: str) -> FixResult:
        """Create a success result object.
        
        Args:
            fixed_code: The fixed code string
            
        Returns:
            FixResult object
        """
        return FixResult(
            status=FixStatus.SUCCESS,
            changes={'fixed_code': fixed_code},
            explanation=None,
            confidence=None
        )

    def _handle_failed_fix(self, current_file_path: str, file_content: str, language: str = 'python') -> FixResult:
        """Handle failed LLM fix by attempting common fixes.
        
        Args:
            current_file_path: Path to the file being processed
            file_content: Content of the file
            language: Programming language ('python' or 'typescript')
            
        Returns:
            FixResult object
        """
        try:
            fixed_content = self._attempt_common_fixes(current_file_path, file_content, language)
            if fixed_content != file_content:
                # Validate syntax based on language
                if language == 'python':
                    ast.parse(fixed_content)
                    logger.info(f"Successfully parsed fixed Python code with ast")
                elif language == 'typescript':
                    logger.info(f"Fixed TypeScript code validated by formatter")
                else:
                    logger.warning(f"Unknown language {language}, skipping syntax validation")
                
                self._apply_code_changes(current_file_path, fixed_content)
                return FixResult(
                    status=FixStatus.SUCCESS,
                    changes={'type': 'common_fixes'}
                )
        except Exception as e:
            logger.error(f"Failed to apply common fixes to {current_file_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'language': language
            })
            raise
        
        logger.error(f"All fix attempts failed for {current_file_path}")
        return FixResult(
            status=FixStatus.ERROR,
            changes={},
            error=self.ERROR_MSG_FIX_FAILED
        )
        
    def _attempt_common_fixes(self, current_file_path: str, file_content: str, language: str = 'python') -> str:
        """Attempt common fixes on the file content.
        
        Args:
            current_file_path: Path to the file being processed
            file_content: Content of the file
            language: Programming language ('python' or 'typescript')
            
        Returns:
            Fixed content string
        """
        logger.info("Attempting common fixes", extra={'file_path': current_file_path, 'language': language})
        
        # Use language-specific formatter for fixes
        formatter = CodeFormatter(language=language)
        fixed_content = formatter.format_code(file_content)
        
        return fixed_content
    
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
        
        logger.info(f"Running tests for {path}")
        test_results = self.test_runner.run_tests(path)
        results['test_results'] = test_results
        total_tests = test_results['overall_status']["summary"]["total_regions"]
        passed_tests = test_results['overall_status']["summary"]["passed_regions"]
        failed_tests = test_results['overall_status']["summary"]["failed_regions"]
        error_tests = test_results['overall_status']["summary"]["error_regions"]
        results['status'] = 'success' if passed_tests == total_tests else 'failed'  
    
        return results
    
    def _create_pr_if_needed(self, results: Dict) -> None:
        """Create PR if changes were made."""
        if results['changes']:
            pr_data = self._get_pr_manager().create_pr(results['changes'], results['test_results'])
            results['pr'] = pr_data
    
    def _get_pr_manager(self) -> PRManager:
        """Get or create PRManager instance.
        
        Returns:
            PRManager instance
            
        Raises:
            ConfigurationError: If PRManager creation fails
        """
        if self.pr_manager is None:
            try:
                self.pr_manager = PRManager(self.config.__dict__)
            except Exception as e:
                raise ConfigurationError(f"Failed to initialize PRManager: {str(e)}")
        return self.pr_manager
    
    def fix_code(self, file_path: str, test_execution_result=None, 
                config: Optional['TestConfiguration'] = None, files_to_fix: List[str] = None) -> Dict:
        """Fix code based on test failures.
        
        Args:
            file_path: Path to the main test file
            test_execution_result: Test execution result from previous run
            config: Test configuration
            files_to_fix: List of files to fix
            
        Returns:
            Dictionary containing fix results
        """
        try:
            logger.debug("AutoFix initialized")
            logger.info("Starting code fix")
            
            # Initialize components
            state_manager = CodeStateManager(set(files_to_fix))
            attempt_tracker = FixAttemptTracker(self.config.max_retries)
            learning_manager = LearningManager()
            test_history = TestExecutionHistory()
            
            logger.debug(f"State manager: {state_manager}")
            logger.debug(f"Attempt tracker: {attempt_tracker}")
            
            # Set baseline failures for learning
            if test_execution_result:
                baseline_failures = self._extract_failure_data_from_unified(test_execution_result)
                learning_manager.set_baseline_failures(baseline_failures)
                test_history.add_baseline_result(test_execution_result)
                logger.debug("Set baseline failures for learning")
            
            logger.debug("Learning manager initialized")
            
            # Check if Git is available
            git_available = self._check_git_availability()
            original_branch = None
            branch_name = None
            
            if git_available:
                try:
                    # Store the original branch
                    original_branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
                    logger.info("Retrieved original branch", extra={'branch': original_branch})
                    
                    # Initialize branch_name with a default value
                    branch_name = f"autofix-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
                    logger.info(f"Created and switched to branch: {branch_name}")
                except Exception as e:
                    logger.warning(f"Git operations failed, continuing without Git: {str(e)}")
                    git_available = False
            else:
                logger.info("Git not available, using file-based operations")
            
            results = {'status': 'pending', 'changes': {}, 'processed_files': []}
            
            # Use provided test_execution_result as baseline, otherwise run baseline test
            if test_execution_result is not None:
                baseline_test_results = test_execution_result
                logger.debug("Using provided test execution result as baseline")
            else:
                logger.info("Running baseline test before any fixes")
                baseline_test_results = self.test_runner.run_tests(Path(file_path))
                test_history.add_baseline_result(baseline_test_results)
                logger.info(f"Baseline test results: {baseline_test_results}")
            
            try:
                logger.debug(f"Attempt tracker should continue check")
                while attempt_tracker.should_continue():
                    logger.debug(f"Attempt tracker should continue")
                    attempt = attempt_tracker.start_attempt()
                    logger.info(f"Starting attempt {attempt.attempt_number} of {self.config.max_retries}")
                    
                    try:
                        # Store original code state
                        attempt.original_code = {
                            path: self._read_file_content(path)
                            for path in files_to_fix
                        }
                        
                        # Get enhanced failure data with learning from previous attempts
                        enhanced_failure_data = learning_manager.get_enhanced_failure_data(attempt.attempt_number)
                        logger.info(f"Using enhanced failure data for attempt {attempt.attempt_number}", extra={
                            'has_learning_context': bool(enhanced_failure_data.get('learning_context')),
                            'has_previous_analysis': bool(enhanced_failure_data.get('previous_attempt_analysis'))
                        })
                        
                        # Process each file individually
                        for current_file in files_to_fix:
                            try:
                                file_content = self._read_file_content(current_file)
                                context_files = {
                                    path: self._read_file_content(path)
                                    for path in files_to_fix
                                    if path != current_file
                                }
                                
                                fix_result = self._process_file_with_llm(
                                    current_file, file_content, context_files, enhanced_failure_data, config
                                )
                                logger.debug(f"fix result: {fix_result}")
                                if fix_result.status == FixStatus.SUCCESS:
                                    logger.debug(f"fix result success")
                                    results['changes'][current_file] = fix_result.changes
                                    results['processed_files'].append({
                                        'file_path': current_file,
                                        'status': 'processed'
                                    })
                                else:
                                    results['processed_files'].append({
                                        'file_path': current_file,
                                        'status': 'error',
                                        'error': fix_result.error
                                    })
                                    
                            except Exception as e:
                                logger.error(f"Error processing file {current_file}: {str(e)}")
                                results['processed_files'].append({
                                    'file_path': current_file,
                                    'status': 'error',
                                    'error': str(e)
                                })
                        
                        # Run tests and get unified result
                        logger.info(f"Running tests after attempt {attempt.attempt_number}")
                        current_test_result = self._run_tests_and_get_result(Path(file_path))
                        
                        # Add to test history
                        test_history.add_fix_attempt_result(current_test_result)
                        
                        # Update attempt status using unified result
                        status = self._determine_attempt_status_from_unified(current_test_result)
                        attempt_tracker.update_attempt_with_unified_result(
                            attempt, status, results, current_test_result
                        )
                        
                        # Show attempt results
                        failed_count = current_test_result.get_failure_count()
                        total_count = current_test_result.summary.total_tests
                        logger.info(f"Attempt {attempt.attempt_number} results: {total_count - failed_count}/{total_count} tests passed")
                        
                        # Record attempt for learning (convert to legacy format for compatibility)
                        learning_manager.record_attempt(
                            attempt.attempt_number, 
                            results['changes'], 
                            current_test_result.to_legacy_format(), 
                            status
                        )
                        logger.info(f"Recorded attempt {attempt.attempt_number} for learning")
                        
                        if status == FixStatus.SUCCESS:
                            logger.info("All tests passed!")
                            test_history.set_final_result(current_test_result)
                            break
                        
                    except Exception as e:
                        logger.error(f"Error in attempt {attempt.attempt_number}: {str(e)}")
                        attempt_tracker.update_attempt(
                            attempt, FixStatus.ERROR, {}, error=str(e)
                        )
                        state_manager.restore_files()
                # Add this except block to fix IndentationError
            except Exception as e:
                logger.error(f"Error during fix attempts: {str(e)}")
                raise
                
            # Add learning summary to results
            learning_summary = learning_manager.get_learning_summary()
            results['learning_summary'] = learning_summary
            results['test_history'] = test_history.to_legacy_format()
            logger.info("Learning summary added to results", extra={
                'total_attempts': learning_summary['total_attempts'],
                'patterns_learned': len(learning_summary['successful_patterns'])
            })
            
            # Create PR if needed and Git is available
            if self.config.create_pr and git_available:
                logger.info(f"start creating pr")
                try:
                    best_attempt = attempt_tracker.get_best_attempt()
                    logger.info(f"best attempt: {best_attempt}")
                    if best_attempt and hasattr(best_attempt, 'test_execution_result'):
                        # Use test history for improvement analysis
                        improvement_summary = test_history.get_improvement_summary()
                        logger.info(f"start creating pr")
                        
                        # Create test results for PR using test history
                        test_results_for_pr = self._create_test_results_for_pr_from_history(test_history)
                        
                        pr_data = self._get_pr_manager().create_pr(
                            best_attempt.changes,
                            test_results_for_pr
                        )
                        return {
                            'status': 'success' if best_attempt.status == FixStatus.SUCCESS else 'improved',
                            'attempts': [vars(attempt) for attempt in attempt_tracker.attempts],
                            'pr': pr_data,
                            'improvement_summary': improvement_summary,
                            'learning_summary': learning_summary,
                            'test_history': test_history.to_legacy_format()
                        }
                except Exception as e:
                    logger.error(f"PR creation failed: {str(e)}")
                    # Check if this is a private repository access issue
                    if "Private repository access issue" in str(e) or "not all refs are readable" in str(e):
                        logger.error("Private repository access issue detected. Changes were made but PR creation failed due to repository permissions.")
                        # Don't revert changes for permission issues - let user handle manually
                        return {
                            'status': 'partial_success',
                            'message': 'Code changes were made successfully, but PR creation failed due to private repository access issues. Please check your GitHub token permissions.',
                            'attempts': [vars(attempt) for attempt in attempt_tracker.attempts],
                            'error': str(e),
                            'changes_made': True,
                            'learning_summary': learning_summary,
                            'test_history': test_history.to_legacy_format()
                        }
                    else:
                        logger.info("PR creation failed for other reasons, reverting changes")
                        if git_available and original_branch:
                            subprocess.run(["git", "checkout", original_branch], check=True)
                        raise PRCreationError(f"Failed to create PR: {str(e)}")
            elif self.config.create_pr and not git_available:
                logger.warning("PR creation requested but Git is not available. Changes were made but no PR was created.")
                return {
                    'status': 'partial_success',
                    'message': 'Code changes were made successfully, but PR creation failed because Git is not available in this environment.',
                    'attempts': [vars(attempt) for attempt in attempt_tracker.attempts],
                    'changes_made': True,
                    'learning_summary': learning_summary,
                    'test_history': test_history.to_legacy_format()
                }
            
            # Check if any improvements were made, even if not all tests pass
            best_attempt = attempt_tracker.get_best_attempt()
            has_any_improvements = False
            
            if best_attempt and best_attempt.test_execution_result:
                # Compare with baseline to see if there were any improvements
                if test_execution_result:
                    improvement_summary = self._get_improvement_summary_from_unified(
                        test_execution_result, best_attempt.test_execution_result
                    )
                    has_any_improvements = improvement_summary['has_improvement']
                else:
                    # If no baseline, check if any tests passed
                    has_any_improvements = best_attempt.test_execution_result.get_failure_count() < best_attempt.test_execution_result.summary.total_tests
            
            # Determine if we should preserve changes based on improvements and configuration
            should_preserve_changes = (
                has_any_improvements or 
                best_attempt.status == FixStatus.SUCCESS or
                (len(results['changes']) > 0 and self.config.preserve_partial_improvements)  # Use config option
            )
            
            logger.info("Change preservation decision", extra={
                'has_any_improvements': has_any_improvements,
                'best_attempt_success': best_attempt.status == FixStatus.SUCCESS if best_attempt else False,
                'changes_made': len(results['changes']) > 0,
                'preserve_partial_improvements': self.config.preserve_partial_improvements,
                'should_preserve_changes': should_preserve_changes
            })
            
            if should_preserve_changes:
                logger.info("Preserving changes due to improvements or successful fixes")
                return {
                    'status': 'success' if best_attempt and best_attempt.status == FixStatus.SUCCESS else 'improved',
                    'message': 'Code changes were applied successfully. Some improvements were made even if not all tests pass.',
                    'attempts': [vars(attempt) for attempt in attempt_tracker.attempts],
                    'changes_made': True,
                    'learning_summary': learning_summary,
                    'test_history': test_history.to_legacy_format(),
                    'best_test_execution_result': best_attempt.test_execution_result if best_attempt else None
                }
            else:
                # Only revert if no improvements were made at all
                logger.info("No improvements were made, reverting changes")
                if git_available and original_branch:
                    subprocess.run(["git", "checkout", original_branch], check=True)
                else:
                    # If Git is not available, restore files using state manager
                    state_manager.restore_files()
                    logger.info("Restored files using state manager (Git not available)")
                
                return {
                    'status': 'failed',
                    'message': 'No improvements were made to the code. All changes have been reverted.',
                    'attempts': [vars(attempt) for attempt in attempt_tracker.attempts],
                    'changes_made': False,
                    'learning_summary': learning_summary,
                    'test_history': test_history.to_legacy_format(),
                    'best_test_execution_result': None
                }
                
        except Exception as e:
            logger.error(f"Error in fix_code: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Try to restore original branch or files
            try:
                if 'git_available' in locals() and git_available and 'original_branch' in locals() and original_branch:
                    subprocess.run(["git", "checkout", original_branch], check=True)
                elif 'state_manager' in locals():
                    state_manager.restore_files()
            except Exception as restore_error:
                logger.error(f"Failed to restore original state: {str(restore_error)}")
            
            return {
                'status': 'error',
                'error': str(e),
                'attempts': [vars(attempt) for attempt in attempt_tracker.attempts] if 'attempt_tracker' in locals() else [],
                'test_history': test_history.to_legacy_format() if 'test_history' in locals() else None,
                'best_test_execution_result': None
            }

    def _run_tests_and_get_result(self, path: Path):
        """Run tests and return unified TestExecutionResult."""
        return self.test_runner.run_tests(path)
    
    def _determine_attempt_status_from_unified(self, test_execution_result) -> FixStatus:
        """Determine attempt status from unified TestExecutionResult."""
        if test_execution_result.is_successful():
            return FixStatus.SUCCESS
        elif test_execution_result.get_failure_count() > 0:
            return FixStatus.FAILED
        else:
            return FixStatus.ERROR
    
    def _get_improvement_summary_from_unified(self, baseline_result, current_result) -> Dict:
        """Get improvement summary comparing two unified TestExecutionResult objects."""
        baseline_failed = len(baseline_result.get_failed_tests())
        current_failed = len(current_result.get_failed_tests())
        
        return {
            'baseline_failed': baseline_failed,
            'current_failed': current_failed,
            'improvement': baseline_failed - current_failed,
            'has_improvement': current_failed < baseline_failed,
            'all_passed': current_result.is_successful()
        }
    
    def _create_test_results_for_pr_from_history(self, test_history: TestExecutionHistory) -> Dict:
        """Create test results for PR using test history."""
        # Create agent info
        agent_info: AgentInfo = {
            'name': 'Kaizen AutoFix Agent',
            'version': '1.0.0',
            'description': 'Automated code fixing agent using LLM-based analysis'
        }
        
        # Get all results from test history
        all_results = test_history.get_all_results()
        
        # Convert each result to the expected Attempt format
        attempts = []
        for i, result in enumerate(all_results):
            # Convert test cases to the expected TestCase format
            test_cases = []
            for tc in result.test_cases:
                # Safely serialize evaluation data
                safe_evaluation = self._safe_serialize_evaluation(tc.evaluation)
                
                test_case: TestCase = {
                    'name': tc.name,
                    'status': tc.status.value,
                    'input': tc.input,
                    'expected_output': tc.expected_output,
                    'actual_output': tc.actual_output,
                    'evaluation': safe_evaluation,
                    'reason': tc.error_message
                }
                test_cases.append(test_case)
            
            # Create attempt
            attempt: Attempt = {
                'status': result.status.value,
                'test_cases': test_cases
            }
            attempts.append(attempt)
        
        # Create TestResults structure
        test_results_for_pr: TestResults = {
            'agent_info': agent_info,
            'attempts': attempts,
            'additional_summary': f"Total attempts: {len(attempts)}"
        }
        
        return test_results_for_pr
    
    def _safe_serialize_evaluation(self, evaluation: Optional[Dict[str, Any]]) -> Optional[str]:
        """Safely serialize evaluation data to prevent JSON serialization issues.
        
        Args:
            evaluation: Evaluation data to serialize
            
        Returns:
            Serialized evaluation as string, or None if serialization fails
        """
        if evaluation is None:
            return None
        
        try:
            # Try to serialize as JSON first
            import json
            return json.dumps(evaluation, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize evaluation as JSON: {str(e)}")
            try:
                # Fallback to string representation
                return str(evaluation)
            except Exception as e2:
                logger.warning(f"Failed to convert evaluation to string: {str(e2)}")
                return "Evaluation data unavailable"

    def _check_git_availability(self) -> bool:
        """Check if Git is available in the current environment.
        
        Returns:
            True if Git is available, False otherwise
        """
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _extract_failure_data_from_unified(self, test_execution_result) -> Dict:
        """Extract failure data from unified test execution result for learning manager compatibility.
        
        Args:
            test_execution_result: Unified TestExecutionResult object
            
        Returns:
            Dictionary containing failure data in legacy format
        """
        return get_failed_tests_dict_from_unified(test_execution_result) 