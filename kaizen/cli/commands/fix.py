"""Fix-related CLI commands."""

import click
import yaml
from pathlib import Path
from typing import Optional
from rich.console import Console

from ...autofix.test.runner import TestRunner
from ...utils.test_utils import collect_failed_tests
from ...autofix.main import AutoFix

console = Console()

@click.command()
@click.argument('test_files', nargs=-1, type=click.Path(exists=True))
@click.option('--project', '-p', type=click.Path(exists=True), required=True, help='Path to agent project')
@click.option('--results', '-r', type=click.Path(), help='Path to save test results')
@click.option('--make-pr', is_flag=True, help='Create a GitHub pull request')
@click.option('--max-retries', type=int, default=1, help='Maximum number of retry attempts for auto-fix (default: 1)')
@click.option('--base-branch', default='main', help='Base branch for pull request (default: main)')
def fix_tests(test_files: tuple, project: str, results: Optional[str], make_pr: bool, max_retries: int, base_branch: str):
    """Automatically fix failing tests."""
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
                AutoFix(Path(test_file)).fix_code(str(resolved_file_path), failed_tests, max_retries=max_retries, create_pr=make_pr, base_branch=base_branch)
                fixed_tests.extend(failed_tests)
        
        if fixed_tests:
            console.print(f"\n[green]Successfully fixed {len(fixed_tests)} tests![/green]")
        else:
            console.print("\n[yellow]No tests were fixed.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error fixing tests: {str(e)}[/red]")
        raise click.Abort() 