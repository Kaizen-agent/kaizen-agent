"""Environment variable setup and validation for Kaizen CLI."""

import os
import click
from pathlib import Path
from typing import Dict, List, Optional, Set
from dotenv import load_dotenv

# Required environment variables for different features
REQUIRED_VARS = {
    'core': ['GOOGLE_API_KEY'],
    'github': ['GITHUB_TOKEN'],
    'optional': ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'LLM_MODEL_NAME']
}

# Feature descriptions
FEATURE_DESCRIPTIONS = {
    'core': 'Core functionality (required for all operations)',
    'github': 'GitHub integration (required for PR creation)',
    'optional': 'Optional LLM providers (alternative to Google)'
}

def load_environment_variables(workspace_root: Optional[Path] = None) -> Dict[str, str]:
    """Load environment variables from .env files and user's environment.
    
    Args:
        workspace_root: Root directory to search for .env files
        
    Returns:
        Dictionary of loaded environment variables
    """
    if workspace_root is None:
        workspace_root = Path.cwd()
    
    loaded_vars = {}
    
    # Look for .env files in the workspace root
    env_files = [
        workspace_root / ".env",
        workspace_root / ".env.local",
        workspace_root / ".env.test"
    ]
    
    for env_file in env_files:
        if env_file.exists():
            try:
                load_dotenv(env_file, override=True)
                loaded_vars[str(env_file)] = "loaded"
            except Exception as e:
                loaded_vars[str(env_file)] = f"error: {str(e)}"
    
    return loaded_vars

