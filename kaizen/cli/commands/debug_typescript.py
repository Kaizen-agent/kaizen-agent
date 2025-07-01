"""TypeScript debugging command for Kaizen CLI.

This command helps debug TypeScript execution issues by providing detailed
information about the execution environment, dependencies, and performance.
"""

import click
import subprocess
import os
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

@click.command()
@click.option('--test-file', type=click.Path(exists=True), help='Test a specific TypeScript file')
@click.option('--check-deps', is_flag=True, help='Check TypeScript dependencies')
@click.option('--benchmark', is_flag=True, help='Run performance benchmarks')
@click.option('--diagnose', is_flag=True, help='Run comprehensive TypeScript environment diagnosis')
@click.option('--verbose', '-v', is_flag=True, help='Show verbose output')
def debug_typescript(test_file: str, check_deps: bool, benchmark: bool, diagnose: bool, verbose: bool):
    """Debug TypeScript execution issues.
    
    This command helps identify and resolve TypeScript execution problems
    by checking the environment, dependencies, and performance.
    """
    console.print(Panel.fit("🔍 TypeScript Debugging Tool", style="bold blue"))
    
    # Check basic environment
    console.print("\n[bold]1. Environment Check[/bold]")
    check_environment()
    
    # Run comprehensive diagnosis
    if diagnose:
        console.print("\n[bold]2. Comprehensive TypeScript Diagnosis[/bold]")
        run_comprehensive_diagnosis()
    
    # Check TypeScript dependencies
    if check_deps:
        console.print("\n[bold]3. Dependency Check[/bold]")
        check_dependencies()
    
    # Test specific file
    if test_file:
        console.print(f"\n[bold]4. File Test: {test_file}[/bold]")
        test_typescript_file(test_file, verbose)
    
    # Run benchmarks
    if benchmark:
        console.print("\n[bold]5. Performance Benchmark[/bold]")
        run_benchmarks()
    
    console.print("\n[bold green]✅ Debugging complete![/bold green]")

