"""Test to verify that functions are properly extracted from imported modules."""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dependency_manager import DependencyManager
import logging

def test_function_extraction():
    """Test that functions are properly extracted from imported modules."""
    
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Create dependency manager
    manager = DependencyManager()
    
    # Test importing the referenced files from the test configuration
    config_path = Path("../../test_agent/summarizer_agent/test_config.yaml")
    referenced_files = ["prompt.py", "utils.py"]
    
    print("Testing function extraction from imported modules...")
    
    # Import dependencies
    import_result = manager.import_dependencies(
        dependencies=[],  # No package dependencies in this test
        referenced_files=referenced_files,
        config_path=config_path
    )
    
    if import_result.is_success:
        print("✅ Dependency import successful")
        
        # Check what was imported
        namespace = import_result.value.namespace
        print(f"   Namespace contains {len(namespace)} items")
        
        # Check for specific modules
        if 'prompt' in namespace:
            print("   ✅ prompt module imported")
        else:
            print("   ❌ prompt module not found")
            
        if 'utils' in namespace:
            print("   ✅ utils module imported")
        else:
            print("   ❌ utils module not found")
        
        # Check for specific functions
        if 'get_prompt' in namespace:
            print("   ✅ get_prompt function extracted")
            # Test the function
            try:
                result = namespace['get_prompt']("test text")
                print(f"   ✅ get_prompt function works: {result}")
            except Exception as e:
                print(f"   ❌ get_prompt function failed: {e}")
        else:
            print("   ❌ get_prompt function not found")
            
        if 'call_gemini_llm' in namespace:
            print("   ✅ call_gemini_llm function extracted")
        else:
            print("   ❌ call_gemini_llm function not found")
            
        # List all callable functions
        functions = [name for name, obj in namespace.items() if callable(obj) and not name.startswith('_')]
        print(f"   Available functions: {functions}")
        
        # List all imported modules
        modules = [name for name, obj in namespace.items() if hasattr(obj, '__file__') or hasattr(obj, '__name__')]
        print(f"   Imported modules: {modules}")
        
    else:
        print(f"❌ Dependency import failed: {import_result.error}")
        return False
    
    # Cleanup
    manager.cleanup()
    
    print("\n🎉 Function extraction test completed!")
    return True

if __name__ == "__main__":
    success = test_function_extraction()
    if not success:
        sys.exit(1) 