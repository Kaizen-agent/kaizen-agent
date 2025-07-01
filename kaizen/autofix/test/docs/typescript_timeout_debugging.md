# TypeScript Timeout Debugging Guide

This guide helps you identify and resolve TypeScript execution timeout issues, especially when working with Mastra AI agents.

## Quick Diagnosis

### 1. Use the Debug Command

The easiest way to diagnose TypeScript issues is to use the built-in debugging command:

```bash
# Check your environment and dependencies
kaizen debug-typescript --check-deps

# Test a specific TypeScript file
kaizen debug-typescript --test-file your_agent.ts --verbose

# Run performance benchmarks
kaizen debug-typescript --benchmark
```

### 2. Enable Detailed Logging

When running tests, use the debug flags to get detailed information:

```bash
# Enable verbose logging
kaizen test --config test_config.yaml --verbose

# Enable TypeScript-specific debugging
kaizen test --config test_config.yaml --debug-ts

# Clear cache and show statistics
kaizen test --config test_config.yaml --clear-ts-cache --show-cache-stats
```

## Understanding the Logs

When you enable `--debug-ts`, you'll see detailed logs like this:

```
🚀 Starting TypeScript execution for region: email_agent
   Method: auto-detect
   Input data: ['test input']
   Code length: 2048 characters
🤖 Detected Mastra agent, applying optimizations: email_agent
📁 Creating temporary TypeScript file...
✅ Temporary file created: /tmp/tmp123.ts (took 0.02s)
   File size: 2048 bytes
📝 Generating optimized execution script...
✅ Execution script generated (took 0.01s)
   Script length: 1024 characters
📄 Writing execution script to temporary file...
✅ Execution script written: /tmp/tmp456.ts (took 0.01s)
   Script file size: 1024 bytes
⚙️  Preparing ts-node command...
🔧 Adding Mastra-specific optimizations...
   Added: --transpile-only, --skip-project, optimized compiler options
✅ ts-node command prepared (took 0.01s)
   Command: npx ts-node --transpile-only --skip-project --compiler-options {"module":"commonjs","target":"es2020","esModuleInterop":true,"skipLibCheck":true} /tmp/tmp456.ts
🌍 Setting up environment variables...
✅ Environment variables set (took 0.01s)
   NODE_ENV: production
   TS_NODE_CACHE: true
   TS_NODE_CACHE_DIRECTORY: /Users/user/.kaizen/ts-cache
⏱️  Setting execution timeout: 180 seconds
🚀 Starting ts-node execution...
   This may take a while for first-time compilation...
✅ ts-node execution completed (took 45.23s)
   Return code: 0
   stdout length: 256 characters
   stderr length: 0 characters
📊 Parsing execution output...
✅ Output parsed successfully (took 0.01s)
   Parsed data: {'result': 'Hello, test input!', 'tracked_values': {}}
🎉 TypeScript execution successful!
   Total execution time: 45.28s
   Result type: str
```

## Common Timeout Causes

### 1. **First-time Compilation** (Most Common)
- **Symptoms**: First run takes 30-60 seconds, subsequent runs are faster
- **Solution**: The system automatically caches compiled modules. Subsequent runs should be much faster.

### 2. **Mastra Agent Initialization**
- **Symptoms**: Long loading times when using `@mastra/core/agent` or `@ai-sdk/google`
- **Solution**: The system automatically detects Mastra agents and applies optimizations:
  - Uses `--transpile-only` to skip type checking
  - Sets `NODE_ENV=production` to disable development features
  - Uses optimized compiler options
  - Extends timeout to 180 seconds

### 3. **Network Dependencies**
- **Symptoms**: Timeouts when loading external packages
- **Solution**: 
  - Check your internet connection
  - Ensure npm registry is accessible
  - Consider using a local npm cache

### 4. **Large Dependencies**
- **Symptoms**: Timeouts with heavy packages like AI SDKs
- **Solution**: The system automatically applies optimizations for heavy frameworks

## Performance Optimizations

### Automatic Optimizations

The system automatically applies these optimizations:

1. **TypeScript Compilation Caching**
   - Cache directory: `~/.kaizen/ts-cache/`
   - Compiled modules are cached for faster subsequent runs

2. **Mastra-Specific Optimizations**
   - `--transpile-only`: Skips type checking for speed
   - `--skip-project`: Ignores tsconfig.json for faster loading
   - Optimized compiler options for production builds

3. **Environment Optimizations**
   - `NODE_ENV=production` for Mastra agents
   - `TS_NODE_CACHE=true` for caching
   - Extended timeouts (180s for Mastra, 120s for regular TypeScript)

### Manual Optimizations

You can also manually optimize your setup:

1. **Pre-install Dependencies**
   ```bash
   npm install -g ts-node typescript
   npm install @mastra/core @ai-sdk/google
   ```

2. **Use Local Dependencies**
   ```bash
   npm install --save-dev typescript ts-node
   ```

3. **Configure TypeScript**
   Create a `tsconfig.json` with optimizations:
   ```json
   {
     "compilerOptions": {
       "module": "commonjs",
       "target": "es2020",
       "esModuleInterop": true,
       "skipLibCheck": true,
       "noEmitOnError": false
     }
   }
   ```

## Troubleshooting Steps

### Step 1: Check Environment
```bash
kaizen debug-typescript --check-deps
```

### Step 2: Test Your File
```bash
kaizen debug-typescript --test-file your_agent.ts --verbose
```

### Step 3: Clear Cache and Retry
```bash
kaizen test --config test_config.yaml --clear-ts-cache
```

### Step 4: Increase Timeout
Add timeout to your test configuration:
```yaml
steps:
  - name: "Test agent"
    timeout: 300  # 5 minutes
    input:
      input: ["test input"]
    expected_output:
      status: "success"
```

### Step 5: Check for Specific Issues

#### Network Issues
```bash
# Test npm registry access
npm ping

# Check for proxy issues
npm config list
```

#### Permission Issues
```bash
# Check file permissions
ls -la your_agent.ts

# Check cache directory permissions
ls -la ~/.kaizen/ts-cache/
```

#### Memory Issues
```bash
# Check available memory
free -h

# Monitor Node.js memory usage
node --max-old-space-size=4096 your_agent.ts
```

## Configuration Examples

### Basic Test Configuration
```yaml
name: "Mastra Agent Test"
file_path: "email_agent.ts"
language: "typescript"
steps:
  - name: "Test email agent"
    timeout: 180  # 3 minutes for Mastra
    input:
      input: ["Please improve this email"]
    expected_output:
      status: "success"
```

### Advanced Configuration with Optimizations
```yaml
name: "Optimized Mastra Test"
file_path: "email_agent.ts"
language: "typescript"
settings:
  timeout: 300  # Global 5-minute timeout
  ts_node_options:
    - "--transpile-only"
    - "--skip-project"
  environment:
    NODE_ENV: "production"
    TS_NODE_CACHE: "true"
steps:
  - name: "Test with optimizations"
    timeout: 180
    input:
      input: ["test input"]
    expected_output:
      status: "success"
```

## Getting Help

If you're still experiencing issues:

1. **Run the debug command** and share the output
2. **Check the logs** with `--verbose` and `--debug-ts`
3. **Try the benchmark** to compare performance
4. **Clear the cache** and try again
5. **Check your TypeScript file** for syntax errors or heavy dependencies

The system is designed to handle most TypeScript execution scenarios automatically, but these debugging tools help identify specific issues when they occur. 