"""GitHub access diagnostic command for detailed troubleshooting."""

import click
import logging
import os
import requests
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel

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
logger = logging.getLogger("kaizen.github-diagnose")

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), help='Test configuration file (optional)')
@click.option('--repo', help='Repository name (owner/repo)')
@click.option('--token', help='GitHub token to test (optional, uses GITHUB_TOKEN env var if not provided)')
def diagnose_github_access(config: str, repo: str, token: str) -> None:
    """Comprehensive GitHub access diagnostic for troubleshooting organization and repository issues.
    
    This command provides detailed diagnostics for GitHub access issues, especially
    for organization repositories and "not all refs are readable" errors.
    
    Args:
        config: Path to test configuration file (optional)
        repo: Repository name in format owner/repo (optional if config provided)
        token: GitHub token to test (optional)
        
    Example:
        >>> diagnose_github_access --config test_config.yaml
        >>> diagnose_github_access --repo owner/repo
        >>> diagnose_github_access --repo owner/repo --token ghp_xxx
    """
    console = Console()
    
    try:
        # Load environment variables
        load_environment_variables()
        
        # Get token
        github_token = token or os.environ.get('GITHUB_TOKEN')
        if not github_token:
            console.print("[bold red]Error: No GitHub token provided[/bold red]")
            console.print("Please provide a token with --token or set GITHUB_TOKEN environment variable")
            return
        
        # Determine repository information
        if config:
            # Load from config file
            config_manager = ConfigurationManager()
            config_result = config_manager.load_configuration(Path(config))
            
            if not config_result.is_success:
                console.print(f"[bold red]Configuration error: {config_result.error}[/bold red]")
                return
            
            config_obj = config_result.value
            
            # Create PR manager to get repository info
            from kaizen.autofix.pr.manager import PRManager
            pr_manager = PRManager(config_obj.__dict__)
            repo_owner, repo_name = pr_manager._get_repository_info()
            repo_full_name = f"{repo_owner}/{repo_name}"
            
        elif repo:
            # Use provided repository
            repo_full_name = repo
            if '/' not in repo:
                console.print("[bold red]Error: Repository must be in format owner/repo[/bold red]")
                return
            repo_owner, repo_name = repo.split('/', 1)
            
        else:
            console.print("[bold red]Error: Either --config or --repo must be provided[/bold red]")
            return
        
        console.print(f"\n[bold blue]GitHub Access Diagnostic for: {repo_full_name}[/bold blue]")
        console.print("=" * 60)
        
        # Run comprehensive diagnostics
        _run_token_diagnostics(console, github_token)
        _run_user_diagnostics(console, github_token)
        _run_organization_diagnostics(console, github_token, repo_owner)
        _run_repository_diagnostics(console, github_token, repo_owner, repo_name)
        _run_branch_diagnostics(console, github_token, repo_owner, repo_name)
        _run_pr_diagnostics(console, github_token, repo_owner, repo_name)
        
        # Provide summary and recommendations
        _provide_summary_and_recommendations(console, repo_full_name)
        
    except Exception as e:
        console.print(f"[bold red]Error during diagnostic: {str(e)}[/bold red]")
        logger.exception("GitHub diagnostic failed")

def _run_token_diagnostics(console: Console, token: str) -> None:
    """Run token-specific diagnostics."""
    console.print("\n[bold]1. Token Diagnostics[/bold]")
    
    # Check token format
    if token.startswith('ghp_'):
        console.print("  [green]✓ Token format: Personal Access Token (Classic)[/green]")
    elif token.startswith('gho_'):
        console.print("  [green]✓ Token format: Fine-grained Personal Access Token[/green]")
    elif token.startswith('ghu_'):
        console.print("  [green]✓ Token format: User-to-Server Token[/green]")
    else:
        console.print("  [yellow]⚠ Token format: Unknown (may be a custom token)[/yellow]")
    
    # Test basic API access
    try:
        response = requests.get(
            'https://api.github.com/user',
            headers={'Authorization': f'token {token}'},
            timeout=10
        )
        if response.status_code == 200:
            user_data = response.json()
            console.print(f"  [green]✓ Token valid: Authenticated as {user_data.get('login', 'Unknown')}[/green]")
        else:
            console.print(f"  [red]✗ Token invalid: {response.status_code} - {response.text}[/red]")
            return
    except Exception as e:
        console.print(f"  [red]✗ Token test failed: {str(e)}[/red]")
        return

