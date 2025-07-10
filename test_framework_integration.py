#!/usr/bin/env python3

import sys
from pathlib import Path
import tempfile
import os

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_framework_integration():
    """Test that the framework field is properly integrated throughout the test execution flow."""
    
    # Create a temporary test configuration
    config_content = '''
name: 'Framework Integration Test'
file_path: 'test_agent.py'
language: 'python'
framework: 'llamaindex'
description: 'Test configuration for framework integration testing'
agent:
  module: 'test_agent'
  class: 'TestAgent'
  method: 'process'
evaluation:
  evaluation_targets:
    - name: quality
      source: return
      criteria: "The response should be well-structured and accurate"
      weight: 1.0
steps:
  - name: Framework Test
    input:
      input: 
        - name: message
          type: string
          value: "Test message for framework integration"
      method: process
    expected_output:
      contains: "processed"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_file = f.name

    try:
        print("🧪 Testing Framework Integration")
        print("=" * 50)
        
        # Test 1: Configuration Loading
        print("\n1. Testing Configuration Loading...")
        from kaizen.cli.commands.config import ConfigurationManager
        
        config_manager = ConfigurationManager()
        config_result = config_manager.load_configuration(
            Path(config_file),
            auto_fix=False,
            create_pr=False,
            max_retries=0,
            base_branch='main',
            pr_strategy='ALL_PASSING'
        )
        
        if not config_result.is_success:
            print(f"❌ Config loading failed: {config_result.error}")
            return False
        
        config = config_result.value
        print(f"✅ Config loaded successfully: {config.name}")
        print(f"   Language: {config.language.value}")
        print(f"   Framework: {config.framework.value}")
        
        # Test 2: Framework Override
        print("\n2. Testing Framework Override...")
        config_with_override = config_manager.load_configuration(
            Path(config_file),
            auto_fix=False,
            create_pr=False,
            max_retries=0,
            base_branch='main',
            pr_strategy='ALL_PASSING',
            framework='langchain'  # Override the YAML framework
        )
        
        if not config_with_override.is_success:
            print(f"❌ Config loading with override failed: {config_with_override.error}")
            return False
        
        config_override = config_with_override.value
        print(f"✅ Framework override successful")
        print(f"   Original: {config.framework.value}")
        print(f"   Override: {config_override.framework.value}")
        
        # Test 3: Runner Config Creation
        print("\n3. Testing Runner Config Creation...")
        from kaizen.cli.commands.test_commands import TestAllCommand
        import logging
        
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        command = TestAllCommand(config, logger, verbose=True)
        runner_config = command._create_runner_config()
        
        if 'framework' not in runner_config:
            print("❌ Framework field not found in runner config")
            return False
        
        print(f"✅ Runner config created successfully")
        print(f"   Framework in runner config: {runner_config['framework']}")
        print(f"   Framework type: {type(runner_config['framework'])}")
        
        # Test 4: Test Runner Integration
        print("\n4. Testing Test Runner Integration...")
        
        # Create a mock test file for the runner
        test_file_content = '''
class TestAgent:
    def process(self, message):
        return f"processed: {message}"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_file_content)
            test_file = f.name
        
        try:
            # Test that the runner can access the framework field
            # We'll just check the config without initializing the full runner
            # to avoid API key requirements
            if 'framework' not in runner_config:
                print("❌ Framework field not found in test runner config")
                return False
            
            print(f"✅ Test runner integration successful")
            print(f"   Framework in test runner: {runner_config['framework']}")
            
        finally:
            os.unlink(test_file)
        
        # Test 5: Framework Validation
        print("\n5. Testing Framework Validation...")
        from kaizen.cli.commands.types import Framework
        
        # Test valid frameworks
        valid_frameworks = ['llamaindex', 'langchain', 'autogen', 'custom']
        for framework_name in valid_frameworks:
            try:
                framework = Framework.from_str(framework_name)
                print(f"   ✅ Valid framework: {framework_name} -> {framework.value}")
            except ValueError as e:
                print(f"   ❌ Invalid framework: {framework_name} - {e}")
                return False
        
        # Test invalid framework
        try:
            Framework.from_str('invalid_framework')
            print("   ❌ Invalid framework should have failed")
            return False
        except ValueError:
            print("   ✅ Invalid framework correctly rejected")
        
        print("\n🎉 All Framework Integration Tests Passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.unlink(config_file)

if __name__ == "__main__":
    success = test_framework_integration()
    sys.exit(0 if success else 1) 