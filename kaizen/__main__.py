"""
CLI entry point for Kaizen Agent.
"""
import sys
from pathlib import Path
from rich.console import Console
from .cli import cli
from .config import get_config

console = Console()

def main():
    try:
        # Initialize configuration
        config = get_config()
        
        # Run CLI
        cli()
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main() 