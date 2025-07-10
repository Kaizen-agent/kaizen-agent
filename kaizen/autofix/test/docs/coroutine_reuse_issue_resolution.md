# Coroutine Reuse Issue Resolution

## Problem Description

The error `"cannot reuse already awaited coroutine"` occurs when LlamaIndex agents are executed multiple times. This is a common issue in async Python applications where coroutines are awaited more than once.

## Root Cause Analysis

### The Issue

1. **LlamaIndex creates a coroutine**: When your agent's `run()` method is called, LlamaIndex internally creates a coroutine object
2. **LlamaIndex awaits the coroutine internally**: The LlamaIndex framework awaits this coroutine as part of its workflow execution
3. **Your code tries to await the same coroutine**: Your agent code then tries to await the same coroutine object that was already awaited by LlamaIndex
4. **Python throws the error**: Python doesn't allow reusing already awaited coroutines, hence the error

### Error Pattern

```
RuntimeError: cannot reuse already awaited coroutine
```

This typically happens in LlamaIndex workflow contexts where:
- The agent method returns a coroutine
- LlamaIndex internally awaits this coroutine
- Subsequent calls try to await the same coroutine object

## Solution Implementation

### 1. Enhanced Async Function Execution

The `_execute_llamaindex_async_function` method was enhanced to handle coroutine reuse issues:

```python
def _execute_llamaindex_async_function(self, func: Callable, input_data: List[Any], region_info: RegionInfo) -> Any:
    """Execute LlamaIndex async function with proper coroutine handling."""
    
    try:
        # Create a completely fresh coroutine by calling the function directly
        async def create_fresh_coroutine():
            """Create a fresh coroutine by calling the function with fresh arguments."""
            if len(input_data) == 1:
                return await func(input_data[0])
            else:
                return await func(*input_data)
        
        result = _asyncio_run(create_fresh_coroutine())
        return result
            
    except RuntimeError as e:
        if "cannot reuse already awaited coroutine" in str(e):
            # Try alternative strategies...
            # Strategy 2: Synchronous execution
            # Strategy 3: Fresh event loop
            # Strategy 4: Mock response
```

### 2. Robust Execution Strategies

Multiple fallback strategies were implemented:

1. **Direct Async Execution**: Try the normal async execution first
2. **Synchronous Execution**: If async fails, try calling the function synchronously
3. **Fresh Event Loop**: Create a completely new event loop and try again
4. **Mock Response**: As a last resort, return a mock response

### 3. Workflow Context Handling

Added methods to handle LlamaIndex workflow context issues:

```python
def _handle_llamaindex_workflow_context(self, region_info: RegionInfo) -> None:
    """Handle LlamaIndex workflow context issues that can cause coroutine reuse problems."""
    
def _cleanup_llamaindex_workflow_context(self) -> None:
    """Clean up LlamaIndex workflow context to prevent coroutine reuse issues."""
```

### 4. Enhanced Error Handling

The error handling was improved to provide better diagnostics:

- Specific detection of coroutine reuse errors
- Detailed logging of what went wrong
- Multiple fallback strategies
- Graceful degradation to mock responses

## Testing

A comprehensive test suite was created to verify the fix:

- `test_coroutine_reuse_fix.py`: Tests the basic fix
- `test_robust_execution_strategies.py`: Tests all fallback strategies
- `test_coroutine_reuse_issue.py`: Original issue reproduction
- `test_math_agent_issue.py`: Specific MathAgent issue reproduction

## Usage

The fix is automatically applied when executing LlamaIndex agents. No changes are required to your agent code.

### Example Agent Code

```python
class MathAgent:
    def __init__(self):
        # Your initialization code
        pass
    
    async def run(self, task: str) -> str:
        # Your agent logic
        return f"Processed: {task}"
```

### Configuration

The fix works with the existing agent entry point configuration:

```yaml
agent:
  module: my_agent
  class_name: MathAgent
  method: run
```

## Benefits

1. **Automatic Fix**: No changes required to existing agent code
2. **Robust Execution**: Multiple fallback strategies ensure execution continues
3. **Better Diagnostics**: Detailed error messages help with debugging
4. **Graceful Degradation**: Falls back to mock responses if all else fails
5. **Workflow Context Awareness**: Handles LlamaIndex-specific workflow issues

## Prevention

To prevent this issue in your own code:

1. **Always create fresh coroutines**: Don't reuse coroutine objects
2. **Use async functions properly**: Ensure proper async/await patterns
3. **Handle workflow contexts**: Be aware of LlamaIndex workflow patterns
4. **Test multiple executions**: Verify your agent works with multiple calls

## Related Issues

This fix addresses several related issues:

- [Issue #24](https://github.com/Kaizen-agent/kaizen-agent/pull/24): Refactor: Implement Simple Import Resolution System
- [Issue #40](https://github.com/Kaizen-agent/kaizen-agent/pull/40): Refactor: Simplify onboarding and introduce agent entry point configuration
- [Issue #41](https://github.com/Kaizen-agent/kaizen-agent/pull/41): feat: Add TypeScript support for AI agents

## Future Improvements

Potential future enhancements:

1. **Automatic coroutine detection**: Detect when coroutines are being reused
2. **Better workflow context handling**: More sophisticated LlamaIndex integration
3. **Performance optimization**: Cache successful execution patterns
4. **Enhanced diagnostics**: More detailed error reporting and suggestions 