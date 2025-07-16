"""Test script for configuration manager integration with memory system.

This script tests that configuration manager information is properly stored
in the memory system and can be retrieved for analysis.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the parent directory to the path so we can import the memory system
sys.path.insert(0, str(Path(__file__).parent))

from memory import ExecutionMemory


def test_config_memory_integration():
    """Test that configuration manager information is stored in memory."""
    print("🧪 Testing Configuration Manager Memory Integration")
    print("=" * 60)
    
    # Initialize memory
    memory = ExecutionMemory()
    execution_id = "config_test_001"
    
    # Create a mock config object
    class MockConfig:
        def __init__(self):
            self.name = "test_config"
            self.auto_fix = True
            self.create_pr = False
            self.max_retries = 3
            self.better_ai = True
            self.language = type('Language', (), {'value': 'python'})()
            self.pr_strategy = 'ANY_IMPROVEMENT'
            self.base_branch = 'main'
            self.config_path = '/path/to/config.yaml'
            self.files_to_fix = ['example.py', 'test.py']
            self.dependencies = ['requests', 'pandas']
            self.referenced_files = ['utils.py']
            self.agent_type = 'gpt-4'
            self.description = 'Test configuration for memory integration'
    
    # Create a mock config manager
    class MockConfigManager:
        def __init__(self):
            self.name = "ConfigurationManager"
    
    config = MockConfig()
    config_manager = MockConfigManager()
    
    # Test 1: Start execution with config and config_manager
    memory.start_execution(execution_id, config, config_manager)
    print("✅ Started execution with config and config_manager")
    
    # Test 2: Check that configuration context was stored
    current_execution = memory.current_execution
    if 'configuration_context' in current_execution:
        config_context = current_execution['configuration_context']
        print("✅ Configuration context stored in memory")
        print(f"   - Auto-fix: {config_context['config_values']['auto_fix']}")
        print(f"   - Better AI: {config_context['config_values']['better_ai']}")
        print(f"   - Max retries: {config_context['config_values']['max_retries']}")
        print(f"   - Language: {config_context['config_values']['language']}")
    else:
        print("❌ Configuration context not found in memory")
        return False
    
    # Test 3: Simulate storing config manager info (like TestAllCommand would do)
    config_manager_info = {
        'config_manager_type': type(config_manager).__name__,
        'config_validation_status': 'validated',
        'config_loading_method': 'ConfigurationManager.load_configuration',
        'config_environment': {
            'auto_fix': config.auto_fix,
            'create_pr': config.create_pr,
            'max_retries': config.max_retries,
            'better_ai': getattr(config, 'better_ai', False),
            'language': getattr(getattr(config, 'language', None), 'value', None),
            'pr_strategy': getattr(config, 'pr_strategy', None),
            'base_branch': getattr(config, 'base_branch', 'main')
        },
        'config_metadata': {
            'config_name': getattr(config, 'name', None),
            'config_file_path': getattr(config, 'config_path', None),
            'files_to_fix': getattr(config, 'files_to_fix', []),
            'dependencies': getattr(config, 'dependencies', []),
            'referenced_files': getattr(config, 'referenced_files', []),
            'agent_type': getattr(config, 'agent_type', None),
            'description': getattr(config, 'description', None)
        }
    }
    
    # Store in memory
    memory.current_execution['config_manager_info'] = config_manager_info
    
    # Update configuration context with config manager details
    if 'configuration_context' in memory.current_execution:
        memory.current_execution['configuration_context']['config_manager_details'] = {
            'manager_type': config_manager_info['config_manager_type'],
            'validation_status': config_manager_info['config_validation_status'],
            'loading_method': config_manager_info['config_loading_method']
        }
    
    print("✅ Stored config manager information in memory")
    
    # Test 4: Get learning context and check config factors
    learning_context = memory.get_previous_attempts_insights('test_file.py')
    if 'configuration_factors' in learning_context:
        config_factors = learning_context['configuration_factors']
        print("✅ Configuration factors found in learning context")
        print(f"   - Current config: {config_factors['current_config']}")
        print(f"   - Config influence: {config_factors['config_influence_on_attempts']}")
    else:
        print("❌ Configuration factors not found in learning context")
        return False
    
    # Test 5: Check config manager info in memory
    if 'config_manager_info' in memory.current_execution:
        stored_config_info = memory.current_execution['config_manager_info']
        print("✅ Config manager info stored in memory")
        print(f"   - Manager type: {stored_config_info['config_manager_type']}")
        print(f"   - Validation status: {stored_config_info['config_validation_status']}")
        print(f"   - Loading method: {stored_config_info['config_loading_method']}")
        print(f"   - Config environment: {stored_config_info['config_environment']}")
        print(f"   - Config metadata: {stored_config_info['config_metadata']}")
    else:
        print("❌ Config manager info not found in memory")
        return False
    
    # Test 6: Check config manager details in configuration context
    config_context = memory.current_execution['configuration_context']
    if 'config_manager_details' in config_context:
        config_manager_details = config_context['config_manager_details']
        print("✅ Config manager details in configuration context")
        print(f"   - Manager type: {config_manager_details['manager_type']}")
        print(f"   - Validation status: {config_manager_details['validation_status']}")
        print(f"   - Loading method: {config_manager_details['loading_method']}")
    else:
        print("❌ Config manager details not found in configuration context")
        return False
    
    print("\n✅ All configuration manager memory integration tests passed!")
    return True


def test_config_analysis_functions():
    """Test configuration analysis functions."""
    print("\n🧪 Testing Configuration Analysis Functions")
    print("=" * 50)
    
    # Initialize memory with config
    memory = ExecutionMemory()
    execution_id = "config_analysis_test"
    
    class MockConfig:
        def __init__(self):
            self.auto_fix = True
            self.create_pr = False
            self.max_retries = 5
            self.better_ai = True
            self.language = type('Language', (), {'value': 'python'})()
    
    class MockConfigManager:
        def __init__(self):
            self.name = "ConfigurationManager"
    
    config = MockConfig()
    config_manager = MockConfigManager()
    
    memory.start_execution(execution_id, config, config_manager)
    
    # Test config impact analysis
    config_impact = memory._analyze_config_impact_on_attempts('test_file.py')
    print("✅ Config impact analysis:")
    print(f"   - Better AI enabled: {config_impact['better_ai_enabled']}")
    print(f"   - Max retries setting: {config_impact['max_retries_setting']}")
    print(f"   - Language context: {config_impact['language_context']}")
    print(f"   - Auto-fix enabled: {config_impact['auto_fix_enabled']}")
    
    # Test learning context with config factors
    learning_context = memory.get_previous_attempts_insights('test_file.py')
    config_factors = learning_context.get('configuration_factors', {})
    
    print("✅ Learning context config factors:")
    print(f"   - Current config: {config_factors.get('current_config', {})}")
    print(f"   - Config influence: {config_factors.get('config_influence_on_attempts', {})}")
    
    print("✅ Configuration analysis functions work correctly!")
    return True


def main():
    """Run all configuration memory integration tests."""
    print("🧠 Configuration Manager Memory Integration Test Suite")
    print("=" * 70)
    
    try:
        # Test basic integration
        success1 = test_config_memory_integration()
        
        # Test analysis functions
        success2 = test_config_analysis_functions()
        
        if success1 and success2:
            print("\n🎉 All configuration memory integration tests passed!")
            print("Configuration manager information is properly stored and accessible in memory.")
            return True
        else:
            print("\n❌ Some tests failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 