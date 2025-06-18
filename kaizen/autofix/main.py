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

if TYPE_CHECKING:
    from kaizen.cli.commands.models import TestConfiguration

from .file.dependency import collect_referenced_files, analyze_failure_dependencies
from .code.fixer import fix_common_syntax_issues, fix_aggressive_syntax_issues, apply_code_changes
from .code.llm_fixer import LLMCodeFixer
from .test.runner import TestRunner
from .pr.manager import PRManager
from .types import FixStatus, CompatibilityIssue

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
    status: FixStatus = FixStatus.PENDING
    changes: Dict[str, Any] = None
    test_results: Optional[Dict[str, Any]] = None
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
            max_retries=config['max_retries'],
            create_pr=config['create_pr'],
            pr_strategy=PRStrategy[config['pr_strategy']],
            base_branch=config['base_branch'],
            auto_fix=config['auto_fix']
        )

class FixResultDict(TypedDict):
    """Type definition for fix result dictionary."""
    fixed_code: str
    changes: Dict[str, Any]
    explanation: Optional[str]
    confidence: Optional[float]



class CodeFormatter:
    """Handles code formatting and syntax fixes."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
                
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            self.logger.info("Gemini model initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise
    
    def _format_with_llm(self, code: str) -> str:
        """Format Python code using LLM.
        
        Args:
            code: The Python code to format
            
        Returns:
            Formatted code string
        """
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
            self.logger.info("Starting code formatting", extra={'code_length': len(code)})
            
            ## LLM FIXER
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
            if is_valid:
                self.logger.debug("Code already valid, applying basic formatting")
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
            
        except Exception as e:
            self.logger.error("Error formatting code", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            # Return original code instead of raising exception
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
        """Remove markdown notations from code."""
        # Remove markdown code block notations
        code = re.sub(r'^```(?:python|py)?\s*\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n?\s*```\s*$', '', code, flags=re.MULTILINE)
        
        # Remove markdown headers at start of lines
        code = re.sub(r'^#+\s+', '', code, flags=re.MULTILINE)
        
        # Remove markdown formatting (be careful not to break code)
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip if line appears to be in a string literal
            if not (line.strip().startswith(('"""', "'''", '"', "'")) or 
                   '"""' in line or "'''" in line):
                # Remove markdown formatting
                line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # Bold
                line = re.sub(r'\*(.*?)\*', r'\1', line)      # Italic
                if not line.strip().startswith('f'):
                    line = re.sub(r'`(.*?)`', r'\1', line)    # Inline code
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
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
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            
            # Basic operator spacing (simple cases only)
            if '=' in line and not any(op in line for op in ['==', '!=', '<=', '>=']):
                parts = line.split('=', 1)
                if len(parts) == 2:
                    line = parts[0].rstrip() + ' = ' + parts[1].lstrip()
            
            formatted_lines.append(line)
        
        # Remove excessive blank lines
        result = []
        prev_empty = False
        for line in formatted_lines:
            if line.strip() == '':
                if not prev_empty:
                    result.append(line)
                prev_empty = True
            else:
                result.append(line)
                prev_empty = False
        
        return '\n'.join(result)

