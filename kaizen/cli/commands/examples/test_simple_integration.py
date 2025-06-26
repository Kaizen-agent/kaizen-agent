"""Simple integration test to verify dependency management works with actual test configuration."""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dependency_manager import DependencyManager
import logging

def test_simple_dependency_import():
    """Test that dependencies are properly imported for the summarizer agent."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create dependency manager
    manager = DependencyManager()
    
    # Test importing the referenced files from the test configuration
    config_path = Path("../../examples/summarizer_agent/test_config.yaml")
    referenced_files = ["prompt.py", "utils.py"]
    
    print("Testing dependency import for summarizer agent...")
    
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
            
        # List all imported modules
        print(f"   Imported modules: {list(namespace.keys())}")
        
    else:
        print(f"❌ Dependency import failed: {import_result.error}")
        return False
    
    # Cleanup
    manager.cleanup()
    
    print("\n🎉 Simple integration test completed!")
    return True

if __name__ == "__main__":
    success = test_simple_dependency_import()
    if not success:
        sys.exit(1) 