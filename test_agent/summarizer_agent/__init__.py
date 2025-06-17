"""
Summarizer Agent package.
This package contains the SummarizerAgent class and its dependencies.
"""

try:
    from .agent import SummarizerAgent
except ImportError as e:
    print(f"Warning: Could not import SummarizerAgent: {e}")
    raise

__all__ = ['SummarizerAgent'] 