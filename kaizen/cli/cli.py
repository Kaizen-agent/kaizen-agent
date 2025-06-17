"""Main CLI module for Kaizen."""

import click
from rich.console import Console

from .commands.test import test_all
from .commands.fix import fix_tests
from test_agent.email_agent.email_agent import main as email_agent

console = Console()

@click.group()
def cli():
    """Kaizen Agent CLI for running and fixing tests."""
    pass

# Register commands
cli.add_command(test_all)
cli.add_command(fix_tests)
cli.add_command(email_agent, name='email')

if __name__ == '__main__':
    cli() 