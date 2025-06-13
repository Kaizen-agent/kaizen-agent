import click
import yaml
import json
from typing import Dict, Any
from .agent_runners import TestLogger
from .code_region import extract_code_regions
import os
from datetime import datetime
import types
from pathlib import Path
from .runner import TestRunner, run_test_block
from .autofix import run_autofix_and_pr

@click.group()
def cli():
    """Kaizen Agent - A testing framework for AI agents."""
    pass

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
def test_all(config: str, auto_fix: bool, create_pr: bool):
    """
    Run all tests specified in the configuration file.
    
    CONFIG: Path to the test configuration YAML file
    """
    try:
        with open(config, 'r') as f:
            test_config = yaml.safe_load(f)
            
        # Create test runner
        runner = TestRunner(test_config)
        logger = TestLogger(test_config.get('name', 'Unnamed Test'))
        
        click.echo(f"Running test: {test_config.get('name', 'Unnamed Test')}")
        click.echo("=" * 50)
        
        # Run tests
        results = runner.run_tests(Path(config))
        
        # Check if any tests failed
        failed_tests = []
        for region, result in results.items():
            for test_case in result.get('test_cases', []):
                if test_case['status'] != 'passed':
                    failed_tests.append({
                        'region': region,
                        'test_name': test_case['name'],
                        'error_message': test_case.get('details', 'Test failed')
                    })
        
        if failed_tests and auto_fix:
            click.echo("\nAttempting to fix failing tests...")
            file_path = test_config.get('file_path')
            if file_path:
                run_autofix_and_pr(failed_tests, file_path)
            else:
                click.echo("Error: file_path not specified in test configuration")
        
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

if __name__ == '__main__':
    cli() 