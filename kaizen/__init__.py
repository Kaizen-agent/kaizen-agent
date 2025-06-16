"""Kaizen - AI-powered test automation and fixing."""

from .autofix.main import AutoFix
from .autofix.prompt.detector import PromptDetector
from .autofix.file.dependency import collect_referenced_files, analyze_failure_dependencies
from .autofix.code.fixer import fix_common_syntax_issues, fix_aggressive_syntax_issues, apply_code_changes
from .autofix.test.runner import TestRunner
from .autofix.pr.manager import PRManager
from .cli import cli

__version__ = "0.1.0"
__all__ = [
    'AutoFix',
    'PromptDetector',
    'collect_referenced_files',
    'analyze_failure_dependencies',
    'fix_common_syntax_issues',
    'fix_aggressive_syntax_issues',
    'apply_code_changes',
    'TestRunner',
    'PRManager',
    'cli'
] 