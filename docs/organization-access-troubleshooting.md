# Organization Access Troubleshooting Guide

This guide helps you resolve GitHub organization-level access issues that can prevent PR creation even when your token has the correct scopes.

## The Problem: "not all refs are readable" with Correct Token

You may encounter this error even when:
- ✅ Your `GITHUB_TOKEN` has the `repo` scope
- ✅ You can access the repository
- ✅ You can read repository information
- ❌ But PR creation still fails with "not all refs are readable"

This typically indicates **organization-level restrictions** or **repository-specific settings**.

## Root Causes and Solutions

### 1. **Organization Membership Issues**

#### Problem
You're not a member of the organization that owns the repository.

#### Symptoms
- Can access repository metadata
- Cannot create PRs
- "not all refs are readable" error

#### Solution
1. **Check organization membership:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user/orgs
   ```

2. **Request organization access:**
   - Go to the organization page on GitHub
   - Click "Request access" if you're not a member
   - Wait for approval from organization admins

3. **Verify your role:**
   - Organization members have different permission levels
   - You need at least "Read" access to create PRs

### 2. **Organization Role Permissions**

#### Problem
Your organization role doesn't have sufficient permissions.

#### Organization Roles (from least to most permissions):
- **Outside collaborator**: Limited access to specific repositories
- **Member**: Basic access to organization repositories
- **Moderator**: Can manage repository access and moderate discussions
- **Admin**: Full access to organization settings

#### Solution
1. **Check your current role:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/orgs/ORGANIZATION_NAME/memberships/YOUR_USERNAME
   ```

2. **Request role upgrade:**
   - Contact organization admins
   - Request appropriate permissions for your role

### 3. **Repository-Specific Access**

#### Problem
The repository has specific access controls that prevent your token from creating PRs.

#### Solution
1. **Check repository access:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO
   ```

2. **Verify collaborator status:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO/collaborators/YOUR_USERNAME
   ```

3. **Request collaborator access:**
   - Go to repository Settings > Collaborators
   - Add yourself as a collaborator (if you have admin access)
   - Or request access from repository owners

### 4. **Branch Protection Rules**

#### Problem
The repository has branch protection rules that prevent PR creation from certain sources.

#### Common Restrictions:
- **Require pull request reviews**: Must have approved reviews
- **Restrict pushes that create files**: Cannot create new files directly
- **Require status checks**: Must pass CI/CD checks
- **Restrict who can push**: Only specific users/teams can push

#### Solution
1. **Check branch protection:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO/branches/BRANCH_NAME/protection
   ```

2. **Work with repository admins:**
   - Request exceptions for your workflow
   - Set up appropriate branch protection rules
   - Ensure your token/user has necessary permissions

### 5. **Organization SSO Requirements**

#### Problem
The organization requires Single Sign-On (SSO) authentication.

#### Symptoms
- Token works for public repositories
- Token fails for organization private repositories
- "not all refs are readable" error

#### Solution
1. **Enable SSO for your token:**
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Find your token and click "Configure SSO"
   - Authorize the token for the organization

2. **Verify SSO status:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user/orgs
   # Look for "sso_enabled": true in the response
   ```

### 6. **Repository Visibility and Settings**

#### Problem
Repository settings prevent PR creation from external sources.

#### Solution
1. **Check repository settings:**
   - Go to repository Settings > General
   - Verify "Allow forking" is enabled
   - Check "Allow squash merging" and other merge options

2. **Verify fork permissions:**
   - Some organizations require PRs to come from forks
   - Check if you need to fork the repository first

## Diagnostic Commands

### Test Organization Access
```bash
# Check if you're a member of the organization
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/orgs/ORGANIZATION_NAME/members/YOUR_USERNAME

# Check your organization role
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/orgs/ORGANIZATION_NAME/memberships/YOUR_USERNAME

# List all organizations you belong to
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user/orgs
```

### Test Repository Access
```bash
# Check repository access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO

# Check collaborator status
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO/collaborators/YOUR_USERNAME

# Check branch protection
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO/branches/main/protection
```

### Test PR Creation Permissions
```bash
# Try to create a test PR (this will fail but show the exact error)
curl -X POST \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/pulls \
  -d '{
    "title": "Test PR",
    "head": "your-branch",
    "base": "main"
  }'
```

## Step-by-Step Troubleshooting

### Step 1: Verify Basic Access
```bash
# Test with Kaizen
kaizen test-github-access --repo owner/repo-name
```

### Step 2: Run Comprehensive Diagnostics
```bash
# Get detailed diagnostics
kaizen diagnose-github-access --repo owner/repo-name
```

### Step 3: Check Organization Membership
```bash
# Verify you're a member
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/orgs/ORGANIZATION_NAME/members/YOUR_USERNAME
```

### Step 4: Check Repository Permissions
```bash
# Verify repository access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO
```

### Step 5: Test PR Creation with Access Testing
```bash
# Run tests with access testing enabled
kaizen test-all --config your_config.yaml --create-pr --test-github-access
```

### Step 6: Save Detailed Logs for Analysis
```bash
# Save detailed logs to analyze any issues
kaizen test-all --config your_config.yaml --create-pr --test-github-access --save-logs --verbose
```

## Using Kaizen Commands for Troubleshooting

### Environment Setup Check
```bash
# Check if environment is properly configured
kaizen setup check-env --features github
```

### GitHub Access Testing
```bash
# Test with config file
kaizen test-github-access --config your_config.yaml

# Test specific repository
kaizen test-github-access --repo owner/repo-name
```

### Comprehensive Diagnostics
```bash
# Run detailed diagnostics
kaizen diagnose-github-access --config your_config.yaml

# Or test specific repository
kaizen diagnose-github-access --repo owner/repo-name
```

### Test Execution with Access Testing
```bash
# Run tests with GitHub access testing
kaizen test-all --config your_config.yaml --create-pr --test-github-access

# Save detailed logs for analysis
kaizen test-all --config your_config.yaml --create-pr --test-github-access --save-logs --verbose
```

## Common Error Patterns and Solutions

### "not all refs are readable"
- **Cause**: Organization restrictions or branch protection rules
- **Solution**: Contact organization admins, enable SSO, check repository settings

### "403 Forbidden"
- **Cause**: Insufficient permissions or organization membership issues
- **Solution**: Request organization membership, verify collaborator status

### "Repository not found"
- **Cause**: Repository doesn't exist or you don't have access
- **Solution**: Verify repository name, request access from owners

### "Branch not found"
- **Cause**: Branch doesn't exist or you can't access it
- **Solution**: Check branch name, verify branch exists, check permissions

## Getting Help

If you're still experiencing issues:

1. **Run the diagnostic commands** above
2. **Check the detailed error messages** in the command output
3. **Contact organization administrators** for permission issues
4. **Test manual PR creation** in GitHub web interface
5. **Provide diagnostic output** when seeking help

## Quick Reference

```bash
# Environment setup
kaizen setup check-env --features github

# Access testing
kaizen test-github-access --repo owner/repo-name

# Comprehensive diagnostics
kaizen diagnose-github-access --repo owner/repo-name

# Test execution with access testing
kaizen test-all --config your_config.yaml --create-pr --test-github-access --save-logs --verbose
``` 