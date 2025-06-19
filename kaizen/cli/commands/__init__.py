"""CLI commands for Kaizen."""

from .test import test_all
from .fix import fix_tests

__all__ = ['test_all', 'fix_tests'] 