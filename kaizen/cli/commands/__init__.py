"""CLI commands for Kaizen."""

from .test import test_all, run_test
from .fix import fix_tests

__all__ = ['test_all', 'run_test', 'fix_tests'] 