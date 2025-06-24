# GitHub Access Issue Resolution Guide

## Problem Summary

You encountered a "not all refs are readable" error when trying to create a pull request to a private repository (`suzuking1192/pharma_ai_agent`), even though your GitHub token has the correct `repo` scope.

## Root Cause Analysis

The error occurs because of **organization-level restrictions** or **repository-specific settings** that prevent PR creation, even with correct token scopes. This is common with:

1. **Organization membership issues** - You may not be a full member of the organization
2. **SSO requirements** - The organization may require Single Sign-On authentication
3. **Repository-specific permissions** - The repository may have specific access controls
4. **Branch protection rules** - The repository may have restrictions on PR creation

## Immediate Solutions

### 1. Run Comprehensive Diagnostics

Use the diagnostic command to identify the exact issue:

```bash
# If you have a config file
kaizen diagnose-github-access --config your_config.yaml

# Or specify the repository directly
kaizen diagnose-github-access --repo suzuking1192/pharma_ai_agent
```

This will provide detailed information about:
- Token validity and scopes
- Organization membership status
- Repository access permissions
- Branch protection rules
- PR creation capabilities

### 2. Test GitHub Access

Run the enhanced GitHub access test:

```bash
# Test with config file
kaizen test-github-access --config your_config.yaml

# Or test specific repository
kaizen test-github-access --repo suzuking1192/pharma_ai_agent
```

### 3. Manual Verification Steps

#### Check Organization Membership
```bash
# Replace with your actual token and organization
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/orgs/suzuking1192/memberships/YOUR_USERNAME
```

#### Check Repository Access
```bash
# Test repository access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/suzuking1192/pharma_ai_agent
```

#### Test Manual PR Creation
1. Go to https://github.com/suzuking1192/pharma_ai_agent
2. Try to create a PR manually in the web interface
3. If manual creation fails, the issue is with permissions, not the token

## Common Resolution Steps

### For Organization Members
1. **Request role upgrade** from organization administrators
2. **Enable SSO** for your personal access token:
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Find your token and click "Configure SSO"
   - Authorize the token for the `suzuking1192` organization
3. **Request repository access** if you're not a collaborator

### For Outside Collaborators
1. **Request full organization membership** (not just outside collaborator)
2. **Ask for repository-specific collaborator access**
3. **Verify your access level** allows PR creation

### For Repository Owners/Admins
1. **Check branch protection rules** in repository settings
2. **Verify organization settings** allow your access level
3. **Add necessary collaborators** with appropriate permissions

## Enhanced Error Handling

The system now provides:

### Better Error Messages
- Specific guidance for organization-level issues
- Clear recommendations for different access levels
- Step-by-step troubleshooting instructions

### Improved Diagnostics
- Organization membership detection
- SSO requirement identification
- Repository permission analysis
- Branch protection rule checking

### Preserved Code Changes
- If PR creation fails due to permissions, code changes are preserved
- You can manually create the PR or fix permissions and retry

## Testing Your Setup

### Step 1: Run Diagnostics
```bash
kaizen diagnose-github-access --repo suzuking1192/pharma_ai_agent
```

### Step 2: Check Access
```bash
kaizen test-github-access --repo suzuking1192/pharma_ai_agent
```

### Step 3: Test PR Creation with Access Testing
```bash
# Run your tests with PR creation and access testing
kaizen test-all --config your_config.yaml --create-pr --test-github-access
```

### Step 4: Save Detailed Logs for Analysis
```bash
# Save detailed logs to analyze any issues
kaizen test-all --config your_config.yaml --create-pr --test-github-access --save-logs --verbose
```

## Expected Outcomes

### If Diagnostics Show Organization Issues
- Contact organization administrators (`suzuking1192`)
- Request full membership or repository access
- Enable SSO for your token if required

### If Diagnostics Show Repository Issues
- Check repository settings for branch protection
- Verify collaborator permissions
- Test manual PR creation

### If Diagnostics Show Token Issues
- Regenerate token with correct scopes (`repo` for private repositories)
- Enable SSO if required by the organization
- Verify token has necessary permissions

## Prevention

1. **Use organization-specific tokens** when possible
2. **Enable SSO** for tokens used with organization repositories
3. **Regularly verify permissions** and access levels
4. **Test access** before running automated workflows
5. **Keep tokens updated** with appropriate scopes

## Getting Help

If you're still experiencing issues:

1. **Run the diagnostic commands** above
2. **Check the detailed troubleshooting guide**: `docs/organization-access-troubleshooting.md`
3. **Contact organization administrators** for permission issues
4. **Test manual PR creation** in GitHub web interface
5. **Provide diagnostic output** when seeking help

## Quick Commands Reference

```bash
# Comprehensive diagnostics
kaizen diagnose-github-access --repo suzuking1192/pharma_ai_agent

# Test access
kaizen test-github-access --repo suzuking1192/pharma_ai_agent

# Run tests with PR creation and access testing
kaizen test-all --config your_config.yaml --create-pr --test-github-access

# Save detailed logs for analysis
kaizen test-all --config your_config.yaml --create-pr --test-github-access --save-logs --verbose

# Check environment setup
kaizen setup check-env --features github
```

## Next Steps

1. **Run the diagnostic command** to identify the specific issue
2. **Follow the recommendations** provided by the diagnostics
3. **Contact organization administrators** if membership issues are detected
4. **Test manual PR creation** to verify permissions
5. **Retry your automated workflow** once permissions are resolved

The enhanced error handling and diagnostics should help you quickly identify and resolve the access issues preventing PR creation. 