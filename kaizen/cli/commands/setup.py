"""Setup commands for Kaizen CLI."""

import click
from pathlib import Path
from typing import Optional

from ..utils.env_setup import (
    display_environment_status,
    create_env_example_file,
    check_environment_setup,
    get_missing_variables
)

@click.command()
@click.option('--workspace', type=click.Path(exists=True), help='Workspace root directory')
@click.option('--features', multiple=True, 
              type=click.Choice(['core', 'github', 'optional']),
              help='Features to check (can specify multiple)')
def check_env(workspace: Optional[str], features: tuple) -> None:
    """Check environment setup and display status.
    
    This command checks if all required environment variables are set
    and displays helpful information about the current setup.
    """
    workspace_path = Path(workspace) if workspace else None
    required_features = list(features) if features else ['core']
    
    display_environment_status(workspace_path, required_features)

@click.command()
@click.option('--workspace', type=click.Path(exists=True), help='Workspace root directory')
def create_env_example(workspace: Optional[str]) -> None:
    """Create a .env.example file with all required environment variables.
    
    This command creates a template .env.example file that users can copy
    to .env and fill in with their actual values.
    """
    workspace_path = Path(workspace) if workspace else None
    create_env_example_file(workspace_path)

@click.command()
@click.option('--workspace', type=click.Path(exists=True), help='Workspace root directory')
@click.option('--features', multiple=True, 
              type=click.Choice(['core', 'github', 'optional']),
              help='Features to validate (can specify multiple)')
def validate_env(workspace: Optional[str], features: tuple) -> None:
    """Validate environment setup and exit with appropriate code.
    
    This command validates the environment setup and exits with code 0
    if everything is properly configured, or code 1 if there are issues.
    This is useful for CI/CD pipelines and automated scripts.
    """
    workspace_path = Path(workspace) if workspace else None
    required_features = list(features) if features else ['core']
    
    is_setup = check_environment_setup(workspace_path, required_features)
    
    if is_setup:
        click.echo("✅ Environment is properly configured")
        exit(0)
    else:
        missing_vars = get_missing_variables(required_features)
        click.echo(f"❌ Environment is not properly configured. Missing variables: {', '.join(missing_vars)}")
        exit(1)

@click.group()
def setup() -> None:
    """Setup and configuration commands for Kaizen."""
    pass

# Add commands to the setup group
setup.add_command(check_env, name='check-env')
setup.add_command(create_env_example, name='create-env-example')
setup.add_command(validate_env, name='validate-env') 