def _run_user_diagnostics(console: Console, token: str) -> None:
    """Run user-specific diagnostics."""
    console.print("\n[bold]2. User Diagnostics[/bold]")
    
    try:
        # Get user information
        response = requests.get(
            'https://api.github.com/user',
            headers={'Authorization': f'token {token}'},
            timeout=10
        )
        user_data = response.json()
        
        console.print(f"  [green]✓ User: {user_data.get('login', 'Unknown')}[/green]")
        console.print(f"  [green]✓ User ID: {user_data.get('id', 'Unknown')}[/green]")
        console.print(f"  [green]✓ Account type: {user_data.get('type', 'Unknown')}[/green]")
        
        # Get user organizations
        org_response = requests.get(
            'https://api.github.com/user/orgs',
            headers={'Authorization': f'token {token}'},
            timeout=10
        )
        if org_response.status_code == 200:
            orgs = org_response.json()
            if orgs:
                console.print(f"  [green]✓ Organization memberships: {len(orgs)}[/green]")
                for org in orgs[:3]:  # Show first 3
                    console.print(f"    • {org.get('login', 'Unknown')} (Role: {org.get('role', 'Unknown')})")
                if len(orgs) > 3:
                    console.print(f"    • ... and {len(orgs) - 3} more")
            else:
                console.print("  [yellow]⚠ No organization memberships[/yellow]")
        else:
            console.print(f"  [red]✗ Failed to get organizations: {org_response.status_code}[/red]")
            
    except Exception as e:
        console.print(f"  [red]✗ User diagnostics failed: {str(e)}[/red]")

def _run_organization_diagnostics(console: Console, token: str, org_name: str) -> None:
    """Run organization-specific diagnostics."""
    console.print(f"\n[bold]3. Organization Diagnostics: {org_name}[/bold]")
    
    try:
        # Check if it's an organization
        org_response = requests.get(
            f'https://api.github.com/orgs/{org_name}',
            headers={'Authorization': f'token {token}'},
            timeout=10
        )
        
        if org_response.status_code == 200:
            org_data = org_response.json()
            console.print(f"  [green]✓ Organization exists: {org_data.get('name', org_name)}[/green]")
            console.print(f"  [green]✓ Organization type: {org_data.get('type', 'Unknown')}[/green]")
            
            # Check membership
            membership_response = requests.get(
                f'https://api.github.com/orgs/{org_name}/memberships/{org_name}',
                headers={'Authorization': f'token {token}'},
                timeout=10
            )
            
            if membership_response.status_code == 200:
                membership_data = membership_response.json()
                role = membership_data.get('role', 'Unknown')
                state = membership_data.get('state', 'Unknown')
                console.print(f"  [green]✓ Organization member: Yes (Role: {role}, State: {state})[/green]")
            elif membership_response.status_code == 404:
                console.print("  [red]✗ Organization member: No[/red]")
                console.print("  [yellow]⚠ This is likely the root cause of your access issues[/yellow]")
            else:
                console.print(f"  [yellow]⚠ Membership check failed: {membership_response.status_code}[/yellow]")
                
        elif org_response.status_code == 404:
            console.print("  [dim]Organization: Not found (likely a user account)[/dim]")
        else:
            console.print(f"  [red]✗ Organization check failed: {org_response.status_code}[/red]")
            
    except Exception as e:
        console.print(f"  [red]✗ Organization diagnostics failed: {str(e)}[/red]")

