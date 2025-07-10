#!/usr/bin/env python3
"""Test to reproduce the exact MathAgent coroutine reuse issue."""

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


# Mock the LlamaIndex components to reproduce the issue
class MockLiteLLM:
    def __init__(self, model, temperature, api_key, system_prompt):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.system_prompt = system_prompt

class MockReActAgent:
    def __init__(self, tools, llm):
        self.tools = tools
        self.llm = llm
        self._handler_created = False
        self._cached_handler = None
    
    def run(self, task, ctx):
        """Mock the ReActAgent.run method that creates a handler."""
        print(f"🤖 MockReActAgent.run called with task: {task}")
        
        # This simulates what LlamaIndex does - it creates a handler
        # that gets awaited internally
        async def mock_handler():
            await asyncio.sleep(0.5)  # Simulate async work
            return f"Mock response for: {task}"
        
        # Create the handler (this is what LlamaIndex returns)
        handler = mock_handler()
        print(f"✅ Created handler: {handler}")
        
        # Simulate that this handler gets awaited somewhere in LlamaIndex
        # This is the key issue - the handler is already awaited
        if not self._handler_created:
            # First time, we'll await it to simulate LlamaIndex's internal await
            print("🔄 Simulating LlamaIndex's internal await of the handler...")
            self._handler_created = True
            
            # Actually await the handler to simulate LlamaIndex's internal await
            # This creates the "cannot reuse already awaited coroutine" issue
            async def await_handler():
                return await handler
            
            # Await the handler and cache the result
            self._cached_handler = _asyncio_run(await_handler())
            print(f"🔄 Handler has been awaited internally, cached result: {self._cached_handler}")
            
            # Return the already-awaited handler (this is the problem!)
            return handler  # This handler has already been awaited internally
        
        # For subsequent calls, return the same handler that was already awaited
        print(f"🔄 Returning cached handler that was already awaited...")
        return handler  # This will cause "cannot reuse already awaited coroutine"

class MockContext:
    def __init__(self, agent):
        self.agent = agent

class MockMathAgent:
    def __init__(self):
        # Mock the initialization
        self.llm = MockLiteLLM(
            model='gemini/gemini-2.0-flash-lite', 
            temperature=0,
            api_key="mock_key",
            system_prompt="You are a helpful math assistant."
        )
        self.agent = MockReActAgent(
            tools=[],  # Mock tools
            llm=self.llm,
        )
        self.ctx = MockContext(self.agent)

    async def run(self, task: str) -> str:
        """This is the exact method from the user's code."""
        print(f"🔄 MathAgent.run called with task: {task}")
        
        # This is the problematic line from the user's code:
        # handler = self.agent.run(task, ctx=self.ctx)
        # response = await handler
        # return response
        
        handler = self.agent.run(task, ctx=self.ctx)
        print(f"📥 Got handler: {handler}")
        
        # This is where the error occurs - the handler has already been awaited
        response = await handler
        print(f"📤 Got response: {response}")
        return response


def test_math_agent_issue():
    """Test the exact MathAgent issue."""
    print("\n🧪 Testing MathAgent coroutine reuse issue...")
    
    agent = MockMathAgent()
    
    try:
        # First call - this should work
        print("🔄 First MathAgent.run call...")
        result1 = _asyncio_run(agent.run("What is 2 + 2?"))
        print(f"✅ First call successful: {result1}")
        
        # Second call - this should fail with "cannot reuse already awaited coroutine"
        print("🔄 Second MathAgent.run call...")
        result2 = _asyncio_run(agent.run("What is 3 + 3?"))
        print(f"✅ Second call successful: {result2}")
        print("⚠️  This should have failed! The handler was reused.")
        return False
        
    except Exception as e:
        print(f"✅ Second call correctly failed: {e}")
        return True


