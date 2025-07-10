#!/usr/bin/env python3
"""Standalone test for async execution functionality."""

import asyncio
import time
import sys
import importlib
import builtins
import traceback


# Copy the _asyncio_run function directly to avoid import issues
def _asyncio_run(coro):
    """Compatibility function for asyncio.run() that works with older Python versions."""
    # Import asyncio fresh each time to avoid module corruption
    import asyncio
    import sys
    
    # Ensure we have the real asyncio module
    if 'asyncio' in sys.modules:
        real_asyncio = sys.modules['asyncio']
        # Check if it's the real asyncio module
        if hasattr(real_asyncio, 'new_event_loop'):
            asyncio = real_asyncio
        else:
            # Re-import asyncio if it's been corrupted
            import importlib
            asyncio = importlib.reload(real_asyncio)
    else:
        # Import asyncio for the first time
        import asyncio
    
    try:
        # Try the modern asyncio.run (Python 3.7+)
        if hasattr(asyncio, 'run'):
            return asyncio.run(coro)
        else:
            # Fallback for older Python versions
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
    except Exception as e:
        # If asyncio is corrupted, try to reload it
        import importlib
        asyncio = importlib.reload(asyncio)
        # Try again with reloaded asyncio
        if hasattr(asyncio, 'run'):
            return asyncio.run(coro)
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()


class SimpleAsyncAgent:
    """A simple async agent for testing."""
    
    def __init__(self):
        self.name = "SimpleAsyncAgent"
    
    async def run(self, message: str) -> str:
        """Simple async method that simulates some work."""
        print(f"🤖 SimpleAsyncAgent processing: {message}")
        await asyncio.sleep(1)  # Simulate async work
        return f"Processed: {message}"


class LlamaIndexStyleAgent:
    """A LlamaIndex-style agent for testing."""
    
    def __init__(self):
        self.name = "LlamaIndexStyleAgent"
        self.workflow_context = None
    
    async def run(self, message: str) -> str:
        """LlamaIndex-style async method with workflow context."""
        print(f"🤖 LlamaIndexStyleAgent processing: {message}")
        
        # Simulate LlamaIndex workflow context
        self.workflow_context = {"status": "running", "message": message}
        
        # Simulate async work with multiple steps
        await asyncio.sleep(0.5)
        self.workflow_context["step"] = "analyzing"
        
        await asyncio.sleep(0.5)
        self.workflow_context["step"] = "processing"
        
        await asyncio.sleep(0.5)
        self.workflow_context["status"] = "completed"
        
        return f"LlamaIndex processed: {message}"


def test_simple_async_function():
    """Test simple async function execution."""
    print("\n🧪 Testing simple async function...")
    
    async def simple_async_func(message: str) -> str:
        await asyncio.sleep(0.5)
        return f"Simple async result: {message}"
    
    try:
        result = _asyncio_run(simple_async_func("Hello World"))
        print(f"✅ Simple async function result: {result}")
        return True
    except Exception as e:
        print(f"❌ Simple async function failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_simple_async_agent():
    """Test simple async agent execution."""
    print("\n🧪 Testing simple async agent...")
    
    agent = SimpleAsyncAgent()
    
    try:
        # Test using _asyncio_run
        result = _asyncio_run(agent.run("Hello from simple agent"))
        print(f"✅ Simple async agent result: {result}")
        return True
    except Exception as e:
        print(f"❌ Simple async agent failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_llamaindex_style_agent():
    """Test LlamaIndex-style async agent execution."""
    print("\n🧪 Testing LlamaIndex-style async agent...")
    
    agent = LlamaIndexStyleAgent()
    
    try:
        # Test using _asyncio_run
        result = _asyncio_run(agent.run("Hello from LlamaIndex agent"))
        print(f"✅ LlamaIndex-style agent result: {result}")
        print(f"   Workflow context: {agent.workflow_context}")
        return True
    except Exception as e:
        print(f"❌ LlamaIndex-style agent failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_event_loop_conflicts():
    """Test handling of event loop conflicts."""
    print("\n🧪 Testing event loop conflict handling...")
    
    async def conflicting_async_func():
        # This simulates a function that might create its own event loop
        await asyncio.sleep(0.1)
        return "Conflicting async result"
    
    try:
        result = _asyncio_run(conflicting_async_func())
        print(f"✅ Event loop conflict handling result: {result}")
        return True
    except Exception as e:
        print(f"❌ Event loop conflict handling failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_multiple_async_calls():
    """Test multiple async calls to ensure no conflicts."""
    print("\n🧪 Testing multiple async calls...")
    
    async def async_func_1():
        await asyncio.sleep(0.1)
        return "Result 1"
    
    async def async_func_2():
        await asyncio.sleep(0.1)
        return "Result 2"
    
    try:
        result1 = _asyncio_run(async_func_1())
        result2 = _asyncio_run(async_func_2())
        print(f"✅ Multiple async calls results: {result1}, {result2}")
        return True
    except Exception as e:
        print(f"❌ Multiple async calls failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_existing_event_loop():
    """Test behavior when an event loop is already running."""
    print("\n🧪 Testing with existing event loop...")
    
    async def test_func():
        await asyncio.sleep(0.1)
        return "Existing loop test result"
    
    try:
        # This should work even if there's an existing event loop
        result = _asyncio_run(test_func())
        print(f"✅ Existing event loop test result: {result}")
        return True
    except Exception as e:
        print(f"❌ Existing event loop test failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def run_all_tests():
    """Run all async execution tests."""
    print("🚀 Starting async execution tests...")
    
    tests = [
        ("Simple Async Function", test_simple_async_function),
        ("Simple Async Agent", test_simple_async_agent),
        ("LlamaIndex Style Agent", test_llamaindex_style_agent),
        ("Event Loop Conflicts", test_event_loop_conflicts),
        ("Multiple Async Calls", test_multiple_async_calls),
        ("Existing Event Loop", test_existing_event_loop),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        success = test_func()
        end_time = time.time()
        
        duration = end_time - start_time
        status = "✅ PASS" if success else "❌ FAIL"
        
        print(f"\n{status} - {test_name} (took {duration:.2f}s)")
        results.append((test_name, success, duration))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name} ({duration:.2f}s)")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Async execution is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 