def _run_repository_diagnostics(console: Console, token: str, owner: str, repo: str) -> None:
    """Run repository-specific diagnostics."""
    console.print(f"\n[bold]4. Repository Diagnostics: {owner}/{repo}[/bold]")
    
    try:
        # Get repository information
        repo_response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}',
            headers={'Authorization': f'token {token}'},
            timeout=10
        )
        
        if repo_response.status_code == 200:
            repo_data = repo_response.json()
            console.print(f"  [green]✓ Repository accessible: {repo_data.get('full_name', 'Unknown')}[/green]")
            console.print(f"  [green]✓ Repository type: {'Private' if repo_data.get('private') else 'Public'}[/green]")
            console.print(f"  [green]✓ Default branch: {repo_data.get('default_branch', 'Unknown')}[/green]")
            
            # Check permissions
            permissions = repo_data.get('permissions', {})
            if permissions:
                console.print("  [green]✓ Repository permissions:[/green]")
                for perm, value in permissions.items():
                    status = "✓" if value else "✗"
                    color = "green" if value else "red"
                    console.print(f"    [{color}]{status} {perm}: {value}[/{color}]")
            
            # Check collaborator status
            collab_response = requests.get(
                f'https://api.github.com/repos/{owner}/{repo}/collaborators/{owner}',
                headers={'Authorization': f'token {token}'},
                timeout=10
            )
            
            if collab_response.status_code == 200:
                collab_data = collab_response.json()
                permissions = collab_data.get('permissions', {})
                console.print("  [green]✓ Collaborator status: Confirmed[/green]")
                console.print(f"  [green]✓ Collaborator permissions: {permissions}[/green]")
            elif collab_response.status_code == 404:
                console.print("  [yellow]⚠ Collaborator status: Not a collaborator[/yellow]")
            else:
                console.print(f"  [yellow]⚠ Collaborator check failed: {collab_response.status_code}[/yellow]")
                
        elif repo_response.status_code == 404:
            console.print("  [red]✗ Repository not found or not accessible[/red]")
        elif repo_response.status_code == 403:
            console.print("  [red]✗ Repository access forbidden (insufficient permissions)[/red]")
        else:
            console.print(f"  [red]✗ Repository check failed: {repo_response.status_code}[/red]")
            
    except Exception as e:
        console.print(f"  [red]✗ Repository diagnostics failed: {str(e)}[/red]")

def _run_branch_diagnostics(console: Console, token: str, owner: str, repo: str) -> None:
    """Run branch-specific diagnostics."""
    console.print(f"\n[bold]5. Branch Diagnostics[/bold]")
    
    try:
        # Get current branch (this would need git info, but we'll test main)
        branches_to_test = ['main', 'master']
        
        for branch in branches_to_test:
            branch_response = requests.get(
                f'https://api.github.com/repos/{owner}/{repo}/branches/{branch}',
                headers={'Authorization': f'token {token}'},
                timeout=10
            )
            
            if branch_response.status_code == 200:
                branch_data = branch_response.json()
                console.print(f"  [green]✓ Branch '{branch}' accessible: {branch_data.get('name', branch)}[/green]")
                console.print(f"  [green]✓ Branch SHA: {branch_data.get('commit', {}).get('sha', 'Unknown')[:8]}...[/green]")
                
                # Check protection
                protection_response = requests.get(
                    f'https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection',
                    headers={'Authorization': f'token {token}'},
                    timeout=10
                )
                
                if protection_response.status_code == 200:
                    protection_data = protection_response.json()
                    console.print(f"  [yellow]⚠ Branch '{branch}' has protection rules[/yellow]")
                    if protection_data.get('required_status_checks'):
                        console.print("    • Status checks required")
                    if protection_data.get('enforce_admins'):
                        console.print("    • Admin enforcement enabled")
                    if protection_data.get('restrictions'):
                        console.print("    • Push restrictions enabled")
                elif protection_response.status_code == 404:
                    console.print(f"  [green]✓ Branch '{branch}' has no protection rules[/green]")
                else:
                    console.print(f"  [yellow]⚠ Branch '{branch}' protection check failed: {protection_response.status_code}[/yellow]")
                    
                break  # Found a working branch
            elif branch_response.status_code == 404:
                console.print(f"  [yellow]⚠ Branch '{branch}' not found[/yellow]")
            elif branch_response.status_code == 403:
                console.print(f"  [red]✗ Branch '{branch}' access forbidden[/red]")
            else:
                console.print(f"  [red]✗ Branch '{branch}' check failed: {branch_response.status_code}[/red]")
        else:
            console.print("  [red]✗ No accessible branches found[/red]")
            
    except Exception as e:
        console.print(f"  [red]✗ Branch diagnostics failed: {str(e)}[/red]")

