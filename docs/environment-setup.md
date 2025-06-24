# Environment Setup Guide

This guide explains how to set up environment variables for the Kaizen CLI tool.

## Quick Start

1. **Check your current setup:**
   ```bash
   kaizen setup check-env
   ```

2. **Create a template .env file:**
   ```bash
   kaizen setup create-env-example
   ```

3. **Copy and configure your .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

## Required Environment Variables

### Core Functionality (Required for all operations)

- **`GOOGLE_API_KEY`**: Your Google AI API key for LLM operations
  - Get it from: https://makersuite.google.com/app/apikey
  - Required for: All test execution and code fixing

### GitHub Integration (Required for PR creation)

- **`GITHUB_TOKEN`**: Your GitHub personal access token
  - Create it at: https://github.com/settings/tokens
  - Required scopes: `repo`, `workflow`
  - Required for: Creating pull requests with fixes

### Optional LLM Providers

- **`OPENAI_API_KEY`**: Your OpenAI API key
  - Get it from: https://platform.openai.com/api-keys
  - Alternative to Google AI for LLM operations

- **`ANTHROPIC_API_KEY`**: Your Anthropic API key
  - Get it from: https://console.anthropic.com/
  - Alternative to Google AI for LLM operations

### Optional Configuration

- **`LLM_MODEL_NAME`**: Custom LLM model name
  - Default: `gemini-2.5-flash-preview-05-20`
  - Override the default model used for LLM operations

## Setup Commands

### Check Environment Status

```bash
# Check core functionality only
kaizen setup check-env

# Check core and GitHub integration
kaizen setup check-env --features core github

# Check all features
kaizen setup check-env --features core github optional
```

### Create Environment Template

```bash
# Create .env.example in current directory
kaizen setup create-env-example

# Create .env.example in specific workspace
kaizen setup create-env-example --workspace /path/to/project
```

### Validate Environment (for CI/CD)

```bash
# Validate core functionality
kaizen setup validate-env

# Validate core and GitHub integration
kaizen setup validate-env --features core github

# Exit with code 0 if valid, 1 if invalid
```

## Environment File Locations

The CLI looks for `.env` files in the following order:

1. `.env` (current directory)
2. `.env.local` (current directory)
3. `.env.test` (current directory)

## Example .env File

```bash
# Core functionality (required)
GOOGLE_API_KEY=your_google_api_key_here

# GitHub integration (required for PR creation)
GITHUB_TOKEN=your_github_personal_access_token_here

# Optional LLM providers (alternative to Google)
# OPENAI_API_KEY=your_openai_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Custom LLM model name
# LLM_MODEL_NAME=gemini-2.5-flash-preview-05-20
```

## Troubleshooting

### Common Issues

1. **"GITHUB_TOKEN environment variable not set"**
   - This error occurs when trying to create PRs without a GitHub token
   - Solution: Set up your GitHub token or disable PR creation with `--create-pr=false`

2. **"GOOGLE_API_KEY environment variable not set"**
   - This error occurs when the core API key is missing
   - Solution: Get a Google AI API key and add it to your .env file

3. **Environment variables not loading**
   - Make sure your .env file is in the correct location
   - Restart your terminal after creating/modifying .env files
   - Check file permissions on your .env file

### Getting API Keys

#### Google AI API Key
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key to your .env file

#### GitHub Personal Access Token
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`
4. Generate token and copy to your .env file

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign in to your OpenAI account
3. Click "Create new secret key"
4. Copy the generated key to your .env file

#### Anthropic API Key
1. Go to https://console.anthropic.com/
2. Sign in to your Anthropic account
3. Navigate to API Keys section
4. Create a new API key and copy to your .env file

## Security Best Practices

1. **Never commit .env files to version control**
   - Add `.env` to your `.gitignore` file
   - Use `.env.example` to document required variables

2. **Use environment-specific files**
   - `.env.local` for local development
   - `.env.test` for testing environments
   - `.env.production` for production (if needed)

3. **Rotate API keys regularly**
   - Set up reminders to rotate your API keys
   - Monitor API usage for unusual activity

4. **Use least privilege principle**
   - Only grant necessary scopes to GitHub tokens
   - Use separate API keys for different environments

## Integration with CI/CD

For automated environments, you can validate the setup:

```bash
# In your CI/CD pipeline
kaizen setup validate-env --features core github
if [ $? -eq 0 ]; then
    echo "Environment is properly configured"
    # Continue with your pipeline
else
    echo "Environment validation failed"
    exit 1
fi
```

## Next Steps

After setting up your environment variables:

1. **Test your setup:**
   ```bash
   kaizen setup check-env
   ```

2. **Test GitHub access:**
   ```bash
   kaizen test-github-access --repo owner/repo-name
   ```

3. **Run your first test:**
   ```bash
   kaizen test-all --config your-test-config.yaml
   ```

4. **Try auto-fixing:**
   ```bash
   kaizen test-all --config your-test-config.yaml --auto-fix
   ```

5. **Create a pull request with access testing:**
   ```bash
   kaizen test-all --config your-test-config.yaml --auto-fix --create-pr --test-github-access
   ```

6. **Save detailed logs for analysis:**
   ```bash
   kaizen test-all --config your-test-config.yaml --auto-fix --save-logs --verbose
   ```

## Available CLI Commands

### Core Commands
- `kaizen test-all --config <file>` - Run tests with configuration
- `kaizen setup check-env` - Check environment setup
- `kaizen setup create-env-example` - Create environment template

### GitHub Integration
- `kaizen test-github-access --config <file>` - Test GitHub access
- `kaizen test-github-access --repo owner/repo` - Test specific repository
- `kaizen diagnose-github-access --config <file>` - Comprehensive GitHub diagnostics

### Advanced Options
- `--auto-fix` - Enable automatic code fixing
- `--create-pr` - Create pull request with fixes
- `--test-github-access` - Test GitHub access before running tests
- `--save-logs` - Save detailed test logs in JSON format
- `--verbose` - Show detailed debug information
- `--max-retries <n>` - Maximum fix attempts (default: 1)
- `--base-branch <branch>` - Base branch for PR (default: main) 