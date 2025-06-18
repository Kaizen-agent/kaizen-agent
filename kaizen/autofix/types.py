"""Shared types for the autofix module."""

from enum import Enum, auto
from typing import Dict, Any, Optional, List, Set, Tuple, NamedTuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from kaizen.cli.commands.models import TestConfiguration

class FixStatus(Enum):
    """Status of a code fix operation."""
    SUCCESS = 'success'
    ERROR = 'error'
    COMPATIBILITY_ISSUE = 'compatibility_issue'
    PENDING = 'pending'
    RETRY = 'retry'
    FAILED = 'failed'

class CompatibilityIssue(NamedTuple):
    """Represents a compatibility issue found during code analysis."""
    file_path: str
    issue_type: str
    description: str
    line_number: Optional[int] = None 