def _run_pr_diagnostics(console: Console, token: str, owner: str, repo: str) -> None:
    """Run pull request diagnostics."""
    console.print(f"\n[bold]6. Pull Request Diagnostics[/bold]")
    
    try:
        # Test PR listing (read permissions)
        pr_response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=1',
            headers={'Authorization': f'token {token}'},
            timeout=10
        )
        
        if pr_response.status_code == 200:
            prs = pr_response.json()
            console.print(f"  [green]✓ PR read access: Confirmed ({len(prs)} PRs accessible)[/green]")
            
            # Test PR creation (this will fail but show the exact error)
            test_pr_data = {
                'title': 'Test PR - Diagnostic',
                'head': 'test-branch',
                'base': 'main',
                'body': 'This is a diagnostic test PR that will fail.'
            }
            
            create_pr_response = requests.post(
                f'https://api.github.com/repos/{owner}/{repo}/pulls',
                headers={
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json'
                },
                json=test_pr_data,
                timeout=10
            )
            
            if create_pr_response.status_code == 422:
                error_data = create_pr_response.json()
                console.print(f"  [yellow]⚠ PR creation test: Expected failure (422)[/yellow]")
                console.print(f"  [yellow]⚠ Error message: {error_data.get('message', 'Unknown')}[/yellow]")
                
                # Check for specific error patterns
                errors = error_data.get('errors', [])
                for error in errors:
                    if 'not all refs are readable' in error.get('message', ''):
                        console.print("  [red]✗ 'not all refs are readable' error detected[/red]")
                        console.print("  [yellow]⚠ This is the specific error you're encountering[/yellow]")
                    elif 'head' in error.get('field', ''):
                        console.print("  [yellow]⚠ Head branch issue detected[/yellow]")
                    elif 'base' in error.get('field', ''):
                        console.print("  [yellow]⚠ Base branch issue detected[/yellow]")
                        
            elif create_pr_response.status_code == 403:
                console.print("  [red]✗ PR creation forbidden (insufficient permissions)[/red]")
            else:
                console.print(f"  [yellow]⚠ PR creation test: Unexpected response {create_pr_response.status_code}[/yellow]")
                
        elif pr_response.status_code == 403:
            console.print("  [red]✗ PR read access forbidden[/red]")
        else:
            console.print(f"  [red]✗ PR diagnostics failed: {pr_response.status_code}[/red]")
            
    except Exception as e:
        console.print(f"  [red]✗ PR diagnostics failed: {str(e)}[/red]")

def _provide_summary_and_recommendations(console: Console, repo_full_name: str) -> None:
    """Provide summary and specific recommendations."""
    console.print("\n" + "=" * 60)
    console.print("[bold blue]Summary and Recommendations[/bold blue]")
    console.print("=" * 60)
    
    console.print("\n[bold]Common Solutions for 'not all refs are readable':[/bold]")
    
    solutions = [
        "1. [bold]Organization Membership[/bold]: Request full membership (not just outside collaborator)",
        "2. [bold]SSO Authorization[/bold]: Enable SSO for your token in organization settings",
        "3. [bold]Repository Access[/bold]: Request collaborator access to the specific repository",
        "4. [bold]Branch Protection[/bold]: Ask admins to check branch protection rules",
        "5. [bold]Token Scopes[/bold]: Ensure token has 'repo' scope (not just 'public_repo')",
        "6. [bold]Manual Test[/bold]: Try creating a PR manually in GitHub web interface"
    ]
    
    for solution in solutions:
        console.print(f"  {solution}")
    
    console.print(f"\n[bold]Next Steps for {repo_full_name}:[/bold]")
    console.print("1. Run the diagnostic commands shown above")
    console.print("2. Contact organization administrators if membership issues detected")
    console.print("3. Check repository settings and branch protection rules")
    console.print("4. Verify your token has SSO authorization if required")
    console.print("5. Test manual PR creation in GitHub web interface")
    
    console.print(f"\n[bold]For more detailed help:[/bold]")
    console.print("• Read the organization access troubleshooting guide:")
    console.print("  docs/organization-access-troubleshooting.md")
    console.print("• Run the GitHub access test:")
    console.print(f"  kaizen test-github-access --repo {repo_full_name}")
    console.print("• Check GitHub documentation on organization permissions") 