"""
CLI entry point for Kaizen Agent.
"""
import sys
from pathlib import Path
from rich.console import Console
from .cli import cli

console = Console()

def main():
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main() 