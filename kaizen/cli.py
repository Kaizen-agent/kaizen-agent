import click
import yaml
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console

from .runner import TestRunner, run_test_block
from .logger import TestLogger
from .autofix import run_autofix_and_pr

console = Console()

@click.group()
def cli():
    """Kaizen Agent CLI for running and fixing tests."""
    pass

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=1, help='Maximum number of retry attempts for auto-fix (default: 1)')
def test_all(config: str, auto_fix: bool, create_pr: bool, max_retries: int):
    """
    Run all tests specified in the configuration file.
    
    CONFIG: Path to the test configuration YAML file
    """
    try:
        config_path = Path(config)
        with open(config_path, 'r') as f:
            test_config = yaml.safe_load(f)
            
        # Add config file path to test configuration
        test_config['config_file'] = str(config_path)
            
        # Create test runner
        runner = TestRunner(test_config)
        logger = TestLogger(test_config.get('name', 'Unnamed Test'))
        
        click.echo(f"Running test: {test_config.get('name', 'Unnamed Test')}")
        click.echo("=" * 50)
        
        # Extract file path from the root of the configuration and resolve it relative to config file
        file_path = test_config.get('file_path')
        if not file_path:
            console.print("[red]Error: No file_path found in test configuration[/red]")
            sys.exit(1)
            
        # Resolve file_path relative to config file's directory
        resolved_file_path = (config_path.parent / file_path).resolve()
        console.print(f"[blue]Debug: Resolved file path: {resolved_file_path}[/blue]")
        
        if not resolved_file_path.exists():
            console.print(f"[red]Error: File not found: {resolved_file_path}[/red]")
            sys.exit(1)
            
        results = runner.run_tests(resolved_file_path)
        
        # Check if any tests failed
        failed_tests = []
        for region, result in results.items():
            if not isinstance(result, dict):
                click.echo(f"Warning: Invalid result format for region {region}: {result}")
                continue
                
            test_cases = result.get('test_cases', [])
            if not isinstance(test_cases, list):
                click.echo(f"Warning: Invalid test_cases format for region {region}: {test_cases}")
                continue
                
            for test_case in test_cases:
                if not isinstance(test_case, dict):
                    click.echo(f"Warning: Invalid test case format: {test_case}")
                    continue
                    
                if test_case.get('status') != 'passed':
                    failed_tests.append({
                        'region': region,
                        'test_name': test_case.get('name', 'Unknown Test'),
                        'error_message': test_case.get('details', 'Test failed'),
                        'output': test_case.get('output', 'No output available')
                    })
        
        if failed_tests:
            click.echo("\nFailed Tests:")
            for test in failed_tests:
                click.echo(f"- {test['test_name']} ({test['region']}): {test['error_message']}")
                if test['output']:
                    click.echo(f"  Output: {test['output']}")
            
            if auto_fix:
                click.echo(f"\nAttempting to fix failing tests (max retries: {max_retries})...")
                if file_path:
                    run_autofix_and_pr(failed_tests, str(resolved_file_path), config, max_retries=max_retries, create_pr=create_pr)
                    if create_pr:
                        click.echo("Pull request created with fixes")
                else:
                    click.echo("Error: file_path not specified in test configuration")
        else:
            click.echo("\nAll tests passed!")
        
        # Output results
        click.echo("\nTest Results:")
        click.echo(json.dumps(results, indent=2))
        
    except Exception as e:
        click.echo(f"Error running tests: {str(e)}")
        raise click.Abort()

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.argument('input_text', required=False)
@click.option('--output', '-o', type=click.Path(), help='Path to save output to')
def run_block(file_path: str, input_text: str = None, output: str = None):
    """
    Execute a code block between kaizen markers in a Python file.
    
    FILE_PATH: Path to the Python file containing the code block
    INPUT_TEXT: Optional input to pass to the function/class in the block
    """
    try:
        result = run_test_block(file_path, input_text)
        
        if output:
            with open(output, 'w') as f:
                f.write(result)
            click.echo(f"Output saved to: {output}")
        else:
            click.echo("\nExecution Result:")
            click.echo("=" * 50)
            click.echo(result)
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('test_file', type=click.Path(exists=True))
def run_test(test_file: str):
    """Run a test file and display results."""
    try:
        with open(test_file, 'r') as f:
            test_config = yaml.safe_load(f)
        
        # Create test runner
        runner = TestRunner()
        logger = TestLogger(test_config.get('name', 'Unnamed Test'))
        
        click.echo(f"Running test: {test_config.get('name', 'Unnamed Test')}")
        click.echo("=" * 50)
        
        # Run tests (use run_test, not run_tests)
        passed = runner.run_test(test_file)
        
        if passed:
            click.echo("\nAll steps passed! See test-results/ for details.")
        else:
            click.echo("\nSome steps failed. See test-results/ for details.")
        
    except Exception as e:
        click.echo(f"Error running test: {str(e)}")
        raise click.Abort()

# TODO: Future test generation functionality will be moved to experimental/test_generator.py
# The core CLI now focuses on running tests, analyzing failures, and creating PRs for fixes

@cli.command()
@click.argument('test_files', nargs=-1, type=click.Path(exists=True))
@click.option('--project', '-p', type=click.Path(exists=True), required=True, help='Path to agent project')
@click.option('--results', '-r', type=click.Path(), help='Path to save test results')
@click.option('--make-pr', is_flag=True, help='Create a GitHub pull request')
def fix_tests(test_files: tuple, project: str, results: Optional[str], make_pr: bool):
    """
    Automatically fix failing tests.
    
    TEST_FILES: One or more YAML test files to fix
    """
    try:
        # Run auto-fix
        fixed_tests = auto_fix_tests(test_files, project, results, make_pr)
        
        if fixed_tests:
            console.print(f"\n[green]Successfully fixed {len(fixed_tests)} tests![/green]")
        else:
            console.print("\n[yellow]No tests were fixed.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error fixing tests: {str(e)}[/red]")
        raise click.Abort()

if __name__ == '__main__':
    cli() 