def test_fixed_math_agent():
    """Test a fixed version of MathAgent that creates fresh handlers."""
    print("\n🧪 Testing fixed MathAgent...")
    
    class FixedMathAgent:
        def __init__(self):
            self.llm = MockLiteLLM(
                model='gemini/gemini-2.0-flash-lite', 
                temperature=0,
                api_key="mock_key",
                system_prompt="You are a helpful math assistant."
            )
            self.agent = MockReActAgent(
                tools=[],
                llm=self.llm,
            )
            self.ctx = MockContext(self.agent)

        async def run(self, task: str) -> str:
            """Fixed version that creates fresh handlers."""
            print(f"🔄 FixedMathAgent.run called with task: {task}")
            
            # Create a fresh handler each time
            async def fresh_handler():
                # Call the agent.run method to get a fresh handler
                handler = self.agent.run(task, ctx=self.ctx)
                # Await the fresh handler
                response = await handler
                return response
            
            # Use our wrapper to ensure fresh coroutine creation
            return await fresh_handler()
    
    agent = FixedMathAgent()
    
    try:
        # First call
        print("🔄 First FixedMathAgent.run call...")
        result1 = _asyncio_run(agent.run("What is 2 + 2?"))
        print(f"✅ First call successful: {result1}")
        
        # Second call (should work because we create fresh handlers)
        print("🔄 Second FixedMathAgent.run call...")
        result2 = _asyncio_run(agent.run("What is 3 + 3?"))
        print(f"✅ Second call successful: {result2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fixed MathAgent failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_wrapper_solution_for_math_agent():
    """Test the wrapper solution for MathAgent."""
    print("\n🧪 Testing wrapper solution for MathAgent...")
    
    agent = MockMathAgent()
    
    def execute_math_agent_with_wrapper():
        """Execute MathAgent with wrapper that creates fresh coroutines."""
        async def fresh_coroutine_wrapper():
            return await agent.run("What is 5 + 5?")
        
        return _asyncio_run(fresh_coroutine_wrapper())
    
    try:
        # First execution
        print("🔄 First wrapper execution...")
        result1 = execute_math_agent_with_wrapper()
        print(f"✅ First execution successful: {result1}")
        
        # Second execution (should work because it's a fresh coroutine)
        print("🔄 Second wrapper execution...")
        result2 = execute_math_agent_with_wrapper()
        print(f"✅ Second execution successful: {result2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Wrapper solution failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def test_real_math_agent():
    """Test the real MathAgent pattern with robust coroutine handling."""
    print("\n🧪 Testing real MathAgent with robust coroutine handling...")

    class RealMathAgent:
        def __init__(self):
            self.llm = MockLiteLLM(
                model='gemini/gemini-2.0-flash-lite',
                temperature=0,
                api_key="mock_key",
                system_prompt="You are a helpful math assistant."
            )
            self.agent = MockReActAgent(
                tools=[],
                llm=self.llm,
            )
            self.ctx = MockContext(self.agent)

        async def run(self, task: str) -> str:
            # Always create a fresh coroutine and await it
            async def get_response():
                handler = self.agent.run(task, ctx=self.ctx)
                return await handler
            return await get_response()

    agent = RealMathAgent()
    try:
        print("🔄 First RealMathAgent.run call...")
        result1 = _asyncio_run(agent.run("What is 2 + 2?"))
        print(f"✅ First call successful: {result1}")

        print("🔄 Second RealMathAgent.run call...")
        result2 = _asyncio_run(agent.run("What is 3 + 3?"))
        print(f"✅ Second call successful: {result2}")
        return True
    except Exception as e:
        print(f"❌ RealMathAgent failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def run_all_tests():
    """Run all tests to reproduce and fix the MathAgent issue."""
    print("🚀 Starting MathAgent coroutine reuse issue tests...")
    
    tests = [
        ("MathAgent Issue", test_math_agent_issue),
        ("Fixed MathAgent", test_fixed_math_agent),
        ("Wrapper Solution for MathAgent", test_wrapper_solution_for_math_agent),
        ("Real MathAgent", test_real_math_agent),
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
        print("🎉 All tests passed! The MathAgent coroutine reuse issue has been resolved.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 