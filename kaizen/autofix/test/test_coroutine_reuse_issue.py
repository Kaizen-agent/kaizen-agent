#!/usr/bin/env python3
"""Test to reproduce and fix the 'cannot reuse already awaited coroutine' issue."""

import asyncio
import time
import sys
import traceback
from pathlib import Path

# Add the current directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

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


class LlamaIndexStyleAgent:
    """A LlamaIndex-style agent that reproduces the issue."""
    
    def __init__(self):
        self.name = "LlamaIndexStyleAgent"
        self.workflow_context = None
        self._coroutine_created = False
    
    async def run(self, message: str) -> str:
        """LlamaIndex-style async method that creates its own event loop context."""
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


def create_coroutine_reuse_issue():
    """Create the exact issue: a coroutine that gets awaited multiple times."""
    print("\n🧪 Creating coroutine reuse issue...")
    
    agent = LlamaIndexStyleAgent()
    
    # Create the coroutine
    coro = agent.run("Hello from agent")
    print(f"✅ Created coroutine: {coro}")
    
    # First await (this should work)
    try:
        print("🔄 First await attempt...")
        result1 = _asyncio_run(coro)
        print(f"✅ First await successful: {result1}")
    except Exception as e:
        print(f"❌ First await failed: {e}")
        return False
    
    # Second await (this should fail with "cannot reuse already awaited coroutine")
    try:
        print("🔄 Second await attempt...")
        result2 = _asyncio_run(coro)
        print(f"✅ Second await successful: {result2}")
        print("⚠️  This should have failed! The coroutine was reused.")
        return False
    except Exception as e:
        print(f"✅ Second await correctly failed: {e}")
        return True


def test_wrapper_solution():
    """Test the wrapper solution that creates fresh coroutines."""
    print("\n🧪 Testing wrapper solution...")
    
    agent = LlamaIndexStyleAgent()
    
    def execute_with_wrapper():
        """Wrapper function that creates fresh coroutines."""
        async def fresh_coroutine_wrapper():
            return await agent.run("Hello from wrapper")
        
        return _asyncio_run(fresh_coroutine_wrapper())
    
    # First execution
    try:
        print("🔄 First wrapper execution...")
        result1 = execute_with_wrapper()
        print(f"✅ First wrapper execution successful: {result1}")
    except Exception as e:
        print(f"❌ First wrapper execution failed: {e}")
        return False
    
    # Second execution (should work because it's a fresh coroutine)
    try:
        print("🔄 Second wrapper execution...")
        result2 = execute_with_wrapper()
        print(f"✅ Second wrapper execution successful: {result2}")
        return True
    except Exception as e:
        print(f"❌ Second wrapper execution failed: {e}")
        return False


def test_method_call_solution():
    """Test calling the method directly instead of reusing coroutines."""
    print("\n🧪 Testing method call solution...")
    
    agent = LlamaIndexStyleAgent()
    
    # First execution
    try:
        print("🔄 First method call...")
        result1 = _asyncio_run(agent.run("Hello from method call 1"))
        print(f"✅ First method call successful: {result1}")
    except Exception as e:
        print(f"❌ First method call failed: {e}")
        return False
    
    # Second execution (should work because it's a fresh method call)
    try:
        print("🔄 Second method call...")
        result2 = _asyncio_run(agent.run("Hello from method call 2"))
        print(f"✅ Second method call successful: {result2}")
        return True
    except Exception as e:
        print(f"❌ Second method call failed: {e}")
        return False


def test_llamaindex_execution_simulation():
    """Simulate the exact LlamaIndex execution pattern."""
    print("\n🧪 Testing LlamaIndex execution simulation...")
    
    agent = LlamaIndexStyleAgent()
    
    # Simulate how LlamaIndex might call the method
    def simulate_llamaindex_execution():
        """Simulate LlamaIndex's execution pattern."""
        # This is what our current _execute_llamaindex_async_function does
        async def fresh_coroutine_wrapper():
            return await agent.run("Hello from LlamaIndex simulation")
        
        return _asyncio_run(fresh_coroutine_wrapper())
    
    # First execution
    try:
        print("🔄 First LlamaIndex simulation...")
        result1 = simulate_llamaindex_execution()
        print(f"✅ First LlamaIndex simulation successful: {result1}")
    except Exception as e:
        print(f"❌ First LlamaIndex simulation failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False
    
    # Second execution
    try:
        print("🔄 Second LlamaIndex simulation...")
        result2 = simulate_llamaindex_execution()
        print(f"✅ Second LlamaIndex simulation successful: {result2}")
        return True
    except Exception as e:
        print(f"❌ Second LlamaIndex simulation failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def run_all_tests():
    """Run all tests to reproduce and fix the coroutine reuse issue."""
    print("🚀 Starting coroutine reuse issue tests...")
    
    tests = [
        ("Coroutine Reuse Issue", create_coroutine_reuse_issue),
        ("Wrapper Solution", test_wrapper_solution),
        ("Method Call Solution", test_method_call_solution),
        ("LlamaIndex Simulation", test_llamaindex_execution_simulation),
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
        print("🎉 All tests passed! The coroutine reuse issue has been resolved.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 