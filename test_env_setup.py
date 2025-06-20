#!/usr/bin/env python3
"""Test script to verify environment setup functionality."""

import os
import tempfile
from pathlib import Path

# Import the environment setup utilities
import sys
sys.path.insert(0, str(Path(__file__).parent / "kaizen"))

from kaizen.cli.utils.env_setup import (
    load_environment_variables,
    validate_environment_variables,
    check_environment_setup,
    create_env_example_file,
    get_missing_variables
)

def test_environment_setup():
    """Test the environment setup functionality."""
    
    print("🧪 Testing environment setup functionality...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test 1: Load environment variables
        print("\n1. Testing environment variable loading...")
        
        # Create a .env file with test variables
        env_file = temp_path / ".env"
        env_content = """
# Test environment variables
GOOGLE_API_KEY=test_google_api_key_123
GITHUB_TOKEN=test_github_token_456
OPENAI_API_KEY=test_openai_api_key_789
CUSTOM_VAR=test_custom_value
"""
        env_file.write_text(env_content)
        
        # Test loading
        loaded_files = load_environment_variables(temp_path)
        assert str(env_file) in loaded_files
        assert loaded_files[str(env_file)] == "loaded"
        print("✅ Environment variable loading test passed")
        
        # Test 2: Validate environment variables
        print("\n2. Testing environment variable validation...")
        
        validation_results = validate_environment_variables(['core', 'github'])
        
        # Check core variables
        assert 'core' in validation_results
        assert validation_results['core']['GOOGLE_API_KEY'] == "set"
        
        # Check GitHub variables
        assert 'github' in validation_results
        assert validation_results['github']['GITHUB_TOKEN'] == "set"
        
        print("✅ Environment variable validation test passed")
        
        # Test 3: Check environment setup
        print("\n3. Testing environment setup check...")
        
        is_setup = check_environment_setup(temp_path, ['core', 'github'])
        assert is_setup == True
        print("✅ Environment setup check test passed")
        
        # Test 4: Get missing variables
        print("\n4. Testing missing variables detection...")
        
        # Clear some variables to test missing detection
        if 'GITHUB_TOKEN' in os.environ:
            del os.environ['GITHUB_TOKEN']
        
        missing_vars = get_missing_variables(['github'])
        assert 'GITHUB_TOKEN' in missing_vars
        print("✅ Missing variables detection test passed")
        
        # Test 5: Create .env.example file
        print("\n5. Testing .env.example file creation...")
        
        create_env_example_file(temp_path)
        example_file = temp_path / ".env.example"
        assert example_file.exists()
        
        content = example_file.read_text()
        assert "GOOGLE_API_KEY" in content
        assert "GITHUB_TOKEN" in content
        print("✅ .env.example file creation test passed")
    
    print("\n🎉 All environment setup tests passed!")

def test_environment_setup_without_dotenv():
    """Test environment setup when no .env file exists."""
    
    print("\n🧪 Testing environment setup without .env file...")
    
    # Clear all test environment variables for this test
    test_vars = ['GOOGLE_API_KEY', 'GITHUB_TOKEN', 'OPENAI_API_KEY', 'CUSTOM_VAR']
    original_values = {}
    
    for var in test_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    try:
        # Create a temporary directory without .env file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test loading (should not fail)
            loaded_files = load_environment_variables(temp_path)
            assert len(loaded_files) == 0
            print("✅ Environment loading without .env file test passed")
            
            # Test validation (should show missing variables)
            validation_results = validate_environment_variables(['core'])
            assert 'core' in validation_results
            assert validation_results['core']['GOOGLE_API_KEY'] == "missing"
            print("✅ Environment validation without .env file test passed")
            
            # Test setup check (should return False)
            is_setup = check_environment_setup(temp_path, ['core'])
            assert is_setup == False
            print("✅ Environment setup check without .env file test passed")
        
        print("🎉 Environment setup without .env file tests passed!")
    finally:
        # Restore original environment variables
        for var, value in original_values.items():
            os.environ[var] = value

if __name__ == "__main__":
    print("Testing environment setup functionality...")
    
    # Clear any existing environment variables for testing
    test_vars = ['GOOGLE_API_KEY', 'GITHUB_TOKEN', 'OPENAI_API_KEY', 'CUSTOM_VAR']
    original_values = {}
    
    for var in test_vars:
        if var in os.environ:
            original_values[var] = os.environ[var]
            del os.environ[var]
    
    try:
        test_environment_setup()
        test_environment_setup_without_dotenv()
        print("\n🎉 All tests completed successfully!")
    finally:
        # Restore original environment variables
        for var, value in original_values.items():
            os.environ[var] = value 