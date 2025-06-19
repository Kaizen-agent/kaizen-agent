from .main import AutoFix
from .prompt.detector import PromptDetector
from .file.dependency import collect_referenced_files, analyze_failure_dependencies
from .code.fixer import fix_common_syntax_issues, fix_aggressive_syntax_issues, apply_code_changes
from .test.runner import TestRunner
from .pr.manager import PRManager

__version__ = '0.1.0'
__all__ = [
    'AutoFix',
    'PromptDetector',
    'collect_referenced_files',
    'analyze_failure_dependencies',
    'fix_common_syntax_issues',
    'fix_aggressive_syntax_issues',
    'apply_code_changes',
    'TestRunner',
    'PRManager'
] 