class AutoFix:
    """Handles automatic code fixing."""
    
    # Constants for logging and error messages
    LOG_LEVEL_INFO = "info"
    LOG_LEVEL_ERROR = "error"
    ERROR_MSG_FIX_FAILED = "Failed to fix code"
    
    def __init__(self, config: Union[Dict, 'TestConfiguration']):
        """Initialize AutoFix with configuration.
        
        Args:
            config: Either a dictionary or TestConfiguration object containing configuration
        """
        try:
            if not isinstance(config, dict):
                config = self._convert_test_config_to_dict(config)
            self.config = FixConfig.from_dict(config)
            self.test_runner = TestRunner(config)
            self.pr_manager = PRManager(config)
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
            logger.info("LLM fix result", extra={
                'file_path': current_file_path,
                'status': fix_result.status
            })

            # Format the fixed code
            formatter = CodeFormatter()
            fix_result.fixed_code = formatter.format_code(fix_result.fixed_code)

            # Clean up any markdown or unnecessary text
            fix_result.fixed_code = self._clean_markdown_notations(fix_result.fixed_code)

            if fix_result.status == FixStatus.SUCCESS:
                return self._handle_successful_fix(current_file_path, fix_result)
            return self._handle_failed_fix(current_file_path, file_content)
            
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

    def _handle_successful_fix(self, current_file_path: str, fix_result: FixResultDict) -> FixResult:
        """Handle successful LLM fix.
        
        Args:
            current_file_path: Path to the file being processed
            fix_result: Dictionary containing fix results
            
        Returns:
            FixResult object
            
        Raises:
            ValueError: If the fix result is invalid
            IOError: If there are issues writing to the file
        """
        try:
            fixed_code = self._clean_markdown_notations(fix_result)
            self._apply_code_changes(current_file_path, fixed_code)
            return self._create_success_result(fix_result)
        except (ValueError, IOError) as e:
            logger.error(f"Failed to apply successful fix to {current_file_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'fix_result': fix_result
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

    def _create_success_result(self, fix_result: FixResultDict) -> FixResult:
        """Create a success result object.
        
        Args:
            fix_result: Dictionary containing fix results
            
        Returns:
            FixResult object
        """
        return FixResult(
            status=FixStatus.SUCCESS,
            changes=fix_result['changes'],
            explanation=fix_result.get('explanation'),
            confidence=fix_result.get('confidence')
        )

    def _handle_failed_fix(self, current_file_path: str, file_content: str) -> FixResult:
        """Handle failed LLM fix by attempting common fixes.
        
        Args:
            current_file_path: Path to the file being processed
            file_content: Content of the file
            
        Returns:
            FixResult object
        """
        try:
            fixed_content = self._attempt_common_fixes(current_file_path, file_content)
            if fixed_content != file_content:
                self._apply_code_changes(current_file_path, fixed_content)
                return FixResult(
                    status=FixStatus.SUCCESS,
                    changes={'type': 'common_fixes'}
                )
        except Exception as e:
            logger.error(f"Failed to apply common fixes to {current_file_path}", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            raise
        
        logger.error(f"All fix attempts failed for {current_file_path}")
        return FixResult(
            status=FixStatus.ERROR,
            changes={},
            error=self.ERROR_MSG_FIX_FAILED
        )

    def _attempt_common_fixes(self, current_file_path: str, file_content: str) -> str:
        """Attempt common fixes on the file content.
        
        Args:
            current_file_path: Path to the file being processed
            file_content: Content of the file
            
        Returns:
            Fixed content string
        """
        logger.info("Attempting common fixes", extra={'file_path': current_file_path})
        fixed_content = fix_common_syntax_issues(file_content)
        
        if fixed_content == file_content:
            logger.info("Common fixes had no effect, trying aggressive fixes", 
                       extra={'file_path': current_file_path})
            fixed_content = fix_aggressive_syntax_issues(file_content)
        
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
        if self.config.get('test', {}).get('enabled', False):
            logger.info(f"Running tests for {path}")
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
    
    def fix_code(self, file_path: str, failure_data: List[Dict[str, Any]] = None, 
                config: Optional['TestConfiguration'] = None, files_to_fix: List[str] = None) -> Dict:
        """Fix code in the given files with retry logic.
        
        Args:
            file_path: Main file path (used for test running)
            failure_data: Data about test failures
            user_goal: Optional user goal for fixing
            files_to_fix: List of files to fix
            
        Returns:
            Dict containing fix results
        """
        try:
            logger.info("Starting code fix", extra={
                'file_path': file_path,
                'files_to_fix': files_to_fix,
                'pr_strategy': self.config.pr_strategy.name
            })
            
            if not files_to_fix:
                return {'status': 'error', 'error': 'No files to fix provided'}
            
            # Initialize components
            
            state_manager = CodeStateManager(set(files_to_fix))
            logger.info(f"State manager: {state_manager}")
            attempt_tracker = FixAttemptTracker(self.config.max_retries)
            logger.info(f"Attempt tracker: {attempt_tracker}")
            results = {'status': 'pending', 'changes': {}, 'processed_files': []}
            
            try:
                logger.info(f"Attempt tracker should continue check")
                while attempt_tracker.should_continue():
                    logger.info(f"Attempt tracker should continue")
                    attempt = attempt_tracker.start_attempt()
                    logger.info(f"Starting attempt {attempt.attempt_number} of {self.config.max_retries}")
                    
                    try:
                        # Store original code state
                        attempt.original_code = {
                            path: self._read_file_content(path)
                            for path in files_to_fix
                        }
                        
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
                                    current_file, file_content, context_files, failure_data, config
                                )
                                
                                if fix_result.status == FixStatus.SUCCESS:
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
                        
                        # Run tests
                        test_results = self._run_tests_and_update_status(results, Path(file_path))
                        
                        # Update attempt status
                        status = self._determine_attempt_status(test_results)
                        attempt_tracker.update_attempt(
                            attempt, status, results, test_results
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
                
                # Create PR if needed
                if self.config.create_pr and results['changes']:
                    try:
                        best_attempt = self._get_attempt_for_pr(attempt_tracker)
                        if best_attempt:
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
                    'attempts': [vars(attempt) for attempt in attempt_tracker.attempts],
                    'changes': results['changes'],
                    'processed_files': results['processed_files']
                }
                
            finally:
                state_manager.cleanup()
                
        except Exception as e:
            logger.error("Unexpected error", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {'status': 'error', 'error': str(e)}
    
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