"""GitHub access testing command for Kaizen CLI."""

import click
import logging
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
import os

from .config import ConfigurationManager
from .errors import ConfigurationError
from ..utils.env_setup import load_environment_variables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("kaizen.github-test")

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), help='Test configuration file (optional)')
@click.option('--repo', help='Repository name (owner/repo)')
@click.option('--base-branch', default='main', help='Base branch for testing')
def test_github_access(config: str, repo: str, base_branch: str) -> None:
    """Test GitHub access and permissions for private repositories.
    
    This command helps diagnose GitHub token permission issues, especially for private repositories.
    
    Args:
        config: Path to test configuration file (optional)
        repo: Repository name in format owner/repo (optional if config provided)
        base_branch: Base branch to test access to
        
    Example:
        >>> test_github_access --config test_config.yaml
        >>> test_github_access --repo owner/repo --base-branch main
    """
    console = Console()
    
    try:
        # Load environment variables first
        console.print("[dim]Loading environment variables...[/dim]")
        loaded_files = load_environment_variables()
        if loaded_files:
            console.print(f"[dim]Loaded environment from: {', '.join(loaded_files.keys())}[/dim]")
        else:
            console.print("[dim]No .env files found, using system environment variables[/dim]")
        
        # Check if GITHUB_TOKEN is available
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            console.print("\n[bold red]GITHUB_TOKEN not found in environment variables[/bold red]")
            console.print("\n[bold]Possible solutions:[/bold]")
            console.print("1. Create a .env file in your project root with:")
            console.print("   GITHUB_TOKEN=your_github_token_here")
            console.print("2. Set the environment variable directly:")
            console.print("   export GITHUB_TOKEN=your_github_token_here")
            console.print("3. Check if your .env file is in the correct location")
            console.print("4. Restart your terminal after creating/modifying .env files")
            console.print("\n[bold]For more help, run:[/bold]")
            console.print("   kaizen setup check-env --features github")
            return
        
        # Show token status (without exposing the actual token)
        token_preview = github_token[:8] + "..." if len(github_token) > 8 else "***"
        console.print(f"[dim]GitHub token found: {token_preview}[/dim]")
        
        # Determine repository information
        if config:
            # Load from config file
            config_manager = ConfigurationManager()
            config_result = config_manager.load_configuration(Path(config))
            
            if not config_result.is_success:
                console.print(f"[bold red]Configuration error: {config_result.error}[/bold red]")
                return
            
            config_obj = config_result.value
            base_branch = config_obj.base_branch
            
            # Create PR manager to test access
            from kaizen.autofix.pr.manager import PRManager
            pr_manager = PRManager(config_obj.__dict__)
            
        elif repo:
            # Use provided repository
            from kaizen.autofix.pr.manager import PRManager
            config_dict = {
                'base_branch': base_branch,
                'auto_commit_changes': True
            }
            pr_manager = PRManager(config_dict)
            
        else:
            console.print("[bold red]Error: Either --config or --repo must be provided[/bold red]")
            return
        
        # Test GitHub access
        console.print("\n[bold blue]Testing GitHub Access and Permissions...[/bold blue]")
        access_result = pr_manager.test_github_access()
        
        # Display results
        _display_access_results(console, access_result)
        
    except Exception as e:
        console.print(f"[bold red]Error testing GitHub access: {str(e)}[/bold red]")
        logger.exception("GitHub access test failed")

