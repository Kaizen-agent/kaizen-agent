# LlamaIndex Agent Execution Guide

This document explains how to use the `_execute_llamaindex_agent` method for executing LlamaIndex agents with async support and dynamic import handling.

## Overview

The `_execute_llamaindex_agent` method is designed to handle LlamaIndex agents with the following features:

- **Async Support**: Automatically detects and handles async functions/methods
- **Dynamic Import Handling**: Automatically detects and imports dependencies from code
- **Generic Handling**: Works with different LlamaIndex agent patterns
- **Error Handling**: Comprehensive error handling and logging
- **Variable Tracking**: Supports variable tracking during execution
- **Framework Integration**: Integrates with the existing test framework

## Key Improvements

### 1. Dynamic Import Detection
- **Scalable**: No longer requires hardcoded package configurations
- **Automatic**: Analyzes code AST to extract import statements
- **Flexible**: Handles both standard and third-party imports
- **Robust**: Graceful handling of missing dependencies

### 2. Enhanced Async Support
- **Event Loop Management**: Proper handling of existing event loops
- **Thread Isolation**: Uses ThreadPoolExecutor for async execution
- **Fallback Mechanisms**: Subprocess-based execution for complex scenarios
- **Timeout Handling**: Configurable timeouts with proper cleanup

## Method Signature

```python
def _execute_llamaindex_agent(
    self,
    region_info: RegionInfo,
    input_data: List[Any],
    tracked_variables: Set[str]
) -> Dict[str, Any]:
```

### Parameters

- `region_info`: Region info with entry point configuration
- `input_data`: Input data to pass to the method/function
- `tracked_variables`: Variables to track during execution

### Returns

Dictionary containing:
- `result`: The execution result
- `tracked_values`: Dictionary of tracked variable values
- `tracked_variables`: Set of tracked variable names

## Usage Examples

### 1. Basic Async Agent

```python
import os
import asyncio
from dotenv import load_dotenv
from llama_index.llms.litellm import LiteLLM
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.workflow import Context

load_dotenv()

def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b

def add(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b

class MathAgent:
    def __init__(self):
        self.llm = LiteLLM(model='gemini/gemini-2.0-flash-lite', temperature=0)
        self.agent = ReActAgent(
            tools=[add, multiply],
            llm=self.llm,
        )
        self.ctx = Context(self.agent)

    async def run(self, task: str) -> str:
        handler = self.agent.run(task, ctx=self.ctx)
        response = await handler
        return response
```

### 2. Sync Agent

```python
class SimpleAgent:
    def __init__(self):
        self.name = "SimpleAgent"
    
    def calculate(self, a: float, b: float) -> float:
        """Calculate the sum of two numbers."""
        return a + b
```

### 3. Function-based Agent

```python
def simple_math(a: float, b: float) -> float:
    """Simple math function for testing."""
    return a + b
```

## Configuration

### Entry Point Configuration

```python
from kaizen.autofix.test.code_region import AgentEntryPoint

# For class-based agents
entry_point = AgentEntryPoint(
    module="math_agent",
    class_name="MathAgent",
    method="run",
    fallback_to_function=True
)

# For function-based agents
entry_point = AgentEntryPoint(
    module="math_agent",
    method="simple_math",
    fallback_to_function=True
)
```

### Test Configuration

```yaml
name: "LlamaIndex Agent Test"
file_path: "math_agent.py"
language: "python"
framework: "llamaindex"
description: "Test configuration for LlamaIndex-based agent"

agent:
  module: "math_agent"
  class: "MathAgent"
  method: "run"

steps:
  - name: "Test math calculation"
    input:
      input: 
        - name: task
          type: string
          value: "What is 5 plus 7?"
      method: "run"
    expected_output:
      contains: "12"
    description: "Test the LlamaIndex agent's math calculation"
    timeout: 60
```

## Dynamic Import Handling

### How It Works

The method automatically analyzes your code and handles imports:

1. **AST Analysis**: Parses the code to extract import statements
2. **Import Classification**: Distinguishes between standard and third-party imports
3. **Safe Importing**: Attempts to import modules with error handling
4. **Global Registration**: Makes imports available in sys.modules

### Supported Import Types

```python
# Simple imports
import os
import sys
import asyncio

# From imports
from dotenv import load_dotenv
from llama_index.llms.litellm import LiteLLM
from llama_index.core.agent.workflow import ReActAgent

# Aliased imports
import json as js
from pathlib import Path as P

# All imports are automatically detected and handled
```

### Error Handling

- **Missing Dependencies**: Graceful handling with warning logs
- **Import Errors**: Detailed error reporting
- **Standard Library**: Automatic handling of built-in modules
- **Third-party**: Attempts import with fallback options

## Async Handling

The method automatically detects and handles async functions:

### Async Detection

```python
import asyncio

# The method checks if a function is async
if asyncio.iscoroutinefunction(func):
    # Handle async execution
    return self._execute_async_function(func, input_data)
else:
    # Handle sync execution
    return self._execute_sync_function(func, input_data)
```

### Event Loop Management

The method handles different event loop scenarios:

