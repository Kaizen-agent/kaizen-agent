#!/usr/bin/env python3
"""
Test file for LlamaIndex agent execution.
This demonstrates the _execute_llamaindex_agent method functionality.
"""

import os
import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the necessary modules for testing
from kaizen.autofix.test.code_region import (
    CodeRegionExecutor, 
    CodeRegionExtractor, 
    AgentEntryPoint,
    RegionInfo
)

def create_test_agent_file():
    """Create a test agent file with the user's example code."""
    test_code = '''import os
import asyncio

from dotenv import load_dotenv
from llama_index.llms.litellm import LiteLLM
from llama_index.core.agent.workflow import ReActAgent, ToolCallResult
from llama_index.core.workflow import Context


load_dotenv()
import os

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")


def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b


def add(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b


class MathAgent:
    def __init__(self):
        # Initialize the LLM and agent
        self.llm = LiteLLM(
            model='gemini/gemini-2.0-flash-lite',
            temperature=0,
            api_key=GOOGLE_API_KEY,  # Pass the API key here
        )
        self.agent = ReActAgent(
            tools=[add, multiply],  # The names of the tools/functions
            llm=self.llm,  # The LLM to be used by the agent
        )
        self.ctx = Context(self.agent)

    async def run(self, task: str) -> str:
        # Run the task and print the response
        handler = self.agent.run(task, ctx=self.ctx)
        response = await handler
        return response
        # return handler


async def main():
    math_agent = MathAgent()
    task = 'What is ten plus 30.5?'
    response = await math_agent.run(task)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    test_file_path = Path("test_math_agent.py")
    with open(test_file_path, 'w') as f:
        f.write(test_code)
    
    return test_file_path

def test_llamaindex_agent_execution():
    """Test the LlamaIndex agent execution functionality."""
    print("🧪 Testing LlamaIndex agent execution...")
    
    # Create test agent file
    test_file_path = create_test_agent_file()
    print(f"📝 Created test agent file: {test_file_path}")
    
    try:
        # Initialize the code region extractor and executor
        workspace_root = Path.cwd()
        extractor = CodeRegionExtractor(workspace_root)
        executor = CodeRegionExecutor(workspace_root)
        
        # Create entry point configuration
        entry_point = AgentEntryPoint(
            module="test_math_agent",
            class_name="MathAgent",
            method="run",
            fallback_to_function=True
        )
        
        print(f"🔧 Entry point configuration: {entry_point}")
        
        # Extract region using entry point
        region_info = extractor.extract_region_by_entry_point(test_file_path, entry_point)
        print(f"📋 Extracted region: {region_info.name} (type: {region_info.type.value})")
        
        # Test input data
        input_data = ["What is 5 plus 7?"]
        tracked_variables = set()
        
        print(f"📥 Input data: {input_data}")
        print(f"🔍 Tracked variables: {tracked_variables}")
        
        # Execute the LlamaIndex agent
        print("🚀 Executing LlamaIndex agent...")
        result = executor._execute_llamaindex_agent(region_info, input_data, tracked_variables)
        
        print("✅ Execution completed!")
        print(f"📤 Result: {result['result']}")
        print(f"🔍 Tracked values: {result['tracked_values']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Clean up test file
        try:
            test_file_path.unlink()
            print(f"🧹 Cleaned up test file: {test_file_path}")
        except:
            pass

def test_sync_function_execution():
    """Test execution of a sync function (non-async)."""
    print("\n🧪 Testing sync function execution...")
    
    # Create a simple sync function test
    sync_code = '''def simple_math(a: float, b: float) -> float:
    """Simple math function for testing."""
    return a + b

class SimpleAgent:
    def __init__(self):
        self.name = "SimpleAgent"
    
    def calculate(self, a: float, b: float) -> float:
        """Calculate the sum of two numbers."""
        return a + b
'''
    
    test_file_path = Path("test_sync_agent.py")
    with open(test_file_path, 'w') as f:
        f.write(sync_code)
    
    try:
        workspace_root = Path.cwd()
        extractor = CodeRegionExtractor(workspace_root)
        executor = CodeRegionExecutor(workspace_root)
        
        # Test sync function
        entry_point = AgentEntryPoint(
            module="test_sync_agent",
            class_name="SimpleAgent",
            method="calculate",
            fallback_to_function=True
        )
        
        region_info = extractor.extract_region_by_entry_point(test_file_path, entry_point)
        input_data = [10.5, 20.3]
        tracked_variables = set()
        
        print(f"📥 Input data: {input_data}")
        result = executor._execute_llamaindex_agent(region_info, input_data, tracked_variables)
        
        print("✅ Sync execution completed!")
        print(f"📤 Result: {result['result']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during sync execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        try:
            test_file_path.unlink()
            print(f"🧹 Cleaned up sync test file: {test_file_path}")
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting LlamaIndex agent tests...")
    
    # Test sync function first (should work without external dependencies)
    sync_result = test_sync_function_execution()
    
    # Test async LlamaIndex agent (requires external dependencies)
    print("\n" + "="*50)
    async_result = test_llamaindex_agent_execution()
    
    print("\n📊 Test Summary:")
    print(f"Sync function test: {'✅ PASSED' if sync_result else '❌ FAILED'}")
    print(f"Async LlamaIndex test: {'✅ PASSED' if async_result else '❌ FAILED'}")
    
    if not async_result:
        print("\n💡 Note: Async LlamaIndex test may fail if:")
        print("   - LlamaIndex packages are not installed")
        print("   - Required API keys are not set")
        print("   - Network connectivity issues")
        print("   - The sync function test passing indicates the framework works correctly") 