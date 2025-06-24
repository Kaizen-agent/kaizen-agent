# Private Repository Setup Guide

This guide helps you resolve GitHub token permission issues when working with private repositories in Kaizen.

## The Problem

When working with private repositories, you may encounter errors like:
- `403: Forbidden` when accessing branch information
- `422: Validation Failed - not all refs are readable` when creating pull requests

This happens because private repositories require specific GitHub token permissions.

## Solution: GitHub Token Configuration

### 1. Create a GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "Kaizen AutoFix")
4. Set an expiration date
5. **Important**: Select the following scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (if using GitHub Actions)
   - ✅ `write:packages` (if using GitHub Packages)

### 2. Set the Token in Your Environment

Add the token to your environment variables:

```bash
# Linux/macOS
export GITHUB_TOKEN=ghp_your_token_here

# Windows (PowerShell)
$env:GITHUB_TOKEN="ghp_your_token_here"

# Or add to your .env file
echo "GITHUB_TOKEN=ghp_your_token_here" >> .env
```

### 3. Verify Repository Access

Ensure you have access to the private repository:
- You must be a collaborator, organization member, or owner
- The repository must allow pull request creation from your account

## Testing Your Setup

Use the GitHub access testing command to verify your configuration:

```bash
# Test with a config file
kaizen test-github-access --config test_config.yaml

# Test with a specific repository
kaizen test-github-access --repo owner/repo-name --base-branch main

# Test during normal test execution
kaizen test-all --config test_config.yaml --create-pr --test-github-access
```

## Common Issues and Solutions

### Issue: "not all refs are readable"
**Cause**: Token doesn't have `repo` scope for private repositories
**Solution**: Regenerate token with `repo` scope

### Issue: "403 Forbidden"
**Cause**: Insufficient repository permissions
**Solution**: 
1. Check repository access permissions
2. Ensure token has correct scopes
3. Verify you're a collaborator on the repository

### Issue: "Repository not found"
**Cause**: Repository doesn't exist or you don't have access
**Solution**: Verify repository name and your access permissions

## Token Scopes Explained

| Scope | Public Repos | Private Repos | Description |
|-------|-------------|---------------|-------------|
| `public_repo` | ✅ | ❌ | Access to public repositories only |
| `repo` | ✅ | ✅ | Full access to all repositories |
| `workflow` | ✅ | ✅ | GitHub Actions access |
| `write:packages` | ✅ | ✅ | Package registry access |

## Security Best Practices

1. **Use minimal scopes**: Only grant the permissions you need
2. **Set expiration dates**: Regularly rotate your tokens
3. **Use environment variables**: Never hardcode tokens in your code
4. **Repository-specific tokens**: Consider using repository-specific tokens for better security

## Troubleshooting

### Check Token Permissions
```bash
# Test token access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

### Verify Repository Access
```bash
# Test repository access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO
```

### Check Branch Access
```bash
# Test branch access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO/branches/BRANCH_NAME
```

## Using Kaizen Commands for Testing

### Environment Setup Check
```bash
# Check if environment is properly configured
kaizen setup check-env --features github
```

### GitHub Access Testing
```bash
# Test with config file
kaizen test-github-access --config test_config.yaml

# Test specific repository
kaizen test-github-access --repo owner/repo-name

# Test with specific base branch
kaizen test-github-access --repo owner/repo-name --base-branch main
```

### Comprehensive Diagnostics
```bash
# Run detailed diagnostics
kaizen diagnose-github-access --config test_config.yaml

# Or test specific repository
kaizen diagnose-github-access --repo owner/repo-name
```

### Test Execution with Access Testing
```bash
# Run tests with GitHub access testing
kaizen test-all --config test_config.yaml --create-pr --test-github-access

# Save detailed logs for analysis
kaizen test-all --config test_config.yaml --create-pr --test-github-access --save-logs --verbose
```

## Step-by-Step Setup Process

### Step 1: Environment Setup
```bash
# Check current environment
kaizen setup check-env --features github

# Create environment template if needed
kaizen setup create-env-example

# Edit your .env file with your tokens
# GITHUB_TOKEN=ghp_your_token_here
# GOOGLE_API_KEY=your_google_api_key_here
```

### Step 2: Test GitHub Access
```bash
# Test basic access
kaizen test-github-access --repo owner/repo-name

# Run comprehensive diagnostics
kaizen diagnose-github-access --repo owner/repo-name
```

### Step 3: Test PR Creation
```bash
# Test with access testing enabled
kaizen test-all --config test_config.yaml --create-pr --test-github-access

# Save detailed logs for analysis
kaizen test-all --config test_config.yaml --create-pr --test-github-access --save-logs --verbose
```

## Getting Help

If you're still experiencing issues:

1. Run the GitHub access test: `kaizen test-github-access`
2. Check the detailed error messages in the test output
3. Verify your token has the correct scopes
4. Ensure you have repository access permissions
5. Check the repository settings for pull request restrictions

For additional support, please provide:
- The output of `kaizen test-github-access`
- Your repository visibility (public/private)
- The specific error messages you're seeing

## Quick Commands Reference

```bash
# Environment setup
kaizen setup check-env --features github

# Access testing
kaizen test-github-access --repo owner/repo-name

# Comprehensive diagnostics
kaizen diagnose-github-access --repo owner/repo-name

# Test execution with access testing
kaizen test-all --config test_config.yaml --create-pr --test-github-access

# Save detailed logs
kaizen test-all --config test_config.yaml --create-pr --test-github-access --save-logs --verbose
``` 