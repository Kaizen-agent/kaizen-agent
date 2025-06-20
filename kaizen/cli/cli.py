"""Main CLI module for Kaizen."""

import click
from rich.console import Console

from .commands.test import test_all

console = Console()

@click.group()
def cli():
    """Kaizen Agent CLI for running and fixing tests."""
    pass

# Register commands
cli.add_command(test_all)

if __name__ == '__main__':
    cli() 