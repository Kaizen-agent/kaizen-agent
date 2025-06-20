#!/usr/bin/env python3
"""Test script to verify environment variable loading works correctly."""

import os
import tempfile
from pathlib import Path

# Import the TestRunner to test environment variable loading
import sys
sys.path.insert(0, str(Path(__file__).parent / "kaizen"))

from kaizen.autofix.test.runner import TestRunner

def test_environment_variable_loading():
    """Test that environment variables are loaded correctly."""
    
    # Create a temporary directory with a .env file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a .env file with test variables
        env_file = temp_path / ".env"
        env_content = """
# Test environment variables
GOOGLE_API_KEY=test_google_api_key_123
OPENAI_API_KEY=test_openai_api_key_456
CUSTOM_VAR=test_custom_value
"""
        env_file.write_text(env_content)
        
        # Create a simple test config
        config = {
            'name': 'test',
            'file_path': 'test.py',
            'tests': []
        }
        
        # Test that the TestRunner loads environment variables
        with tempfile.TemporaryDirectory() as test_dir:
            test_path = Path(test_dir)
            
            # Create a pyproject.toml to make this the workspace root
            (test_path / "pyproject.toml").touch()
            
            # Copy the .env file to the test directory
            import shutil
            shutil.copy(env_file, test_path / ".env")
            
            # Change to the test directory and run the test
            original_cwd = os.getcwd()
            try:
                os.chdir(test_path)
                
                # Clear any existing environment variables
                if 'GOOGLE_API_KEY' in os.environ:
                    del os.environ['GOOGLE_API_KEY']
                if 'OPENAI_API_KEY' in os.environ:
                    del os.environ['OPENAI_API_KEY']
                if 'CUSTOM_VAR' in os.environ:
                    del os.environ['CUSTOM_VAR']
                
                # Verify they're cleared
                assert os.getenv('GOOGLE_API_KEY') is None
                assert os.getenv('OPENAI_API_KEY') is None
                assert os.getenv('CUSTOM_VAR') is None
                
                # Create TestRunner (this should load the .env file)
                runner = TestRunner(config)
                
                # Verify environment variables are loaded
                assert os.getenv('GOOGLE_API_KEY') == 'test_google_api_key_123'
                assert os.getenv('OPENAI_API_KEY') == 'test_openai_api_key_456'
                assert os.getenv('CUSTOM_VAR') == 'test_custom_value'
                
                print("✅ Environment variable loading test passed!")
                
            finally:
                os.chdir(original_cwd)

if __name__ == "__main__":
    print("Testing environment variable loading...")
    test_environment_variable_loading()
    print("\n🎉 Environment variable loading test completed!") 