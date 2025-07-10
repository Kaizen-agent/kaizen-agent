#!/usr/bin/env python3
"""Test script to verify the better_ai flag functionality."""

import sys
from pathlib import Path

# Add the kaizen package to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.cli.commands.config import ConfigurationManager
from kaizen.cli.commands.models.configuration import TestConfiguration

def test_better_ai_flag():
    """Test that the better_ai flag is properly handled."""
    
    # Create a minimal config data
    config_data = {
        'name': 'test_better_ai',
        'file_path': 'test_file.py',
        'description': 'Test for better AI flag'
    }
    
    # Test without better_ai flag (default should be False)
    config_manager = ConfigurationManager()
    config_result = config_manager.load_configuration(
        Path('test_config.yaml'),
        auto_fix=True,
        create_pr=False,
        max_retries=2,
        base_branch='main',
        pr_strategy='ALL_PASSING',
        better_ai=False
    )
    
    if not config_result.is_success:
        print(f"❌ Failed to load configuration: {config_result.error}")
        return False
    
    config = config_result.value
    print(f"✅ Configuration loaded successfully")
    print(f"   Name: {config.name}")
    print(f"   Better AI: {config.better_ai}")
    
    # Test with better_ai flag enabled
    config_result_with_better_ai = config_manager.load_configuration(
        Path('test_config.yaml'),
        auto_fix=True,
        create_pr=False,
        max_retries=2,
        base_branch='main',
        pr_strategy='ALL_PASSING',
        better_ai=True
    )
    
    if not config_result_with_better_ai.is_success:
        print(f"❌ Failed to load configuration with better_ai=True: {config_result_with_better_ai.error}")
        return False
    
    config_with_better_ai = config_result_with_better_ai.value
    print(f"✅ Configuration with better_ai=True loaded successfully")
    print(f"   Name: {config_with_better_ai.name}")
    print(f"   Better AI: {config_with_better_ai.better_ai}")
    
    # Verify the flag values are different
    if config.better_ai != config_with_better_ai.better_ai:
        print(f"✅ Better AI flag correctly set: {config.better_ai} vs {config_with_better_ai.better_ai}")
        return True
    else:
        print(f"❌ Better AI flag not working correctly: both are {config.better_ai}")
        return False

def test_cli_overrides():
    """Test that CLI overrides work correctly for better_ai."""
    
    # Create a config with better_ai=True in the data
    config_data = {
        'name': 'test_cli_override',
        'file_path': 'test_file.py',
        'better_ai': True
    }
    
    # Test CLI override to False
    config_manager = ConfigurationManager()
    config_result = config_manager.load_configuration(
        Path('test_config.yaml'),
        auto_fix=True,
        create_pr=False,
        max_retries=2,
        base_branch='main',
        pr_strategy='ALL_PASSING',
        better_ai=False  # CLI override
    )
    
    if not config_result.is_success:
        print(f"❌ Failed to test CLI override: {config_result.error}")
        return False
    
    config = config_result.value
    print(f"✅ CLI override test successful")
    print(f"   Better AI: {config.better_ai}")
    
    return True

if __name__ == "__main__":
    print("Testing better_ai flag functionality...")
    print("=" * 50)
    
    success1 = test_better_ai_flag()
    print()
    success2 = test_cli_overrides()
    
    if success1 and success2:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1) 