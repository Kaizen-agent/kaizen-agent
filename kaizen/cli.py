import click
import yaml
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console

from .runner import TestRunner, run_test_block
from .logger import TestLogger
from .autofix import run_autofix_and_pr

console = Console()

def collect_failed_tests(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect all failed tests from the test results dictionary.
    
    Args:
        results: Dictionary containing test results by region
        
    Returns:
        List of dictionaries containing failed test information
    """
    failed_tests = []
    
    # Check overall status first
    overall_status = results.get('overall_status', {})
    if overall_status.get('status') == 'failed':
        # Add overall failure if there's an error message
        if 'error' in overall_status:
            failed_tests.append({
                'region': 'overall',
                'test_name': 'Overall Test Execution',
                'error_message': overall_status['error'],
                'output': 'No output available'
            })
        
        # Add evaluation failure if present
        if 'evaluation' in overall_status:
            eval_results = overall_status['evaluation']
            if eval_results.get('status') == 'failed':
                failed_tests.append({
                    'region': 'evaluation',
                    'test_name': 'LLM Evaluation',
                    'error_message': f"Evaluation failed with score: {eval_results.get('overall_score')}",
                    'output': str(eval_results.get('criteria', {}))
                })
        
        # Add evaluation error if present
        if 'evaluation_error' in overall_status:
            failed_tests.append({
                'region': 'evaluation',
                'test_name': 'LLM Evaluation',
                'error_message': overall_status['evaluation_error'],
                'output': 'No output available'
            })
    
    # Check individual test cases
    for region, result in results.items():
        if region == 'overall_status':
            continue
            
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
                
            if test_case.get('status') == 'failed':
                failed_tests.append({
                    'region': region,
                    'test_name': test_case.get('name', 'Unknown Test'),
                    'error_message': test_case.get('details', 'Test failed'),
                    'output': test_case.get('output', 'No output available')
                })
    
    return failed_tests

@click.group()
def cli():
    """Kaizen Agent CLI for running and fixing tests."""
    pass

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True, help='Test configuration file')
@click.option('--auto-fix', is_flag=True, help='Automatically fix failing tests')
@click.option('--create-pr', is_flag=True, help='Create a pull request with fixes')
@click.option('--max-retries', type=int, default=1, help='Maximum number of retry attempts for auto-fix (default: 1)')
@click.option('--base-branch', default='main', help='Base branch for pull request (default: main)')
def test_all(config: str, auto_fix: bool, create_pr: bool, max_retries: int, base_branch: str):
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
        print(results)
        # Check if any tests failed
        failed_tests = collect_failed_tests(results)
        
        if failed_tests:
            click.echo("\nFailed Tests:")
            for test in failed_tests:
                click.echo(f"- {test['test_name']} ({test['region']}): {test['error_message']}")
                if test['output']:
                    click.echo(f"  Output: {test['output']}")
            
            if auto_fix:
                click.echo(f"\nAttempting to fix failing tests (max retries: {max_retries})...")
                if file_path:
                    run_autofix_and_pr(failed_tests, str(resolved_file_path), str(config_path), max_retries=max_retries, create_pr=create_pr, base_branch=base_branch)
                    if create_pr:
                        click.echo("Pull request created with fixes")
                else:
                    click.echo("Error: file_path not specified in test configuration")
        else:
            click.echo("\nAll tests passed!")
        
        # Output results
        click.echo("\nTest Results Summary")
        click.echo("=" * 50)
        
        # Print test configuration details
        click.echo(f"\nTest Configuration:")
        click.echo(f"- Name: {test_config.get('name', 'Unnamed Test')}")
        click.echo(f"- File: {resolved_file_path}")
        click.echo(f"- Config: {config_path}")
        
        # Print overall status
        overall_status = results.get('overall_status', 'unknown')
        status = overall_status.get('status', 'unknown') if isinstance(overall_status, dict) else overall_status
        status_emoji = "✅" if status == 'passed' else "❌"
        click.echo(f"\nOverall Status: {status_emoji} {status.upper()}")
        
        # Print test results table
        click.echo("\nTest Results Table:")
        click.echo("| Test Name | Region | Status | Details |")
        click.echo("|-----------|--------|--------|---------|")
        
        for region, result in results.items():
            if region == 'overall_status':
                continue
                
            test_cases = result.get('test_cases', [])
            for test_case in test_cases:
                status = "✅ PASS" if test_case.get('status') == 'passed' else "❌ FAIL"
                try:
                    details = str(test_case.get('details', ''))
                    if len(details) > 50:
                        details = details[:47] + "..."
                except Exception:
                    details = "Error displaying details"
                click.echo(f"| {test_case.get('name', 'Unknown')} | {region} | {status} | {details} |")
        
        # Print failed tests details if any
        failed_tests = collect_failed_tests(results)
        if failed_tests:
            click.echo("\nFailed Tests Details:")
            click.echo("=" * 50)
            for test in failed_tests:
                click.echo(f"\nTest: {test['test_name']} ({test['region']})")
                click.echo(f"Error: {test['error_message']}")
                if test['output']:
                    click.echo(f"Output:\n{test['output']}")
            
            if auto_fix:
                click.echo("\nAuto-fix Attempts:")
                click.echo("=" * 50)
                click.echo(f"Maximum retries: {max_retries}")
                if create_pr:
                    click.echo("Pull request will be created with fixes")
        
        # Save detailed results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = Path("test-results") / f"{test_config.get('name', 'test')}_{timestamp}_report.txt"
        result_file.parent.mkdir(exist_ok=True)
        
        with open(result_file, 'w') as f:
            f.write("Test Results Report\n")
            f.write("=" * 50 + "\n\n")
            
            # Write configuration details
            f.write("Test Configuration:\n")
            f.write(f"- Name: {test_config.get('name', 'Unnamed Test')}\n")
            f.write(f"- File: {resolved_file_path}\n")
            f.write(f"- Config: {config_path}\n\n")
            
            # Write overall status
            f.write(f"Overall Status: {status_emoji} {status.upper()}\n\n")
            
            # Write detailed test results
            f.write("Detailed Test Results:\n")
            f.write("=" * 50 + "\n\n")
            
            for region, result in results.items():
                if region == 'overall_status':
                    continue
                    
                f.write(f"Region: {region}\n")
                f.write("-" * 30 + "\n")
                
                test_cases = result.get('test_cases', [])
                for test_case in test_cases:
                    f.write(f"\nTest: {test_case.get('name', 'Unknown')}\n")
                    f.write(f"Status: {test_case.get('status', 'unknown')}\n")
                    if test_case.get('details'):
                        f.write(f"Details: {test_case.get('details')}\n")
                    if test_case.get('output'):
                        f.write(f"Output:\n{test_case.get('output')}\n")
                    if test_case.get('evaluation'):
                        f.write(f"Evaluation:\n{json.dumps(test_case.get('evaluation'), indent=2)}\n")
                    f.write("-" * 30 + "\n")
            
            # Write failed tests section if any
            if failed_tests:
                f.write("\nFailed Tests Analysis:\n")
                f.write("=" * 50 + "\n\n")
                for test in failed_tests:
                    f.write(f"Test: {test['test_name']} ({test['region']})\n")
                    f.write(f"Error: {test['error_message']}\n")
                    if test['output']:
                        f.write(f"Output:\n{test['output']}\n")
                    f.write("-" * 30 + "\n")
        
        click.echo(f"\nDetailed report saved to: {result_file}")
        
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
@click.option('--max-retries', type=int, default=1, help='Maximum number of retry attempts for auto-fix (default: 1)')
@click.option('--base-branch', default='main', help='Base branch for pull request (default: main)')
def fix_tests(test_files: tuple, project: str, results: Optional[str], make_pr: bool, max_retries: int, base_branch: str):
    """
    Automatically fix failing tests.
    
    TEST_FILES: One or more YAML test files to fix
    """
    try:
        fixed_tests = []
        for test_file in test_files:
            # Load test configuration
            with open(test_file, 'r') as f:
                test_config = yaml.safe_load(f)
            
            # Get file path from test configuration
            file_path = test_config.get('file_path')
            if not file_path:
                console.print(f"[red]Error: No file_path found in test configuration: {test_file}[/red]")
                continue
                
            # Resolve file path relative to test file's directory
            resolved_file_path = (Path(test_file).parent / file_path).resolve()
            if not resolved_file_path.exists():
                console.print(f"[red]Error: File not found: {resolved_file_path}[/red]")
                continue
            
            # Run tests to get failures
            runner = TestRunner(test_config)
            test_results = runner.run_tests(resolved_file_path)
            
            # Collect failed tests
            failed_tests = collect_failed_tests(test_results)
            
            if failed_tests:
                # Run auto-fix
                run_autofix_and_pr(failed_tests, str(resolved_file_path), str(Path(test_file).resolve()), max_retries=max_retries, create_pr=make_pr, base_branch=base_branch)
                fixed_tests.extend(failed_tests)
        
        if fixed_tests:
            console.print(f"\n[green]Successfully fixed {len(fixed_tests)} tests![/green]")
        else:
            console.print("\n[yellow]No tests were fixed.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error fixing tests: {str(e)}[/red]")
        raise click.Abort()

if __name__ == '__main__':
    cli() 