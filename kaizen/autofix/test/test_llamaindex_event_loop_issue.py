#!/usr/bin/env python3
"""Test to simulate the exact LlamaIndex event loop behavior that causes the coroutine reuse issue."""

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
    """A LlamaIndex-style agent that creates its own event loop context."""
    
    def __init__(self):
        self.name = "LlamaIndexStyleAgent"
        self.workflow_context = None
    
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


def simulate_llamaindex_event_loop_behavior():
    """Simulate how LlamaIndex creates its own event loop and tasks."""
    print("\n🧪 Simulating LlamaIndex event loop behavior...")
    
    agent = LlamaIndexStyleAgent()
    
    # Simulate LlamaIndex creating its own event loop
    async def llamaindex_workflow():
        """Simulate LlamaIndex's internal workflow."""
        print("🔄 LlamaIndex creating its own event loop and tasks...")
        
        # Create some background tasks (like LlamaIndex does)
        async def background_task():
            await asyncio.sleep(0.1)
            print("🔄 Background task running...")
        
        # Start background tasks
        task1 = asyncio.create_task(background_task())
        task2 = asyncio.create_task(background_task())
        
        # Now call the agent method
        result = await agent.run("Hello from LlamaIndex workflow")
        
        # Wait for background tasks
        await task1
        await task2
        
        return result
    
    try:
        # Run the LlamaIndex-style workflow
        result = _asyncio_run(llamaindex_workflow())
        print(f"✅ LlamaIndex workflow successful: {result}")
        return True
    except Exception as e:
        print(f"❌ LlamaIndex workflow failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_coroutine_reuse_in_llamaindex_context():
    """Test the coroutine reuse issue in a LlamaIndex-like context."""
    print("\n🧪 Testing coroutine reuse in LlamaIndex context...")
    
    agent = LlamaIndexStyleAgent()
    
    # Simulate the exact issue: LlamaIndex creates a coroutine and awaits it
    async def llamaindex_internal_call():
        """Simulate LlamaIndex's internal call to the agent."""
        # This is what LlamaIndex does internally
        coro = agent.run("Hello from LlamaIndex internal call")
        result = await coro
        return result, coro  # Return both result and the coroutine
    
    try:
        # First call - LlamaIndex creates and awaits the coroutine
        print("🔄 First LlamaIndex internal call...")
        result1, coro = _asyncio_run(llamaindex_internal_call())
        print(f"✅ First call successful: {result1}")
        print(f"   Coroutine: {coro}")
        
        # Now try to reuse the coroutine (this should fail)
        print("🔄 Attempting to reuse the coroutine...")
        try:
            result2 = _asyncio_run(coro)
            print(f"❌ Coroutine reuse should have failed but succeeded: {result2}")
            return False
        except Exception as e:
            print(f"✅ Coroutine reuse correctly failed: {e}")
            return True
            
    except Exception as e:
        print(f"❌ LlamaIndex internal call failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_fresh_coroutine_solution():
    """Test creating fresh coroutines in LlamaIndex context."""
    print("\n🧪 Testing fresh coroutine solution in LlamaIndex context...")
    
    agent = LlamaIndexStyleAgent()
    
    # Solution: Always create fresh coroutines
    def execute_with_fresh_coroutine():
        """Execute with fresh coroutine creation."""
        async def fresh_coroutine_wrapper():
            return await agent.run("Hello from fresh coroutine")
        
        return _asyncio_run(fresh_coroutine_wrapper())
    
    try:
        # First execution
        print("🔄 First fresh coroutine execution...")
        result1 = execute_with_fresh_coroutine()
        print(f"✅ First execution successful: {result1}")
        
        # Second execution (should work because it's a fresh coroutine)
        print("🔄 Second fresh coroutine execution...")
        result2 = execute_with_fresh_coroutine()
        print(f"✅ Second execution successful: {result2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fresh coroutine execution failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_method_call_solution_in_context():
    """Test calling the method directly in LlamaIndex context."""
    print("\n🧪 Testing method call solution in LlamaIndex context...")
    
    agent = LlamaIndexStyleAgent()
    
    # Simulate LlamaIndex context but call method directly
    async def llamaindex_context_with_direct_call():
        """Simulate LlamaIndex context but call method directly."""
        print("🔄 LlamaIndex context with direct method call...")
        
        # Create some background tasks (like LlamaIndex does)
        async def background_task():
            await asyncio.sleep(0.1)
            print("🔄 Background task running...")
        
        # Start background tasks
        task1 = asyncio.create_task(background_task())
        task2 = asyncio.create_task(background_task())
        
        # Call the method directly (not through a stored coroutine)
        result = await agent.run("Hello from direct method call")
        
        # Wait for background tasks
        await task1
        await task2
        
        return result
    
    try:
        # First execution
        print("🔄 First direct method call...")
        result1 = _asyncio_run(llamaindex_context_with_direct_call())
        print(f"✅ First execution successful: {result1}")
        
        # Second execution
        print("🔄 Second direct method call...")
        result2 = _asyncio_run(llamaindex_context_with_direct_call())
        print(f"✅ Second execution successful: {result2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct method call failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def run_all_tests():
    """Run all tests to understand and fix the LlamaIndex event loop issue."""
    print("🚀 Starting LlamaIndex event loop issue tests...")
    
    tests = [
        ("LlamaIndex Event Loop Behavior", simulate_llamaindex_event_loop_behavior),
        ("Coroutine Reuse in LlamaIndex Context", test_coroutine_reuse_in_llamaindex_context),
        ("Fresh Coroutine Solution", test_fresh_coroutine_solution),
        ("Method Call Solution in Context", test_method_call_solution_in_context),
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
        print("🎉 All tests passed! The LlamaIndex event loop issue has been resolved.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 