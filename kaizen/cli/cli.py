"""Main CLI module for Kaizen."""

import os
import sys
import logging
import click
import yaml
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from rich.console import Console

from .commands.test import test_all
from .commands.debug_typescript import debug_typescript
from .commands.test_github_access import test_github_access
from .commands.diagnose_github_access import diagnose_github_access
from .commands.setup import setup
from .commands.analyze_logs import analyze_logs
from .commands.augment import augment
from .utils.env_setup import check_environment_setup, display_environment_status

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExitCode(Enum):
    """Exit codes for CLI commands."""
    SUCCESS = 0
    CONFIG_ERROR = 1
    TEST_ERROR = 2
    FIX_ERROR = 3
    PR_ERROR = 4
    ENV_ERROR = 5
    UNKNOWN_ERROR = 255

@dataclass
class CliContext:
    """CLI context object."""
    debug: bool
    config_path: Path
    auto_fix: bool
    create_pr: bool
    max_retries: int
    base_branch: str
    config: Dict

def load_config(config_path: Path) -> Dict:
    """
    Load and validate configuration file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Dict containing configuration
        
    Raises:
        click.ClickException: If config is invalid
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required fields
        required_fields = ['name', 'file_path']
        for field in required_fields:
            if field not in config:
                raise click.ClickException(f"Missing required field '{field}' in config")
        
        # Support both old 'tests' format and new 'steps' format
        if 'tests' not in config and 'steps' not in config:
            raise click.ClickException("Config must contain either 'tests' or 'steps' section")
            
        return config
        
    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML in config file: {str(e)}")
    except Exception as e:
        raise click.ClickException(f"Failed to load config: {str(e)}")

def setup_logging(debug: bool) -> None:
    """
    Set up logging configuration.
    
    Args:
        debug: Whether to enable debug logging
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().setLevel(level)
    
    # Add file handler for debug mode
    if debug:
        log_file = Path('kaizen-debug.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

def validate_environment(auto_fix: bool, create_pr: bool) -> None:
    """
    Validate environment setup before running commands.
    
    Args:
        auto_fix: Whether auto-fix is enabled
        create_pr: Whether PR creation is enabled
        
    Raises:
        click.ClickException: If environment is not properly configured
    """
    # Determine required features based on command options
    required_features = ['core']  # Core is always required
    
    if create_pr:
        required_features.append('github')
    
    # Check environment setup
    if not check_environment_setup(required_features=required_features):
        click.echo("❌ Environment is not properly configured.")
        click.echo("\nRun 'kaizen setup check-env' to see detailed status and setup instructions.")
        click.echo("Run 'kaizen setup create-env-example' to create a .env.example file.")
        raise click.ClickException("Environment validation failed")

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
@click.pass_context
def cli(ctx: click.Context, debug: bool, config: Optional[str]) -> None:
    """Kaizen - AI-Powered Test Automation and Code Fixing."""
    setup_logging(debug)
    
    # Create context object
    ctx.obj = CliContext(
        debug=debug,
        config_path=Path(config) if config else None,
        auto_fix=False,
        create_pr=False,
        max_retries=1,
        base_branch='main',
        config={}
    )

# Register commands
cli.add_command(test_all)
cli.add_command(debug_typescript)
cli.add_command(test_github_access)
cli.add_command(diagnose_github_access)
cli.add_command(setup)
cli.add_command(analyze_logs)
cli.add_command(augment)

if __name__ == '__main__':
    cli() 