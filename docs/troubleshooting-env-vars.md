# Environment Variable Troubleshooting Guide

This guide helps you resolve common environment variable issues, especially with `GITHUB_TOKEN` not being detected.

## Common Issue: "GITHUB_TOKEN environment variable not set"

### Symptoms
- Error message: `GITHUB_TOKEN environment variable not set. Please set it with your GitHub personal access token.`
- GitHub access tests fail immediately
- PR creation fails with token-related errors

### Root Causes

#### 1. **Environment Variables Not Loaded**
The most common cause is that `.env` files aren't being loaded properly.

**Check if your .env file exists:**
```bash
ls -la .env
```

**Check if your .env file has the correct format:**
```bash
cat .env
# Should contain:
# GITHUB_TOKEN=ghp_your_token_here
# GOOGLE_API_KEY=your_google_api_key_here
```

#### 2. **Wrong File Location**
The `.env` file must be in the correct location.

**Correct locations (in order of priority):**
- `.env` (current directory)
- `.env.local` (current directory)  
- `.env.test` (current directory)

**Check your current directory:**
```bash
pwd
ls -la | grep env
```

#### 3. **File Permissions**
The `.env` file might not be readable.

**Check file permissions:**
```bash
ls -la .env
# Should show: -rw-r--r-- or similar (readable by user)
```

**Fix permissions if needed:**
```bash
chmod 600 .env  # Read/write for owner only
```

#### 4. **Terminal Session Issues**
Environment variables might not be loaded in your current terminal session.

**Check if variables are loaded:**
```bash
echo $GITHUB_TOKEN
# Should show your token (or be empty if not set)
```

**Restart your terminal** after creating/modifying `.env` files.

### Solutions

#### Solution 1: Create/Update .env File
```bash
# Create .env file in your project root
cat > .env << EOF
GITHUB_TOKEN=ghp_your_actual_token_here
GOOGLE_API_KEY=your_actual_google_api_key_here
EOF
```

#### Solution 2: Set Environment Variables Directly
```bash
# Linux/macOS
export GITHUB_TOKEN="ghp_your_actual_token_here"
export GOOGLE_API_KEY="your_actual_google_api_key_here"

# Windows (PowerShell)
$env:GITHUB_TOKEN="ghp_your_actual_token_here"
$env:GOOGLE_API_KEY="your_actual_google_api_key_here"
```

#### Solution 3: Use the Setup Commands
```bash
# Check environment status
kaizen setup check-env --features github

# Create .env.example file
kaizen setup create-env-example

# Copy and edit the example
cp .env.example .env
# Edit .env with your actual values
```

### Verification Steps

#### Step 1: Test Environment Loading
```bash
# Test if .env file is being loaded
kaizen test-github-access --repo owner/repo-name
```

You should see:
```
Loading environment variables...
Loaded environment from: /path/to/.env
GitHub token found: ghp_1234...
```

#### Step 2: Test GitHub Access
```bash
# Test GitHub access with your token
kaizen test-github-access --repo owner/repo-name
```

#### Step 3: Check Token Permissions
```bash
# Test token access directly
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

### Debugging Commands

#### Check Environment Variables
```bash
# Check if variables are set
env | grep -E "(GITHUB_TOKEN|GOOGLE_API_KEY)"

# Check specific variable
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:-'NOT SET'}"
```

#### Check .env File
```bash
# Check if .env file exists and is readable
ls -la .env*

# Check .env file content (be careful not to expose tokens)
head -n 5 .env
```

#### Test Python Environment Loading
```bash
# Test if python-dotenv is working
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('GITHUB_TOKEN:', 'SET' if os.getenv('GITHUB_TOKEN') else 'NOT SET')
"
```

### Common Mistakes

#### 1. **Wrong File Name**
- ❌ `.env.txt` (has .txt extension)
- ❌ `env` (missing dot)
- ✅ `.env` (correct)

#### 2. **Wrong File Format**
- ❌ `GITHUB_TOKEN ghp_token_here` (missing equals sign)
- ❌ `GITHUB_TOKEN= ghp_token_here` (space after equals)
- ✅ `GITHUB_TOKEN=ghp_token_here` (correct)

#### 3. **Wrong Directory**
- ❌ `.env` in home directory when running from project directory
- ❌ `.env` in subdirectory when running from parent directory
- ✅ `.env` in the same directory where you run the command

#### 4. **Token Format Issues**
- ❌ `GITHUB_TOKEN=ghp_token_here` (if token is invalid)
- ❌ `GITHUB_TOKEN=ghp_` (incomplete token)
- ✅ `GITHUB_TOKEN=ghp_1234567890abcdef...` (valid token format)

### Getting Help

If you're still having issues:

1. **Run the diagnostic command:**
   ```bash
   kaizen setup check-env --features github
   ```

2. **Check the detailed error messages** in the command output

3. **Verify your token is valid:**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
   ```

4. **Check if you're in the right directory:**
   ```bash
   pwd
   ls -la .env*
   ```

5. **Try setting the variable directly:**
   ```bash
   export GITHUB_TOKEN="your_token_here"
   kaizen test-github-access --repo owner/repo-name
   ```

### Prevention Tips

1. **Always use .env files** instead of setting variables directly
2. **Add .env to .gitignore** to avoid committing tokens
3. **Use .env.example** to document required variables
4. **Test your setup** before running important commands
5. **Keep tokens secure** and rotate them regularly 