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
                
        if 'tests' not in config:
            raise click.ClickException("Config must contain 'tests' section")
            
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
@click.pass_context
def test_all(ctx: click.Context, config: str, auto_fix: bool, create_pr: bool, 
             max_retries: int, base_branch: str) -> None:
    """Run all tests in the configuration."""
    try:
        # Update context
        ctx.obj.config_path = Path(config)
        ctx.obj.auto_fix = auto_fix
        ctx.obj.create_pr = create_pr
        ctx.obj.max_retries = max_retries
        ctx.obj.base_branch = base_branch
        
        # Load config
        ctx.obj.config = load_config(ctx.obj.config_path)
        
        # Run tests
        test_file_path = Path(ctx.obj.config['file_path'])
        runner = TestRunner(ctx.obj.config)
        results = runner.run_tests(test_file_path)
        
        # Handle results
        if results['_status'] == 'error':
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
@click.argument('test_files', nargs=-1, type=click.Path(exists=True))
@click.option('--project', type=click.Path(exists=True), required=True, help='Project root directory')
@click.option('--make-pr', is_flag=True, help='Create pull request with fixes')
@click.option('--max-retries', type=int, default=1, help='Maximum number of fix attempts')
@click.option('--base-branch', type=str, default='main', help='Base branch for pull request')
@click.pass_context
def fix_tests(ctx: click.Context, test_files: tuple, project: str, make_pr: bool,
              max_retries: int, base_branch: str) -> None:
    """Fix specific test files."""
    try:
        # Update context
        ctx.obj.config = {
            'name': 'Fix Tests',
            'file_path': project,
            'tests': [{'name': Path(f).stem, 'input': {'file': f}} for f in test_files]
        }
        ctx.obj.auto_fix = True
        ctx.obj.create_pr = make_pr
        ctx.obj.max_retries = max_retries
        ctx.obj.base_branch = base_branch
        
        # Run fixer
        fixer = AutoFix(ctx.obj.config)
        results = fixer.fix_issues({}, max_retries)
        
        if make_pr and results.get('fixed'):
            pr_creator = PRManager(ctx.obj.config)
            pr_url = pr_creator.create_pr(base_branch)
            click.echo(f"Created pull request: {pr_url}")
            
        if not results.get('fixed'):
            sys.exit(ExitCode.FIX_ERROR.value)
            
        click.echo("All tests fixed!")
        sys.exit(ExitCode.SUCCESS.value)
        
    except Exception as e:
        logger.exception("Unexpected error")
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(ExitCode.UNKNOWN_ERROR.value)

def main() -> None:
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main() 