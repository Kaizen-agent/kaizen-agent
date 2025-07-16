"""User confirmation management utilities.

This module provides utilities for handling user confirmations during test execution,
including auto-fix and pull request creation confirmations.
"""

import os
from typing import Any, Dict, Optional
import click
from rich.console import Console


class ConfirmationManager:
    """Manages user confirmations for test operations."""
    
    def __init__(self, console: Console):
        """Initialize the confirmation manager.
        
        Args:
            console: Rich console for output
        """
        self.console = console
    
    def confirm_auto_fix(self, config: Any, max_retries: int, no_confirm: bool) -> bool:
        """Confirm auto-fix operation with user.
        
        Args:
            config: Test configuration object
            max_retries: Maximum number of retry attempts
            no_confirm: Whether to skip confirmation prompts
            
        Returns:
            True if auto-fix should proceed, False otherwise
        """
        self.console.print("\n[bold yellow]⚠ Auto-fix Warning[/bold yellow]")
        self.console.print("Auto-fix will attempt to modify your code files to fix failing tests.")
        self.console.print("This may change your existing code and could potentially introduce new issues.")
        self.console.print(f"Maximum retry attempts: {max_retries}")
        self.console.print("\n[bold]Files that may be modified:[/bold]")
        
        # Show files that will be tested/modified
        if hasattr(config, 'files_to_fix') and config.files_to_fix:
            for file_path in config.files_to_fix:
                self.console.print(f"  • {file_path}")
        else:
            self.console.print("  • Files specified in test configuration")
        
        if no_confirm:
            self.console.print("✓ Auto-fix confirmed (--no-confirm flag used)")
            return True
        elif not click.confirm("\n[bold]Do you want to proceed with auto-fix?[/bold]"):
            self.console.print("[dim]Auto-fix cancelled by user[/dim]")
            return False
        else:
            self.console.print("✓ Auto-fix confirmed - proceeding with automatic fixes")
            return True
    
    def confirm_pr_creation(self, base_branch: str, pr_strategy: str, no_confirm: bool) -> bool:
        """Confirm pull request creation with user.
        
        Args:
            base_branch: Base branch for pull request
            pr_strategy: Strategy for when to create PRs
            no_confirm: Whether to skip confirmation prompts
            
        Returns:
            True if PR creation should proceed, False otherwise
        """
        self.console.print("\n[bold yellow]⚠ Pull Request Creation Warning[/bold yellow]")
        self.console.print("This will create a pull request on GitHub with the fixes applied.")
        self.console.print(f"Base branch: {base_branch}")
        self.console.print(f"PR strategy: {pr_strategy}")
        self.console.print("\n[bold]What will happen:[/bold]")
        self.console.print("  • A new branch will be created with your fixes")
        self.console.print("  • A pull request will be opened against the base branch")
        self.console.print("  • You'll need to review and merge the PR manually")
        
        if no_confirm:
            self.console.print("✓ PR creation confirmed (--no-confirm flag used)")
            return True
        elif not click.confirm("\n[bold]Do you want to proceed with PR creation?[/bold]"):
            self.console.print("[dim]PR creation cancelled by user[/dim]")
            return False
        else:
            self.console.print("✓ PR creation confirmed - will create pull request after fixes")
            return True
    
    def check_github_token(self, create_pr: bool, no_confirm: bool) -> bool:
        """Check if GitHub token is available and handle missing token.
        
        Args:
            create_pr: Whether PR creation is enabled
            no_confirm: Whether to skip confirmation prompts
            
        Returns:
            True if GitHub token is available or user wants to continue, False otherwise
        """
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            self.console.print("✗ GITHUB_TOKEN not found in environment variables")
            self.console.print("\n[bold]Possible solutions:[/bold]")
            self.console.print("1. Create a .env file in your project root with:")
            self.console.print("   GITHUB_TOKEN=your_github_token_here")
            self.console.print("2. Set the environment variable directly:")
            self.console.print("   export GITHUB_TOKEN=your_github_token_here")
            self.console.print("3. Check if your .env file is in the correct location")
            self.console.print("4. Restart your terminal after creating/modifying .env files")
            self.console.print("\n[bold]For more help, run:[/bold]")
            self.console.print("   kaizen setup check-env --features github")
            
            if create_pr:
                self.console.print("\n[bold yellow]Warning: PR creation will fail without GITHUB_TOKEN[/bold yellow]")
                if not no_confirm and not click.confirm("Continue with test execution?"):
                    return False
            else:
                return False
        
        # Show token status (without exposing the actual token)
        token_preview = github_token[:8] + "..." if len(github_token) > 8 else "***"
        self.console.print(f"✓ GitHub token found: {token_preview}")
        return True
    
    def test_github_access(self, config: Any, create_pr: bool, no_confirm: bool, verbose: bool) -> bool:
        """Test GitHub access and permissions.
        
        Args:
            config: Test configuration object
            create_pr: Whether PR creation is enabled
            no_confirm: Whether to skip confirmation prompts
            verbose: Whether to show detailed output
            
        Returns:
            True if GitHub access test passes or user wants to continue, False otherwise
        """
        try:
            from kaizen.autofix.pr.manager import PRManager
            pr_manager = PRManager(config.__dict__)
            access_result = pr_manager.test_github_access()
            
            if access_result['overall_status'] == 'full_access':
                self.console.print("✓ GitHub access test passed")
                return True
            elif access_result['overall_status'] == 'limited_branch_access_private':
                self.console.print("[bold yellow]⚠ GitHub access test: Partial access (Private Repository)[/bold yellow]")
                self.console.print("Branch-level access is limited, but PR creation may still work.")
                return True
            else:
                self.console.print(f"✗ GitHub access test failed: {access_result['overall_status']}")
                
                # Display detailed results only in verbose mode
                if verbose:
                    self._display_detailed_access_results(access_result)
                
                if create_pr:
                    if access_result['overall_status'] == 'limited_branch_access_private':
                        self.console.print("\n[bold yellow]Note: Limited branch access detected for private repository. PR creation will be attempted but may fail.[/bold yellow]")
                        if not no_confirm and not click.confirm("Continue with test execution?"):
                            return False
                    else:
                        self.console.print("\n[bold yellow]Warning: PR creation may fail due to access issues.[/bold yellow]")
                        if not no_confirm and not click.confirm("Continue with test execution?"):
                            return False
                
                return True
                
        except Exception as e:
            self.console.print(f"✗ GitHub access test failed: {str(e)}")
            if create_pr:
                self.console.print("[bold yellow]Warning: PR creation may fail due to access issues.[/bold yellow]")
                if not no_confirm and not click.confirm("Continue with test execution?"):
                    return False
            return True
    
    def _display_detailed_access_results(self, access_result: Dict[str, Any]) -> None:
        """Display detailed GitHub access test results.
        
        Args:
            access_result: Results from GitHub access test
        """
        self.console.print("\n[bold]Access Test Results:[/bold]")
        
        # Repository access
        repo = access_result['repository']
        if repo.get('accessible'):
            self.console.print(f"  [green]✓ Repository: {repo.get('full_name', 'Unknown')} (Private: {repo.get('private', False)})[/green]")
        else:
            self.console.print(f"  [red]✗ Repository: {repo.get('error', 'Unknown error')}[/red]")
        
        # Branch access
        current_branch = access_result['current_branch']
        if current_branch.get('accessible'):
            self.console.print(f"  [green]✓ Current branch: {current_branch.get('branch_name', 'Unknown')}[/green]")
        else:
            self.console.print(f"  [red]✗ Current branch: {current_branch.get('error', 'Unknown error')}[/red]")
        
        base_branch = access_result['base_branch']
        if base_branch.get('accessible'):
            self.console.print(f"  [green]✓ Base branch: {base_branch.get('branch_name', 'Unknown')}[/green]")
        else:
            self.console.print(f"  [red]✗ Base branch: {base_branch.get('error', 'Unknown error')}[/red]")
        
        # PR permissions
        pr_perms = access_result['pr_permissions']
        if pr_perms.get('can_read'):
            self.console.print("  [green]✓ PR permissions: Read access confirmed[/green]")
        else:
            self.console.print(f"  [red]✗ PR permissions: {pr_perms.get('error', 'Unknown error')}[/red]")
        
        # Display recommendations
        self.console.print("\n[bold]Recommendations:[/bold]")
        for rec in access_result.get('recommendations', []):
            self.console.print(f"  • {rec}")
    
    def confirm_auto_fix_after_failure(self, test_result: Any, no_confirm: bool) -> bool:
        """Confirm auto-fix after test failure.
        
        Args:
            test_result: Test result object
            no_confirm: Whether to skip confirmation prompts
            
        Returns:
            True if auto-fix should proceed, False otherwise
        """
        self.console.print("\n[bold yellow]⚠ Auto-fix Confirmation[/bold yellow]")
        self.console.print("Tests have failed. Auto-fix will now attempt to fix the failing tests.")
        self.console.print("This will modify your code files and may introduce changes.")
        
        # Show a brief summary of what failed (if available)
        try:
            if test_result.unified_result:
                failed_tests = [tc for tc in test_result.unified_result.test_cases if tc.status.value in ['failed', 'error']]
                if failed_tests:
                    self.console.print(f"\n[bold]Failed test cases ({len(failed_tests)}):[/bold]")
                    for tc in failed_tests[:3]:  # Show first 3 failed tests
                        self.console.print(f"  • {tc.name}")
                    if len(failed_tests) > 3:
                        self.console.print(f"  • ... and {len(failed_tests) - 3} more")
        except Exception as e:
            self.console.print(f"[dim]Could not display failed test summary: {str(e)}[/dim]")
        
        if no_confirm:
            self.console.print("✓ Auto-fix confirmed (--no-confirm flag used)")
            return True
        elif not click.confirm("\n[bold]Do you want to proceed with auto-fix?[/bold]"):
            self.console.print("[dim]Auto-fix cancelled by user after seeing test results[/dim]")
            return False
        else:
            self.console.print("✓ Proceeding with auto-fix to resolve failing tests")
            return True
    
    def confirm_pr_creation_after_auto_fix(self, test_result: Any, base_branch: str, pr_strategy: str, no_confirm: bool) -> bool:
        """Confirm PR creation after auto-fix completion.
        
        Args:
            test_result: Test result object
            base_branch: Base branch for pull request
            pr_strategy: Strategy for when to create PRs
            no_confirm: Whether to skip confirmation prompts
            
        Returns:
            True if PR creation should proceed, False otherwise
        """
        self.console.print("\n[bold yellow]⚠ Pull Request Creation Confirmation[/bold yellow]")
        self.console.print("Auto-fix has been completed. A pull request will now be created with the fixes.")
        self.console.print(f"Base branch: {base_branch}")
        self.console.print(f"PR strategy: {pr_strategy}")
        
        # Show auto-fix summary
        if test_result.test_attempts:
            self.console.print(f"\n[bold]Auto-fix summary:[/bold]")
            self.console.print(f"  • Attempts made: {len(test_result.test_attempts)}")
            
            # Count successful fixes
            successful_fixes = sum(1 for attempt in test_result.test_attempts 
                                 if attempt.get('status') == 'success')
            self.console.print(f"  • Successful fixes: {successful_fixes}")
            
            # Show what was fixed
            try:
                if test_result.unified_result:
                    fixed_tests = [tc for tc in test_result.unified_result.test_cases 
                                 if tc.status.value == 'passed']
                    if fixed_tests:
                        self.console.print(f"  • Tests now passing: {len(fixed_tests)}")
            except Exception as e:
                self.console.print(f"[dim]Could not display fixed test summary: {str(e)}[/dim]")
        
        if no_confirm:
            self.console.print("✓ PR creation confirmed (--no-confirm flag used)")
            return True
        elif not click.confirm("\n[bold]Do you want to create a pull request with these fixes?[/bold]"):
            self.console.print("[dim]PR creation cancelled by user after auto-fix[/dim]")
            return False
        else:
            self.console.print("✓ Proceeding with pull request creation")
            return True 