def validate_environment_variables(required_features: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
    """Validate that required environment variables are set.
    
    Args:
        required_features: List of features that require specific environment variables
        
    Returns:
        Dictionary containing validation results for each feature
    """
    if required_features is None:
        required_features = ['core']
    
    validation_results = {}
    
    for feature in required_features:
        if feature not in REQUIRED_VARS:
            continue
            
        feature_vars = REQUIRED_VARS[feature]
        feature_results = {}
        
        for var in feature_vars:
            value = os.getenv(var)
            if value:
                feature_results[var] = "set"
            else:
                feature_results[var] = "missing"
        
        validation_results[feature] = feature_results
    
    return validation_results

def check_environment_setup(workspace_root: Optional[Path] = None, 
                          required_features: Optional[List[str]] = None) -> bool:
    """Check if environment is properly set up.
    
    Args:
        workspace_root: Root directory to search for .env files
        required_features: List of features that require specific environment variables
        
    Returns:
        True if environment is properly set up, False otherwise
    """
    # Load environment variables
    load_environment_variables(workspace_root)
    
    # Validate required variables
    validation_results = validate_environment_variables(required_features)
    
    # Check if all required variables are set
    for feature, vars_status in validation_results.items():
        for var, status in vars_status.items():
            if status == "missing":
                return False
    
    return True

def display_environment_status(workspace_root: Optional[Path] = None,
                             required_features: Optional[List[str]] = None) -> None:
    """Display the current environment setup status.
    
    Args:
        workspace_root: Root directory to search for .env files
        required_features: List of features that require specific environment variables
    """
    if workspace_root is None:
        workspace_root = Path.cwd()
    
    if required_features is None:
        required_features = ['core']
    
    click.echo("🔍 Checking environment setup...")
    
    # Load environment variables
    loaded_files = load_environment_variables(workspace_root)
    
    # Display loaded .env files
    if loaded_files:
        click.echo("\n📁 Environment files loaded:")
        for file_path, status in loaded_files.items():
            if status == "loaded":
                click.echo(f"  ✅ {file_path}")
            else:
                click.echo(f"  ❌ {file_path} ({status})")
    else:
        click.echo("\n📁 No .env files found in workspace root")
    
    # Validate environment variables
    validation_results = validate_environment_variables(required_features)
    
    click.echo("\n🔧 Environment variables status:")
    for feature, vars_status in validation_results.items():
        if feature in FEATURE_DESCRIPTIONS:
            click.echo(f"\n  {FEATURE_DESCRIPTIONS[feature]}:")
        else:
            click.echo(f"\n  {feature}:")
        
        for var, status in vars_status.items():
            if status == "set":
                click.echo(f"    ✅ {var}")
            else:
                click.echo(f"    ❌ {var} (missing)")
    
    # Check overall status
    is_setup = check_environment_setup(workspace_root, required_features)
    if is_setup:
        click.echo("\n✅ Environment is properly configured!")
    else:
        click.echo("\n❌ Environment is not properly configured.")
        display_setup_instructions(required_features)

def display_setup_instructions(required_features: Optional[List[str]] = None) -> None:
    """Display instructions for setting up environment variables.
    
    Args:
        required_features: List of features that require specific environment variables
    """
    if required_features is None:
        required_features = ['core']
    
    click.echo("\n📋 Setup Instructions:")
    click.echo("=" * 50)
    
    for feature in required_features:
        if feature not in REQUIRED_VARS:
            continue
            
        click.echo(f"\n🔧 {FEATURE_DESCRIPTIONS.get(feature, feature).upper()}:")
        
        for var in REQUIRED_VARS[feature]:
            if var == 'GOOGLE_API_KEY':
                click.echo(f"  {var}:")
                click.echo("    - Get your API key from: https://makersuite.google.com/app/apikey")
                click.echo("    - Add to your .env file: GOOGLE_API_KEY=your_api_key_here")
            elif var == 'GITHUB_TOKEN':
                click.echo(f"  {var}:")
                click.echo("    - Create a personal access token at: https://github.com/settings/tokens")
                click.echo("    - Required scopes: repo, workflow")
                click.echo("    - Add to your .env file: GITHUB_TOKEN=your_token_here")
            elif var == 'OPENAI_API_KEY':
                click.echo(f"  {var}:")
                click.echo("    - Get your API key from: https://platform.openai.com/api-keys")
                click.echo("    - Add to your .env file: OPENAI_API_KEY=your_api_key_here")
            elif var == 'ANTHROPIC_API_KEY':
                click.echo(f"  {var}:")
                click.echo("    - Get your API key from: https://console.anthropic.com/")
                click.echo("    - Add to your .env file: ANTHROPIC_API_KEY=your_api_key_here")
            else:
                click.echo(f"  {var}: Add to your .env file")
    
    click.echo("\n💡 Tips:")
    click.echo("  - Create a .env file in your project root")
    click.echo("  - Never commit .env files to version control")
    click.echo("  - Use .env.example to document required variables")
    click.echo("  - Restart your terminal after setting environment variables")

def create_env_example_file(workspace_root: Optional[Path] = None) -> None:
    """Create a .env.example file with all required environment variables.
    
    Args:
        workspace_root: Root directory to create the .env.example file
    """
    if workspace_root is None:
        workspace_root = Path.cwd()
    
    example_file = workspace_root / ".env.example"
    
    if example_file.exists():
        click.echo(f"⚠️  {example_file} already exists. Skipping creation.")
        return
    
    content = """# Kaizen Agent Environment Variables
# Copy this file to .env and fill in your actual values

# Core functionality (required)
GOOGLE_API_KEY=your_google_api_key_here

# GitHub integration (required for PR creation)
GITHUB_TOKEN=your_github_personal_access_token_here

# Optional LLM providers (alternative to Google)
# OPENAI_API_KEY=your_openai_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Custom LLM model name
# LLM_MODEL_NAME=gemini-2.5-flash-preview-05-20
"""
    
    try:
        example_file.write_text(content)
        click.echo(f"✅ Created {example_file}")
        click.echo("📝 Please copy this file to .env and fill in your actual values")
    except Exception as e:
        click.echo(f"❌ Failed to create {example_file}: {str(e)}")

def get_missing_variables(required_features: Optional[List[str]] = None) -> Set[str]:
    """Get a set of missing environment variables.
    
    Args:
        required_features: List of features that require specific environment variables
        
    Returns:
        Set of missing environment variable names
    """
    if required_features is None:
        required_features = ['core']
    
    missing_vars = set()
    validation_results = validate_environment_variables(required_features)
    
    for feature, vars_status in validation_results.items():
        for var, status in vars_status.items():
            if status == "missing":
                missing_vars.add(var)
    
    return missing_vars 