1. **No Event Loop**: Creates a new event loop
2. **Existing Event Loop**: Uses ThreadPoolExecutor to run in a separate thread
3. **Complex Scenarios**: Falls back to subprocess execution
4. **Timeout Protection**: 5-minute timeout for async operations

## Error Handling

The method provides comprehensive error handling:

### Common Error Scenarios

1. **Module Not Found**: Handles missing LlamaIndex packages
2. **Import Errors**: Graceful handling of import failures
3. **Async Runtime Errors**: Proper event loop management
4. **Timeout Errors**: Protection against hanging operations

### Error Response Format

```python
{
    'result': None,
    'tracked_values': {},
    'tracked_variables': tracked_variables,
    'error': str(e),
    'error_details': traceback.format_exc()
}
```

## Migration Guide

### From Old Implementation

If you were using the old hardcoded package configuration:

**Before:**
```python
# Required manual package configuration
config = ImportManagerConfig()
config.common_packages['llama_index'] = PackageConfig(...)
```

**After:**
```python
# Automatic import detection - no configuration needed
# Just write your imports in the code
from llama_index.llms.litellm import LiteLLM
```

### Benefits of New Implementation

1. **Scalability**: No need to maintain package lists
2. **Flexibility**: Works with any import pattern
3. **Maintainability**: Less configuration overhead
4. **Reliability**: Better error handling and fallbacks

## Dependencies

### Required Packages

Add these to your `requirements.txt`:

```
llama_index
llama_index_core
llama_index_llms_litellm
python-dotenv
```

### Environment Variables

Set up your environment variables:

```bash
# .env file
GOOGLE_API_KEY=your_google_api_key_here
LITELLM_API_KEY=your_litellm_api_key_here
```

## Integration with Test Framework

### Framework Detection

The method is automatically called when `framework='llamaindex'` is specified:

```python
if framework == 'llamaindex':
    return self._execute_llamaindex_agent(region_info, input_data, tracked_variables)
```

### Test Execution Flow

1. **Region Extraction**: Extract code region using entry point
2. **Dependency Resolution**: Resolve LlamaIndex dependencies
3. **Agent Execution**: Execute with async/sync handling
4. **Result Processing**: Return structured results
5. **Variable Tracking**: Track specified variables

## Best Practices

### 1. Error Handling

Always wrap agent execution in try-catch blocks:

```python
try:
    result = executor._execute_llamaindex_agent(region_info, input_data, tracked_variables)
    print(f"Success: {result['result']}")
except Exception as e:
    print(f"Error: {str(e)}")
```

### 2. Timeout Configuration

Set appropriate timeouts for your agents:

```yaml
steps:
  - name: "Test with timeout"
    timeout: 120  # 2 minutes
```

### 3. Variable Tracking

Track important variables for debugging:

```python
tracked_variables = {'llm', 'agent', 'ctx', 'response'}
```

### 4. Async Best Practices

- Use `async def` for agent methods that perform I/O operations
- Handle async operations properly in your agent code
- Test both sync and async versions of your agents

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'llama_index'**
   - Install LlamaIndex packages: `pip install llama_index`
   - Check your Python environment

2. **RuntimeError: There is no current event loop**
   - The method handles this automatically
   - Check if you're calling from an async context

3. **TimeoutError: Operation timed out**
   - Increase timeout in test configuration
   - Check network connectivity for API calls

4. **ImportError: Cannot import name 'LiteLLM'**
   - Install specific LlamaIndex packages
   - Check package versions compatibility

### Debug Mode

Enable debug logging to see detailed execution information:

```python
import logging
logging.getLogger('kaizen.autofix.test.code_region').setLevel(logging.DEBUG)
```

## Testing

### Running Tests

```bash
# Run the test file
python test_llamaindex_agent.py

# Expected output for sync test
✅ Sync execution completed!
📤 Result: 30.8

# Expected output for async test (if dependencies installed)
✅ Execution completed!
📤 Result: "The answer is 12"
```

### Test Coverage

The implementation supports testing:

- ✅ Sync functions and methods
- ✅ Async functions and methods
- ✅ Class-based agents
- ✅ Function-based agents
- ✅ Error handling scenarios
- ✅ Variable tracking
- ✅ Timeout handling

## Migration Guide

### From Regular Execution

If you're migrating from regular execution to LlamaIndex:

1. **Add Framework Specification**:
   ```yaml
   framework: "llamaindex"
   ```

2. **Update Entry Point**:
   ```python
   entry_point = AgentEntryPoint(
       module="your_module",
       class_name="YourAgent",
       method="your_method"
   )
   ```

3. **Handle Async Methods**:
   ```python
   async def your_method(self, input_data):
       # Your async logic here
       return result
   ```

### From Other Frameworks

The method follows the same interface as other framework handlers, making migration straightforward.

## Future Enhancements

Planned improvements:

1. **Enhanced Caching**: Cache compiled agents for faster execution
2. **Streaming Support**: Support for streaming responses
3. **Batch Processing**: Handle multiple inputs efficiently
4. **Advanced Error Recovery**: Automatic retry mechanisms
5. **Performance Monitoring**: Detailed execution metrics

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the test examples in `test_llamaindex_agent.py`
3. Enable debug logging for detailed information
4. Check LlamaIndex documentation for agent-specific issues 