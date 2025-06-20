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

### Step 2: Check Organization Membership
```bash
# Verify you're a member
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/orgs/ORGANIZATION_NAME/members/YOUR_USERNAME
```

### Step 3: Check Repository Permissions
```bash
# Verify repository access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/OWNER/REPO
```

### Step 4: Test Manual PR Creation
1. Go to the repository on GitHub
2. Try to create a PR manually
3. If manual creation works, the issue is with the token/API
4. If manual creation fails, the issue is with permissions

### Step 5: Contact Organization Admins
If all else fails:
1. Contact the organization administrators
2. Request appropriate permissions for your role
3. Ask them to check organization settings and restrictions

## Common Solutions

### For Organization Members
1. **Request role upgrade** to Member or higher
2. **Enable SSO** for your personal access token
3. **Request repository access** if you're not a collaborator

### For Outside Collaborators
1. **Request organization membership**
2. **Ask for collaborator access** to specific repositories
3. **Verify your access level** is sufficient for PR creation

### For Repository Owners
1. **Check branch protection rules**
2. **Verify organization settings**
3. **Add necessary collaborators** with appropriate permissions

## Getting Help

If you're still experiencing issues:

1. **Run the diagnostic commands** above
2. **Check organization settings** with your admin
3. **Verify your token has SSO enabled** (if required)
4. **Test manual PR creation** in the GitHub web interface
5. **Contact organization administrators** for permission issues

### Information to Provide
When seeking help, provide:
- Organization name
- Repository name
- Your role in the organization
- Output of diagnostic commands
- Whether manual PR creation works
- Any error messages from GitHub API

## Prevention

1. **Use organization-specific tokens** when possible
2. **Enable SSO** for tokens used with organization repositories
3. **Regularly verify permissions** and access levels
4. **Keep tokens updated** with appropriate scopes and SSO
5. **Test access** before running automated workflows 