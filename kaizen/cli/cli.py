"""Main CLI module for Kaizen."""

import click
from rich.console import Console

from .commands.test import test_all, run_test, run_block
from .commands.fix import fix_tests

console = Console()

@click.group()
def cli():
    """Kaizen Agent CLI for running and fixing tests."""
    pass

# Register commands
cli.add_command(test_all)
cli.add_command(run_test)
cli.add_command(run_block)
cli.add_command(fix_tests)

if __name__ == '__main__':
    cli() 