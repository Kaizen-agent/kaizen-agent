"""File dependency analysis and management utilities."""

from .dependency import (
    analyze_failure_dependencies,
    collect_referenced_files,
)

__all__ = [
    "analyze_failure_dependencies",
    "collect_referenced_files",
] 