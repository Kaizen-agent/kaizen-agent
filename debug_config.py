#!/usr/bin/env python3

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.cli.commands.config import ConfigurationManager
import tempfile
import os

def test_config_loading():
    """Test the config loading and language detection."""
    
    # Create a temporary YAML config file
    config_content = '''
name: 'Email Improvement Agent Test (TypeScript)'
file_path: 'debug_language.py'
language: 'typescript'
description: 'This agent improves email drafts by making them more professional, clear, and well-structured.'
agent:
  module: 'email-agent'
evaluation:
  evaluation_targets:
    - name: quality
      source: return
      criteria: "The email should be professional, polite, and well-structured with proper salutations and closings"
      weight: 0.5
    - name: format
      source: return
      criteria: "The response should contain only the improved email content without any explanatory text, markdown formatting, or additional commentary."
      weight: 0.5
files_to_fix:
  - 'debug_language.py'
steps:
  - name: Professional Email Improvement
    input:
      input: 
        - name: messages
          type: array
          value:
            - role: "user"
              content: "hey boss, i need time off next week. thanks"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_file = f.name

    try:
        print(f"Testing with config file: {config_file}")
        
        # Load configuration
        config_manager = ConfigurationManager()
        config_result = config_manager.load_configuration(
            Path(config_file),
            auto_fix=False,
            create_pr=False,
            max_retries=0,
            base_branch='main',
            pr_strategy='ALL_PASSING',
            language='typescript'  # This should override the YAML
        )
        
        if not config_result.is_success:
            print(f"❌ Config loading failed: {config_result.error}")
            return
        
        config = config_result.value
        print(f"✅ Config loaded successfully: {config.name}")
        print(f"   Language: {config.language.value}")
        print(f"   Language type: {type(config.language.value)}")
        
        # Test runner config creation
        from kaizen.cli.commands.test_commands import TestAllCommand
        import logging
        
        # Create a logger for the command
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        
        # Create a mock command instance
        command = TestAllCommand(config, logger, verbose=True)
        
        # Create runner config
        runner_config = command._create_runner_config()
        
        print(f"\nRunner config language: {runner_config.get('language')}")
        print(f"Runner config language type: {type(runner_config.get('language'))}")
        
        # Test the language comparison
        language = runner_config.get('language')
        print(f"\nLanguage comparison test:")
        print(f"   language == 'typescript': {language == 'typescript'}")
        print(f"   language == 'python': {language == 'python'}")
        print(f"   repr(language): {repr(language)}")
        
    finally:
        os.unlink(config_file)

if __name__ == "__main__":
    test_config_loading() 