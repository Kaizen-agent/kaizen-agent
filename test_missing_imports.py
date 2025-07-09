#!/usr/bin/env python3
"""Test the improved error handling for missing imports."""

import os
from pathlib import Path
from kaizen.autofix.test.code_region import (
    CodeRegionExecutor, 
    CodeRegionExtractor,
    RegionInfo, 
    AgentEntryPoint, 
    RegionType
)

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def test_missing_imports():
    """Test that missing imports are handled gracefully."""
    print("🧪 Testing missing import handling...")
    
    # Create test directory
    test_dir = Path("test_missing_imports")
    test_dir.mkdir(exist_ok=True)
    
    # Create agent file with missing import
    agent_path = test_dir / "agent.py"
    agent_code = '''
# This import will fail because llama_index.llms.gemini doesn't exist
from llama_index.llms.gemini import Gemini

class TestAgent:
    def __init__(self):
        # This will fail if the import above fails
        try:
            self.llm = Gemini()
        except:
            self.llm = None
    
    def run(self, x):
        if self.llm is None:
            return f"Mock response: {x}"
        else:
            return f"Real response: {x}"
'''
    write_file(agent_path, agent_code)
    
    # Test validation (should pass now)
    extractor = CodeRegionExtractor(test_dir)
    entry_point = AgentEntryPoint(
        module="agent",
        class_name="TestAgent",
        method="run"
    )
    
    print("🔍 Testing validation...")
    validation_result = extractor.validate_entry_point(entry_point, agent_path)
    print(f"   Validation result: {validation_result}")
    assert validation_result, "Validation should pass even with missing imports"
    
    # Test execution
    print("🚀 Testing execution...")
    executor = CodeRegionExecutor(test_dir)
    
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="agent",
        code=agent_code,
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=agent_path,
        entry_point=entry_point
    )
    
    try:
        result = executor._execute_llamaindex_agent(region_info, ["test input"], set())
        print(f"   Execution result: {result['result']}")
        # The test should work regardless of whether the import succeeds or fails
        assert "response" in str(result['result']), "Should return some kind of response"
        print("✅ Missing import test passed!")
        
    except Exception as e:
        print(f"❌ Execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Cleanup
    try:
        agent_path.unlink()
        test_dir.rmdir()
    except Exception:
        pass
    
    return True

def test_complex_missing_imports():
    """Test more complex missing import scenarios."""
    print("🧪 Testing complex missing import scenarios...")
    
    # Create test directory
    test_dir = Path("test_complex_missing_imports")
    test_dir.mkdir(exist_ok=True)
    
    # Create agent file with multiple missing imports
    agent_path = test_dir / "agent.py"
    agent_code = '''
# Multiple missing imports
from llama_index.llms.gemini import Gemini
from llama_index.llms.openai import OpenAI
from nonexistent_module import SomeClass
import another_missing_module

class ComplexAgent:
    def __init__(self):
        self.llms = {}
        try:
            self.llms['gemini'] = Gemini()
        except:
            self.llms['gemini'] = None
        
        try:
            self.llms['openai'] = OpenAI()
        except:
            self.llms['openai'] = None
    
    def run(self, x):
        responses = []
        for name, llm in self.llms.items():
            if llm is None:
                responses.append(f"Mock {name}: {x}")
            else:
                responses.append(f"Real {name}: {x}")
        
        return " | ".join(responses)
'''
    write_file(agent_path, agent_code)
    
    # Test execution
    print("🚀 Testing complex execution...")
    executor = CodeRegionExecutor(test_dir)
    
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="agent",
        code=agent_code,
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=agent_path,
        entry_point=AgentEntryPoint(
            module="agent",
            class_name="ComplexAgent",
            method="run"
        )
    )
    
    try:
        result = executor._execute_llamaindex_agent(region_info, ["test input"], set())
        print(f"   Execution result: {result['result']}")
        # The test should work regardless of whether the imports succeed or fail
        assert "response" in str(result['result']) or "Mock" in str(result['result']) or "Real" in str(result['result']), "Should return some kind of response"
        print("✅ Complex missing import test passed!")
        
    except Exception as e:
        print(f"❌ Complex execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Cleanup
    try:
        agent_path.unlink()
        test_dir.rmdir()
    except Exception:
        pass
    
    return True

def test_definitely_missing_imports():
    """Test with definitely missing imports that should trigger mock creation."""
    print("🧪 Testing definitely missing imports...")
    
    # Create test directory
    test_dir = Path("test_definitely_missing_imports")
    test_dir.mkdir(exist_ok=True)
    
    # Create agent file with definitely missing imports
    agent_path = test_dir / "agent.py"
    agent_code = '''
# These imports should definitely fail
from definitely_nonexistent_module import DefinitelyMissingClass
import another_definitely_missing_module

class DefinitelyMissingAgent:
    def __init__(self):
        try:
            self.missing_class = DefinitelyMissingClass()
        except:
            self.missing_class = None
    
    def run(self, x):
        if self.missing_class is None:
            return f"Handled missing import gracefully: {x}"
        else:
            return f"Unexpected success: {x}"
'''
    write_file(agent_path, agent_code)
    
    # Test execution
    print("🚀 Testing definitely missing imports...")
    executor = CodeRegionExecutor(test_dir)
    
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="agent",
        code=agent_code,
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=agent_path,
        entry_point=AgentEntryPoint(
            module="agent",
            class_name="DefinitelyMissingAgent",
            method="run"
        )
    )
    
    try:
        result = executor._execute_llamaindex_agent(region_info, ["test input"], set())
        print(f"   Execution result: {result['result']}")
        assert "Handled missing import gracefully" in str(result['result']), "Should handle definitely missing imports"
        print("✅ Definitely missing import test passed!")
        
    except Exception as e:
        print(f"❌ Definitely missing import execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Cleanup
    try:
        agent_path.unlink()
        test_dir.rmdir()
    except Exception:
        pass
    
    return True

def main():
    """Run all missing import tests."""
    print("🚀 Starting missing import handling tests...")
    print("=" * 60)
    
    tests = [
        ("Basic Missing Import", test_missing_imports),
        ("Complex Missing Imports", test_complex_missing_imports),
        ("Definitely Missing Imports", test_definitely_missing_imports),
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
        print("🎉 All tests passed! Missing import handling is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 