"""TypeScript cache management utilities.

This module provides utilities for managing TypeScript compilation cache,
including clearing cache and displaying cache statistics.
"""

from pathlib import Path
from typing import Dict, Any
from rich.console import Console


class TypeScriptCacheManager:
    """Manages TypeScript compilation cache operations."""
    
    def __init__(self, console: Console):
        """Initialize the TypeScript cache manager.
        
        Args:
            console: Rich console for output
        """
        self.console = console
    
    def clear_cache(self) -> None:
        """Clear the TypeScript compilation cache."""
        from kaizen.autofix.test.code_region import CodeRegionExecutor
        
        temp_executor = CodeRegionExecutor(Path.cwd())
        temp_executor.clear_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get TypeScript cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        from kaizen.autofix.test.code_region import CodeRegionExecutor
        
        temp_executor = CodeRegionExecutor(Path.cwd())
        return temp_executor.get_cache_stats()
    
    def display_cache_stats(self, stats: Dict[str, Any]) -> None:
        """Display TypeScript cache statistics in a formatted way.
        
        Args:
            stats: Cache statistics dictionary
        """
        self.console.print("\n[bold]TypeScript Cache Statistics:[/bold]")
        self.console.print(f"  • Execution cache entries: {stats['execution_cache_size']}")
        self.console.print(f"  • Compiled modules: {stats['compiled_modules_size']}")
        self.console.print(f"  • Cache directory: {stats['ts_cache_directory']}")
        self.console.print("")
    
    def handle_cache_operations(self, clear_cache: bool, show_stats: bool) -> None:
        """Handle TypeScript cache operations based on flags.
        
        Args:
            clear_cache: Whether to clear the cache
            show_stats: Whether to show cache statistics
        """
        if not (clear_cache or show_stats):
            return
        
        if clear_cache:
            self.console.print("Clearing TypeScript compilation cache...")
            self.clear_cache()
            self.console.print("✓ TypeScript cache cleared")
        
        if show_stats:
            stats = self.get_cache_stats()
            self.display_cache_stats(stats) 