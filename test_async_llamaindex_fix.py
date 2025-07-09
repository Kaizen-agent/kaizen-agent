#!/usr/bin/env python3
"""Test the improved async handling for LlamaIndex agents."""

import asyncio
import sys
import os
from pathlib import Path

# Add the kaizen package to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.autofix.test.code_region import (
    CodeRegionExecutor, 
    RegionInfo, 
    AgentEntryPoint, 
    RegionType
)

def create_test_async_agent():
    """Create a test async LlamaIndex agent."""
    return '''
import asyncio
from typing import Any, List

class AsyncTestAgent:
    """A simple async test agent for LlamaIndex."""
    
    def __init__(self):
        self.name = "AsyncTestAgent"
        self.counter = 0
    
    async def process_message(self, message: str) -> str:
        """Process a message asynchronously."""
        await asyncio.sleep(0.1)  # Simulate async work
        self.counter += 1
        return f"Processed message {self.counter}: {message}"
    
    async def run(self, input_data: List[Any]) -> str:
        """Main async method to run the agent."""
        if not input_data:
            return "No input provided"
        
        message = str(input_data[0])
        result = await self.process_message(message)
        return f"Agent result: {result}"

# Create an instance
async_agent = AsyncTestAgent()
'''

def create_test_sync_agent():
    """Create a test sync LlamaIndex agent."""
    return '''
from typing import Any, List

class SyncTestAgent:
    """A simple sync test agent for LlamaIndex."""
    
    def __init__(self):
        self.name = "SyncTestAgent"
        self.counter = 0
    
    def process_message(self, message: str) -> str:
        """Process a message synchronously."""
        self.counter += 1
        return f"Processed message {self.counter}: {message}"
    
    def run(self, input_data: List[Any]) -> str:
        """Main sync method to run the agent."""
        if not input_data:
            return "No input provided"
        
        message = str(input_data[0])
        result = self.process_message(message)
        return f"Agent result: {result}"

# Create an instance
sync_agent = SyncTestAgent()
'''

def create_test_async_function():
    """Create a test async function."""
    return '''
import asyncio
from typing import Any, List

async def async_test_function(input_data: List[Any]) -> str:
    """A simple async test function."""
    await asyncio.sleep(0.1)  # Simulate async work
    if not input_data:
        return "No input provided"
    
    message = str(input_data[0])
    return f"Async function result: {message}"
'''

def create_test_sync_function():
    """Create a test sync function."""
    return '''
from typing import Any, List

def sync_test_function(input_data: List[Any]) -> str:
    """A simple sync test function."""
    if not input_data:
        return "No input provided"
    
    message = str(input_data[0])
    return f"Sync function result: {message}"
'''

def test_async_agent_execution():
    """Test async agent execution."""
    print("🧪 Testing async agent execution...")
    
    # Create executor
    executor = CodeRegionExecutor(Path.cwd())
    
    # Create region info for async agent
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="async_test_agent",
        code=create_test_async_agent(),
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=Path("test_async_agent.py"),
        entry_point=AgentEntryPoint(
            module="test_async_agent",
            class_name="AsyncTestAgent",
            method="run"
        )
    )
    
    # Test execution
    try:
        result = executor._execute_llamaindex_agent(
            region_info, 
            ["Hello, async world!"], 
            set()
        )
        
        print(f"✅ Async agent execution successful!")
        print(f"   Result: {result['result']}")
        print(f"   Tracked variables: {result['tracked_variables']}")
        return True
        
    except Exception as e:
        print(f"❌ Async agent execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_agent_execution():
    """Test sync agent execution."""
    print("🧪 Testing sync agent execution...")
    
    # Create executor
    executor = CodeRegionExecutor(Path.cwd())
    
    # Create region info for sync agent
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="sync_test_agent",
        code=create_test_sync_agent(),
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=Path("test_sync_agent.py"),
        entry_point=AgentEntryPoint(
            module="test_sync_agent",
            class_name="SyncTestAgent",
            method="run"
        )
    )
    
    # Test execution
    try:
        result = executor._execute_llamaindex_agent(
            region_info, 
            ["Hello, sync world!"], 
            set()
        )
        
        print(f"✅ Sync agent execution successful!")
        print(f"   Result: {result['result']}")
        print(f"   Tracked variables: {result['tracked_variables']}")
        return True
        
    except Exception as e:
        print(f"❌ Sync agent execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_async_function_execution():
    """Test async function execution."""
    print("🧪 Testing async function execution...")
    
    # Create executor
    executor = CodeRegionExecutor(Path.cwd())
    
    # Create region info for async function
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="async_test_function",
        code=create_test_async_function(),
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=Path("test_async_function.py"),
        entry_point=AgentEntryPoint(
            module="test_async_function",
            method="async_test_function"
        )
    )
    
    # Test execution
    try:
        result = executor._execute_llamaindex_agent(
            region_info, 
            ["Hello, async function!"], 
            set()
        )
        
        print(f"✅ Async function execution successful!")
        print(f"   Result: {result['result']}")
        print(f"   Tracked variables: {result['tracked_variables']}")
        return True
        
    except Exception as e:
        print(f"❌ Async function execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_function_execution():
    """Test sync function execution."""
    print("🧪 Testing sync function execution...")
    
    # Create executor
    executor = CodeRegionExecutor(Path.cwd())
    
    # Create region info for sync function
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="sync_test_function",
        code=create_test_sync_function(),
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=Path("test_sync_function.py"),
        entry_point=AgentEntryPoint(
            module="test_sync_function",
            method="sync_test_function"
        )
    )
    
    # Test execution
    try:
        result = executor._execute_llamaindex_agent(
            region_info, 
            ["Hello, sync function!"], 
            set()
        )
        
        print(f"✅ Sync function execution successful!")
        print(f"   Result: {result['result']}")
        print(f"   Tracked variables: {result['tracked_variables']}")
        return True
        
    except Exception as e:
        print(f"❌ Sync function execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_async_execution_in_existing_loop():
    """Test async execution when already in an event loop."""
    print("🧪 Testing async execution in existing event loop...")
    
    async def run_test():
        # Create executor
        executor = CodeRegionExecutor(Path.cwd())
        
        # Create region info for async agent
        region_info = RegionInfo(
            type=RegionType.MODULE,
            name="async_test_agent",
            code=create_test_async_agent(),
            start_line=1,
            end_line=1,
            imports=[],
            dependencies=frozenset(),
            file_path=Path("test_async_agent.py"),
            entry_point=AgentEntryPoint(
                module="test_async_agent",
                class_name="AsyncTestAgent",
                method="run"
            )
        )
        
        # Test execution within existing event loop
        try:
            result = executor._execute_llamaindex_agent(
                region_info, 
                ["Hello from existing loop!"], 
                set()
            )
            
            print(f"✅ Async execution in existing loop successful!")
            print(f"   Result: {result['result']}")
            return True
            
        except Exception as e:
            print(f"❌ Async execution in existing loop failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run the test in an event loop
    return asyncio.run(run_test())

def main():
    """Run all tests."""
    print("🚀 Starting async LlamaIndex execution tests...")
    print("=" * 60)
    
    tests = [
        ("Sync Function", test_sync_function_execution),
        ("Sync Agent", test_sync_agent_execution),
        ("Async Function", test_async_function_execution),
        ("Async Agent", test_async_agent_execution),
        ("Async in Existing Loop", test_async_execution_in_existing_loop),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Async handling is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 