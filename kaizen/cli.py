import click
import yaml
import json
from typing import Dict, Any, Optional
from .agent_runners import TestLogger
from .code_region import extract_code_regions
import os
from datetime import datetime
import types
from pathlib import Path
from .runner import TestRunner, run_test_block
from .autofix import run_autofix_and_pr
from .test_generator import TestGenerator
import sys
from rich import print as console_print

@click.group()
def cli():
    """Kaizen Agent - A testing framework for AI agents."""
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
        with open(config, 'r') as f:
            test_config = yaml.safe_load(f)
            
        # Create test runner
        runner = TestRunner(test_config)
        logger = TestLogger(test_config.get('name', 'Unnamed Test'))
        
        click.echo(f"Running test: {test_config.get('name', 'Unnamed Test')}")
        click.echo("=" * 50)
        
        # Extract file path from the root of the configuration
        file_path = test_config.get('file_path')
        if not file_path:
            console_print("[red]Error: No file_path found in test configuration[/red]")
            sys.exit(1)
            
        results = runner.run_tests(Path(file_path))
        
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
                file_path = test_config.get('file_path')
                if file_path:
                    run_autofix_and_pr(failed_tests, file_path, config, max_retries=max_retries)
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

@cli.command()
@click.option('--project', '-p', type=click.Path(exists=True), required=True, help='Path to agent project')
@click.option('--results', '-r', type=click.Path(exists=True), help='Path to test results directory')
@click.option('--output', '-o', type=click.Path(), default='./test-examples', help='Directory to write new YAML test files')
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to existing test configuration file or directory')
@click.option('--suggestions', is_flag=True, help='Include rationale/comments in YAML')
@click.option('--make-pr', is_flag=True, help='Create a GitHub pull request')
def generate_tests(project: str, results: Optional[str], output: str, config: Optional[str], suggestions: bool, make_pr: bool):
    """
    Generate new YAML-based test cases for an agent project.
    
    PROJECT: Path to agent code (Python or TypeScript)
    RESULTS: Path to existing test results folder (JSON or logs)
    OUTPUT: Directory to write new YAML test files (default: ./test-examples)
    """
    try:
        # Initialize test generator
        generator = TestGenerator(project, results, output)
        
        # Generate test cases
        click.echo("Analyzing codebase and test results...")
        test_cases = generator.generate_tests(
            include_suggestions=suggestions,
            config_path=config
        )
        
        if not test_cases:
            click.echo("No test cases were generated.")
            return
        
        # Save test cases
        click.echo(f"Saving {len(test_cases)} test cases...")
        saved_files = generator.save_test_cases(test_cases)
        
        if not saved_files:
            click.echo("No test files were saved.")
            return
        
        click.echo(f"Saved test files to: {', '.join(saved_files)}")
        
        # Create pull request if requested
        if make_pr:
            click.echo("Creating pull request...")
            branch_name = f"auto/gen-tests-{datetime.now().strftime('%Y%m%d')}"
            
            if generator.create_pull_request(branch_name, saved_files):
                click.echo(f"Successfully created pull request from branch: {branch_name}")
            else:
                click.echo("Failed to create pull request.")
        
    except Exception as e:
        click.echo(f"Error generating tests: {str(e)}")
        raise click.Abort()

if __name__ == '__main__':
    cli() 