def _display_access_results(console: Console, access_result: dict) -> None:
    """Display GitHub access test results in a user-friendly format."""
    
    overall_status = access_result['overall_status']
    
    # Overall status
    if overall_status == 'full_access':
        console.print("\n[bold green]✓ GitHub Access Test: PASSED[/bold green]")
        console.print("All permissions are correctly configured for PR creation.")
    elif overall_status == 'limited_branch_access_private':
        console.print("\n[bold yellow]⚠ GitHub Access Test: PARTIAL ACCESS (Private Repository)[/bold yellow]")
        console.print("Your token can access the repository but branch-level access is limited.")
        console.print("This is often normal for private repositories and PR creation may still work.")
    elif overall_status == 'branch_listing_limited':
        console.print("\n[bold yellow]⚠ GitHub Access Test: BRANCH LISTING LIMITED[/bold yellow]")
        console.print("Your token has correct permissions but cannot list branches.")
        console.print("This is a common limitation with personal access tokens on private repositories.")
        console.print("PR creation should still work despite this limitation.")
    elif overall_status == 'org_membership_required':
        console.print("\n[bold red]✗ GitHub Access Test: ORGANIZATION MEMBERSHIP REQUIRED[/bold red]")
        console.print("You are not a member of the organization that owns the repository.")
        console.print("Organization membership is required to create pull requests.")
    elif overall_status == 'org_limited_access':
        console.print("\n[bold red]✗ GitHub Access Test: ORGANIZATION LIMITED ACCESS[/bold red]")
        console.print("You are an outside collaborator with limited permissions.")
        console.print("Full organization membership may be required for PR creation.")
    else:
        console.print(f"\n[bold red]✗ GitHub Access Test: FAILED ({overall_status})[/bold red]")
        console.print("There are permission issues that need to be resolved.")
    
    # Detailed results
    console.print("\n[bold]Detailed Access Results:[/bold]")
    
    # Repository access
    repo = access_result['repository']
    if repo.get('accessible'):
        privacy_status = "Private" if repo.get('private') else "Public"
        console.print(f"  [green]✓ Repository Access: {repo.get('full_name', 'Unknown')} ({privacy_status})[/green]")
    else:
        console.print(f"  [red]✗ Repository Access: {repo.get('error', 'Unknown error')}[/red]")
    
    # Organization access
    org = access_result.get('organization')
    if org:
        if org.get('is_organization'):
            if org.get('is_member'):
                role = org.get('role', 'Unknown')
                state = org.get('state', 'Unknown')
                console.print(f"  [green]✓ Organization: {org.get('org_login', 'Unknown')} (Role: {role}, State: {state})[/green]")
            else:
                console.print(f"  [red]✗ Organization: {org.get('org_login', 'Unknown')} (Not a member)[/red]")
        else:
            console.print(f"  [dim]Organization: User-owned repository[/dim]")
    
    # Current branch access
    current_branch = access_result['current_branch']
    if current_branch.get('accessible'):
        console.print(f"  [green]✓ Current Branch: {current_branch.get('branch_name', 'Unknown')}[/green]")
    else:
        console.print(f"  [red]✗ Current Branch: {current_branch.get('error', 'Unknown error')}[/red]")
    
    # Base branch access
    base_branch = access_result['base_branch']
    if base_branch.get('accessible'):
        console.print(f"  [green]✓ Base Branch: {base_branch.get('branch_name', 'Unknown')}[/green]")
    else:
        console.print(f"  [red]✗ Base Branch: {base_branch.get('error', 'Unknown error')}[/red]")
    
    # PR permissions
    pr_perms = access_result['pr_permissions']
    if pr_perms.get('can_read'):
        console.print("  [green]✓ Pull Request Permissions: Read access confirmed[/green]")
    else:
        console.print(f"  [red]✗ Pull Request Permissions: {pr_perms.get('error', 'Unknown error')}[/red]")
    
    # Collaborator status
    collaborator = access_result.get('collaborator_status')
    if collaborator:
        if collaborator.get('is_collaborator'):
            permissions = collaborator.get('permission', {})
            console.print(f"  [green]✓ Collaborator Status: Confirmed (Permissions: {permissions})[/green]")
        else:
            console.print(f"  [yellow]⚠ Collaborator Status: Not a collaborator[/yellow]")
    
    # Recommendations
    recommendations = access_result.get('recommendations', [])
    if recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for i, rec in enumerate(recommendations, 1):
            console.print(f"  {i}. {rec}")
    
    # Token scope information
    console.print("\n[bold]GitHub Token Requirements:[/bold]")
    console.print("For private repositories, your GITHUB_TOKEN needs:")
    console.print("  • [bold]repo[/bold] scope (full repository access)")
    console.print("  • [bold]Contents[/bold] read permission")
    console.print("  • [bold]Pull requests[/bold] write permission")
    console.print("\nFor public repositories, [bold]public_repo[/bold] scope is sufficient.")
    
    # Organization-specific guidance
    if org and org.get('is_organization'):
        console.print("\n[bold]Organization-Specific Requirements:[/bold]")
        console.print("For organization repositories, you may also need:")
        console.print("  • [bold]Organization membership[/bold] (not just outside collaborator)")
        console.print("  • [bold]SSO authorization[/bold] for your token")
        console.print("  • [bold]Repository-specific permissions[/bold]")
        console.print("  • [bold]Branch protection rule exceptions[/bold]")
    
    # Next steps
    if overall_status != 'full_access':
        console.print("\n[bold yellow]Next Steps:[/bold yellow]")
        if overall_status == 'org_membership_required':
            console.print("1. Contact organization administrators to request membership")
            console.print("2. Check if your token needs SSO authorization")
            console.print("3. Verify organization settings allow your access level")
            console.print("4. Consider requesting repository-specific collaborator access")
        elif overall_status == 'org_limited_access':
            console.print("1. Request full organization membership (not just outside collaborator)")
            console.print("2. Check organization settings for outside collaborator restrictions")
            console.print("3. Verify your role allows PR creation")
            console.print("4. Contact organization admins for permission upgrades")
        else:
            console.print("1. Check your GITHUB_TOKEN environment variable")
            console.print("2. Verify the token has the correct scopes")
            console.print("3. Ensure you have access to the repository")
            console.print("4. Try running this test again after fixing permissions")
    else:
        console.print("\n[bold green]You're all set! PR creation should work correctly.[/bold green]")

if __name__ == "__main__":
    test_github_access() 