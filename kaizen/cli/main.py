"""Kaizen CLI implementation."""

import os
import sys
import logging
import click
import yaml
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from kaizen.autofix.test.runner import TestRunner
from kaizen.autofix.pr.manager import PRManager
from kaizen.autofix.main import AutoFix
from .utils.env_setup import check_environment_setup, display_environment_status
from .commands.setup import setup
from .commands.debug_typescript import debug_typescript
from kaizen.cli.commands.models.test_execution_result import TestStatus

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

@cli.command()
@click.option('--config', type=click.Path(exists=True), required=True, help='Path to test config file')
@click.option('--auto-fix', is_flag=True, help='Enable automatic code fixing')
@click.option('--create-pr', is_flag=True, help='Create pull request with fixes')
@click.option('--max-retries', type=int, default=1, help='Maximum number of fix attempts')
@click.option('--base-branch', type=str, default='main', help='Base branch for pull request')
@click.option('--skip-env-check', is_flag=True, help='Skip environment validation')
@click.pass_context
def test_all(ctx: click.Context, config: str, auto_fix: bool, create_pr: bool, 
             max_retries: int, base_branch: str, skip_env_check: bool) -> None:
    """Run all tests in the configuration."""
    try:
        # Update context
        ctx.obj.config_path = Path(config)
        ctx.obj.auto_fix = auto_fix
        ctx.obj.create_pr = create_pr
        ctx.obj.max_retries = max_retries
        ctx.obj.base_branch = base_branch
        
        # Validate environment unless skipped
        if not skip_env_check:
            validate_environment(auto_fix, create_pr)
        
        # Load config
        ctx.obj.config = load_config(ctx.obj.config_path)
        
        # Add config file path to config for proper file resolution
        ctx.obj.config['config_file'] = str(ctx.obj.config_path)
        
        # Run tests
        test_file_path = Path(ctx.obj.config['file_path'])
        runner = TestRunner(ctx.obj.config)
        results = runner.run_tests(test_file_path)
        
        # Handle results
        if results.status == TestStatus.ERROR:
            if auto_fix:
                fixer = AutoFix(ctx.obj.config)
                fix_results = fixer.fix_issues(results, max_retries)
                
                if create_pr and fix_results.get('fixed'):
                    pr_creator = PRManager(ctx.obj.config)
                    pr_url = pr_creator.create_pr(base_branch)
                    click.echo(f"Created pull request: {pr_url}")
                    
                if not fix_results.get('fixed'):
                    sys.exit(ExitCode.FIX_ERROR.value)
            else:
                sys.exit(ExitCode.TEST_ERROR.value)
                
        click.echo("All tests passed!")
        sys.exit(ExitCode.SUCCESS.value)
        
    except click.ClickException as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(ExitCode.CONFIG_ERROR.value)
    except Exception as e:
        logger.exception("Unexpected error")
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(ExitCode.UNKNOWN_ERROR.value)

@cli.command()
@click.option('--config', type=click.Path(exists=True), help='Path to test config file (optional)')
@click.option('--repo', help='Repository name (owner/repo)')
@click.option('--base-branch', type=str, default='main', help='Base branch for testing')
def test_github_access(ctx: click.Context, config: Optional[str], repo: Optional[str], base_branch: str) -> None:
    """Test GitHub access and permissions for private repositories."""
    try:
        from .commands.test_github_access import test_github_access as test_access
        
        # Call the test function with the provided arguments
        test_access.callback(config=config, repo=repo, base_branch=base_branch)
        
    except Exception as e:
        logger.exception("GitHub access test failed")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(ExitCode.PR_ERROR.value)

@cli.command()
@click.option('--config', type=click.Path(exists=True), help='Test configuration file (optional)')
@click.option('--repo', help='Repository name (owner/repo)')
@click.option('--token', help='GitHub token to test (optional, uses GITHUB_TOKEN env var if not provided)')
def diagnose_github_access(ctx: click.Context, config: Optional[str], repo: Optional[str], token: Optional[str]) -> None:
    """Comprehensive GitHub access diagnostic for troubleshooting organization and repository issues."""
    try:
        from .commands.diagnose_github_access import diagnose_github_access as diagnose_access
        
        # Call the diagnostic function with the provided arguments
        diagnose_access.callback(config=config, repo=repo, token=token)
        
    except Exception as e:
        logger.exception("GitHub diagnostic failed")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(ExitCode.PR_ERROR.value)

# Add setup commands
cli.add_command(setup)

# Add analyze-logs command
from .commands.analyze_logs import analyze_logs
cli.add_command(analyze_logs)

# Add debug-typescript command
cli.add_command(debug_typescript)

def main() -> None:
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main() 