def check_environment():
    """Check the basic execution environment."""
    table = Table(title="Environment Information")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version/Path", style="yellow")
    
    # Check Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            table.add_row("Node.js", "✅ Available", result.stdout.strip())
        else:
            table.add_row("Node.js", "❌ Not found", "Not installed")
    except FileNotFoundError:
        table.add_row("Node.js", "❌ Not found", "Not installed")
    
    # Check npm
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            table.add_row("npm", "✅ Available", result.stdout.strip())
        else:
            table.add_row("npm", "❌ Not found", "Not installed")
    except FileNotFoundError:
        table.add_row("npm", "❌ Not found", "Not installed")
    
    # Check ts-node
    try:
        result = subprocess.run(['npx', 'ts-node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            table.add_row("ts-node", "✅ Available", result.stdout.strip())
        else:
            table.add_row("ts-node", "❌ Not found", "Run: npm install -g ts-node")
    except FileNotFoundError:
        table.add_row("ts-node", "❌ Not found", "Run: npm install -g ts-node")
    
    # Check TypeScript
    try:
        result = subprocess.run(['npx', 'tsc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            table.add_row("TypeScript", "✅ Available", result.stdout.strip())
        else:
            table.add_row("TypeScript", "❌ Not found", "Run: npm install -g typescript")
    except FileNotFoundError:
        table.add_row("TypeScript", "❌ Not found", "Run: npm install -g typescript")
    
    # Check cache directory
    cache_dir = Path.home() / '.kaizen' / 'ts-cache'
    if cache_dir.exists():
        table.add_row("Cache Directory", "✅ Available", str(cache_dir))
    else:
        table.add_row("Cache Directory", "⚠️  Not found", "Will be created automatically")
    
    console.print(table)

def check_dependencies():
    """Check TypeScript-related dependencies."""
    table = Table(title="Dependency Check")
    table.add_column("Package", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version", style="yellow")
    
    # Common TypeScript packages
    packages = [
        'typescript',
        'ts-node',
        '@types/node',
        '@ai-sdk/google',
        '@mastra/core'
    ]
    
    for package in packages:
        try:
            result = subprocess.run(['npm', 'list', package], capture_output=True, text=True)
            if result.returncode == 0:
                # Extract version from npm list output
                lines = result.stdout.strip().split('\n')
                if len(lines) > 0 and package in lines[0]:
                    version = lines[0].split('@')[-1] if '@' in lines[0] else 'unknown'
                    table.add_row(package, "✅ Installed", version)
                else:
                    table.add_row(package, "❌ Not installed", "Not found")
            else:
                table.add_row(package, "❌ Not installed", "Not found")
        except Exception:
            table.add_row(package, "❌ Error checking", "Check failed")
    
    console.print(table)

def test_typescript_file(file_path: str, verbose: bool):
    """Test a specific TypeScript file."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        console.print(f"[red]❌ File not found: {file_path}[/red]")
        return
    
    console.print(f"Testing file: {file_path}")
    
    # Read file content
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        console.print(f"File size: {len(content)} characters")
    except Exception as e:
        console.print(f"[red]❌ Error reading file: {str(e)}[/red]")
        return
    
    # Check for Mastra patterns
    mastra_patterns = [
        '@mastra/core/agent',
        'new agent(',
        '@ai-sdk/google',
        'google(',
        'gemini-',
        'openai(',
        'anthropic('
    ]
    
    is_mastra = any(pattern in content.lower() for pattern in mastra_patterns)
    console.print(f"Mastra agent detected: {'Yes' if is_mastra else 'No'}")
    
    # Test compilation
    console.print("\n[bold]Testing compilation...[/bold]")
    start_time = time.time()
    
    try:
        # Test with ts-node
        cmd = ['npx', 'ts-node']
        if is_mastra:
            cmd.extend(['--transpile-only', '--skip-project'])
        
        cmd.append(str(file_path))
        
        env = {
            **os.environ,
            'NODE_ENV': 'production' if is_mastra else 'development',
            'TS_NODE_CACHE': 'true'
        }
        
        if verbose:
            console.print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute timeout for testing
            env=env
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            console.print(f"[green]✅ Compilation successful! (took {execution_time:.2f}s)[/green]")
            if verbose and result.stdout:
                console.print(f"Output: {result.stdout}")
        else:
            console.print(f"[red]❌ Compilation failed! (took {execution_time:.2f}s)[/red]")
            console.print(f"Error: {result.stderr}")
            if verbose and result.stdout:
                console.print(f"Output: {result.stdout}")
    
    except subprocess.TimeoutExpired:
        console.print(f"[red]⏰ Compilation timed out after 60 seconds[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error during compilation: {str(e)}[/red]")

def run_benchmarks():
    """Run performance benchmarks."""
    console.print("Running TypeScript performance benchmarks...")
    
    # Create a simple test file
    test_code = """
export function simpleFunction(input: string): string {
    return `Hello, ${input}!`;
}

export const testData = {
    message: "Test message",
    timestamp: Date.now()
};
"""
    
    with open('debug_test.ts', 'w') as f:
        f.write(test_code)
    
    try:
        # Benchmark 1: Simple compilation
        console.print("\n[bold]Benchmark 1: Simple TypeScript compilation[/bold]")
        start_time = time.time()
        
        result = subprocess.run(
            ['npx', 'ts-node', 'debug_test.ts'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        simple_time = time.time() - start_time
        console.print(f"Simple compilation: {simple_time:.2f}s")
        
        # Benchmark 2: With caching
        console.print("\n[bold]Benchmark 2: With TypeScript caching[/bold]")
        start_time = time.time()
        
        env = {
            **os.environ,
            'TS_NODE_CACHE': 'true',
            'NODE_ENV': 'production'
        }
        
        result = subprocess.run(
            ['npx', 'ts-node', '--transpile-only', 'debug_test.ts'],
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        cached_time = time.time() - start_time
        console.print(f"Cached compilation: {cached_time:.2f}s")
        
        # Show improvement
        if simple_time > 0:
            improvement = ((simple_time - cached_time) / simple_time) * 100
            console.print(f"Improvement: {improvement:.1f}%")
        
    except Exception as e:
        console.print(f"[red]❌ Benchmark failed: {str(e)}[/red]")
    finally:
        # Clean up
        try:
            os.remove('debug_test.ts')
        except:
            pass

def run_comprehensive_diagnosis():
    """Run comprehensive TypeScript environment diagnosis."""
    try:
        from kaizen.autofix.test.code_region import CodeRegionExecutor
        
        # Create a temporary executor for diagnosis
        temp_executor = CodeRegionExecutor(Path.cwd())
        
        # Run the comprehensive diagnosis
        diagnostics = temp_executor.diagnose_typescript_environment()
        
        # Display results in a table
        table = Table(title="TypeScript Environment Diagnosis")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        # Add diagnostic results
        for key, value in diagnostics.items():
            if key == 'issues':
                continue  # Handle issues separately
                
            if value is None:
                table.add_row(key.replace('_', ' ').title(), "❌ Not found", "Not available")
            elif isinstance(value, str) and value.startswith("OK"):
                table.add_row(key.replace('_', ' ').title(), "✅ Working", value)
            elif isinstance(value, str) and value.startswith("Failed"):
                table.add_row(key.replace('_', ' ').title(), "❌ Failed", value)
            elif isinstance(value, str) and value.startswith("Error"):
                table.add_row(key.replace('_', ' ').title(), "❌ Error", value)
            elif isinstance(value, str) and value.startswith("Timeout"):
                table.add_row(key.replace('_', ' ').title(), "⏰ Timeout", value)
            elif isinstance(value, str) and value.startswith("Partial"):
                table.add_row(key.replace('_', ' ').title(), "⚠️  Partial", value)
            elif isinstance(value, str) and value.startswith("Not installed"):
                table.add_row(key.replace('_', ' ').title(), "ℹ️  Not installed", value)
            else:
                table.add_row(key.replace('_', ' ').title(), "✅ Available", str(value))
        
        console.print(table)
        
        # Display issues if any
        if diagnostics.get('issues'):
            console.print(f"\n[bold red]Issues Found ({len(diagnostics['issues'])}):[/bold red]")
            for issue in diagnostics['issues']:
                console.print(f"  • {issue}")
            
            console.print(f"\n[bold]Recommendations:[/bold]")
            for issue in diagnostics['issues']:
                if "Node.js" in issue:
                    console.print("  • Install Node.js from https://nodejs.org/")
                elif "npm" in issue:
                    console.print("  • Install npm: npm comes with Node.js")
                elif "ts-node" in issue:
                    console.print("  • Install ts-node: npm install -g ts-node")
                elif "TypeScript" in issue:
                    console.print("  • Install TypeScript: npm install -g typescript")
                elif "network" in issue.lower():
                    console.print("  • Check your internet connection")
                    console.print("  • Check if you're behind a corporate firewall")
                    console.print("  • Try: npm config set registry https://registry.npmjs.org/")
                elif "compilation" in issue.lower():
                    console.print("  • Clear npm cache: npm cache clean --force")
                    console.print("  • Reinstall TypeScript dependencies")
                    console.print("  • Check for conflicting TypeScript versions")
                elif "@ai-sdk/google" in issue:
                    console.print("  • Install @ai-sdk/google: npm install @ai-sdk/google")
                    console.print("  • This is required for Mastra agents using Google AI models")
                elif "@mastra/core" in issue:
                    console.print("  • Install @mastra/core: npm install @mastra/core")
                    console.print("  • This is the core Mastra framework")
                elif "Mastra dependencies" in issue:
                    console.print("  • Install both dependencies: npm install @mastra/core @ai-sdk/google")
                    console.print("  • These are required for Mastra AI agents")
        else:
            console.print(f"\n[bold green]✅ No issues found in TypeScript environment![/bold green]")
            
    except Exception as e:
        console.print(f"[red]❌ Diagnosis failed: {str(e)}[/red]")
        console.print(f"[dim]This might indicate a fundamental issue with the TypeScript setup.[/dim]")

if __name__ == '__main__':
    debug_typescript() 