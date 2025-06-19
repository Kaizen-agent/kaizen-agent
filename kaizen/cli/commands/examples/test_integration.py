"""Integration test to verify dependency management works with test execution."""

import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dependency_manager import DependencyManager
from models.configuration import TestConfiguration
from test_commands import TestAllCommand
import logging

def test_dependency_integration():
    """Test that dependencies are properly integrated with test execution."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create a test configuration with dependencies
    config_data = {
        'name': 'Integration Test',
        'file_path': 'examples/test_file.py',
        'description': 'Test dependency integration',
        'dependencies': ['os', 'sys', 'pathlib'],
        'referenced_files': [],
        'agent_type': 'default',
        'auto_fix': False,
        'create_pr': False,
        'max_retries': 1,
        'base_branch': 'main',
        'pr_strategy': 'ANY_IMPROVEMENT',
        'regions': ['test_function'],
        'steps': [
            {
                'name': 'Test basic functionality',
                'input': {
                    'method': 'run',
                    'input': 'test input data'
                },
                'expected_output': {
                    'status': 'success'
                },
                'description': 'Test the basic functionality',
                'timeout': 30
            }
        ]
    }
    
    # Create configuration object
    config = TestConfiguration.from_dict(config_data, Path('examples/test_config_with_dependencies.yaml'))
    
    # Create test command
    command = TestAllCommand(config, logger)
    
    # Test dependency import
    print("Testing dependency import...")
    import_result = command._import_dependencies()
    
    if import_result.is_success:
        print("✅ Dependency import successful")
        if import_result.value.namespace:
            print(f"   Imported modules: {list(import_result.value.namespace.keys())}")
    else:
        print(f"❌ Dependency import failed: {import_result.error}")
        return False
    
    # Test runner config creation
    print("\nTesting runner config creation...")
    runner_config = command._create_runner_config(import_result.value.namespace)
    
    if 'imported_dependencies' in runner_config:
        print("✅ Imported dependencies added to runner config")
        print(f"   Dependencies: {list(runner_config['imported_dependencies'].keys())}")
    else:
        print("❌ Imported dependencies not found in runner config")
        return False
    
    print("\n🎉 Integration test passed!")
    return True

if __name__ == "__main__":
    success = test_dependency_integration()
    if not success:
        sys.exit(1) 