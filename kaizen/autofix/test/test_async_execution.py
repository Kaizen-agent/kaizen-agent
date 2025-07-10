#!/usr/bin/env python3
"""Test async execution functionality."""

import asyncio
import time
import sys
from pathlib import Path
from typing import Any, List

# Add the parent directory to sys.path to import the modules
sys.path.insert(0, str(Path(__file__).parent))

from code_region import CodeRegionExecutor, RegionInfo, AgentEntryPoint, RegionType
from input_parser import InputParser


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


def create_test_region_info(agent_class: type, class_name: str) -> RegionInfo:
    """Create a test RegionInfo object."""
    # Create the code for the agent
    code = f"""
import asyncio

class {class_name}:
    def __init__(self):
        self.name = "{class_name}"
    
    async def run(self, message: str) -> str:
        print(f"🤖 {{self.name}} processing: {{message}}")
        await asyncio.sleep(1)
        return f"Processed: {{message}}"
"""
    
    return RegionInfo(
        type=RegionType.CLASS,
        name=class_name,
        code=code,
        start_line=1,
        end_line=len(code.split('\n')),
        imports=[],
        dependencies=frozenset(),
        class_methods=['run'],
        file_path=Path(__file__),
        entry_point=AgentEntryPoint(
            module='test_agent',
            class_name=class_name,
            method='run',
            fallback_to_function=True
        )
    )


def test_simple_async_function():
    """Test simple async function execution."""
    print("\n🧪 Testing simple async function...")
    
    async def simple_async_func(message: str) -> str:
        await asyncio.sleep(0.5)
        return f"Simple async result: {message}"
    
    # Test the _asyncio_run function directly
    from code_region import _asyncio_run
    
    try:
        result = _asyncio_run(simple_async_func("Hello World"))
        print(f"✅ Simple async function result: {result}")
        return True
    except Exception as e:
        print(f"❌ Simple async function failed: {e}")
        return False


def test_simple_async_agent():
    """Test simple async agent execution."""
    print("\n🧪 Testing simple async agent...")
    
    agent = SimpleAsyncAgent()
    
    try:
        # Test using asyncio.run directly
        result = asyncio.run(agent.run("Hello from simple agent"))
        print(f"✅ Simple async agent result: {result}")
        return True
    except Exception as e:
        print(f"❌ Simple async agent failed: {e}")
        return False


def test_llamaindex_style_agent():
    """Test LlamaIndex-style async agent execution."""
    print("\n🧪 Testing LlamaIndex-style async agent...")
    
    agent = LlamaIndexStyleAgent()
    
    try:
        # Test using asyncio.run directly
        result = asyncio.run(agent.run("Hello from LlamaIndex agent"))
        print(f"✅ LlamaIndex-style agent result: {result}")
        print(f"   Workflow context: {agent.workflow_context}")
        return True
    except Exception as e:
        print(f"❌ LlamaIndex-style agent failed: {e}")
        return False


def test_code_region_executor():
    """Test the CodeRegionExecutor with async functions."""
    print("\n🧪 Testing CodeRegionExecutor with async functions...")
    
    # Create executor
    executor = CodeRegionExecutor(workspace_root=Path(__file__).parent)
    
    # Test with simple async agent
    simple_region = create_test_region_info(SimpleAsyncAgent, "TestSimpleAgent")
    
    try:
        result = executor._execute_llamaindex_async_function(
            func=lambda x: SimpleAsyncAgent().run(x),
            input_data=["Hello from executor"],
            region_info=simple_region
        )
        print(f"✅ CodeRegionExecutor simple agent result: {result}")
        return True
    except Exception as e:
        print(f"❌ CodeRegionExecutor simple agent failed: {e}")
        return False


def test_llamaindex_async_execution():
    """Test the LlamaIndex async execution specifically."""
    print("\n🧪 Testing LlamaIndex async execution...")
    
    # Create executor
    executor = CodeRegionExecutor(workspace_root=Path(__file__).parent)
    
    # Test with LlamaIndex-style agent
    llamaindex_region = create_test_region_info(LlamaIndexStyleAgent, "TestLlamaIndexAgent")
    
    try:
        result = executor._execute_llamaindex_async_function(
            func=lambda x: LlamaIndexStyleAgent().run(x),
            input_data=["Hello from LlamaIndex executor"],
            region_info=llamaindex_region
        )
        print(f"✅ CodeRegionExecutor LlamaIndex agent result: {result}")
        return True
    except Exception as e:
        print(f"❌ CodeRegionExecutor LlamaIndex agent failed: {e}")
        return False


def test_event_loop_conflicts():
    """Test handling of event loop conflicts."""
    print("\n🧪 Testing event loop conflict handling...")
    
    async def conflicting_async_func():
        # This simulates a function that might create its own event loop
        await asyncio.sleep(0.1)
        return "Conflicting async result"
    
    try:
        # Test the _asyncio_run function with potential conflicts
        from code_region import _asyncio_run
        
        result = _asyncio_run(conflicting_async_func())
        print(f"✅ Event loop conflict handling result: {result}")
        return True
    except Exception as e:
        print(f"❌ Event loop conflict handling failed: {e}")
        return False


def run_all_tests():
    """Run all async execution tests."""
    print("🚀 Starting async execution tests...")
    
    tests = [
        ("Simple Async Function", test_simple_async_function),
        ("Simple Async Agent", test_simple_async_agent),
        ("LlamaIndex Style Agent", test_llamaindex_style_agent),
        ("CodeRegionExecutor Simple", test_code_region_executor),
        ("CodeRegionExecutor LlamaIndex", test_llamaindex_async_execution),
        ("Event Loop Conflicts", test_event_loop_conflicts),
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