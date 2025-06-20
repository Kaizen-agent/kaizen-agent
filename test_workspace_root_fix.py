#!/usr/bin/env python3
"""Test script to verify workspace root detection works in different scenarios."""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Import the TestRunner to test the workspace root detection
import sys
sys.path.insert(0, str(Path(__file__).parent / "kaizen"))

from kaizen.autofix.test.runner import TestRunner

def test_workspace_root_detection():
    """Test that workspace root detection works in different scenarios."""
    
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test 1: Project with pyproject.toml
        project_dir = temp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").touch()
        
        with patch('pathlib.Path.cwd', return_value=project_dir):
            config = {
                'name': 'test',
                'file_path': 'test.py',
                'tests': []
            }
            runner = TestRunner(config)
            assert runner.workspace_root == project_dir
            print("✅ Test 1 passed: Found workspace root with pyproject.toml")
        
        # Test 2: Project with requirements.txt
        req_project = temp_path / "req_project"
        req_project.mkdir()
        (req_project / "requirements.txt").touch()
        
        with patch('pathlib.Path.cwd', return_value=req_project):
            config = {
                'name': 'test',
                'file_path': 'test.py',
                'tests': []
            }
            runner = TestRunner(config)
            assert runner.workspace_root == req_project
            print("✅ Test 2 passed: Found workspace root with requirements.txt")
        
        # Test 3: Project with src directory
        src_project = temp_path / "src_project"
        src_project.mkdir()
        (src_project / "src").mkdir()
        
        with patch('pathlib.Path.cwd', return_value=src_project):
            config = {
                'name': 'test',
                'file_path': 'test.py',
                'tests': []
            }
            runner = TestRunner(config)
            assert runner.workspace_root == src_project
            print("✅ Test 3 passed: Found workspace root with src directory")
        
        # Test 4: kaizen-agent project (development scenario) - no project indicators
        kaizen_project = temp_path / "kaizen-agent"
        kaizen_project.mkdir()
        subdir = kaizen_project / "subdir"
        subdir.mkdir()
        
        with patch('pathlib.Path.cwd', return_value=subdir):
            config = {
                'name': 'test',
                'file_path': 'test.py',
                'tests': []
            }
            print(f"Debug: subdir={subdir}")
            print(f"Debug: subdir.parents={list(subdir.parents)}")
            runner = TestRunner(config)
            print(f"Debug: Expected {kaizen_project}, got {runner.workspace_root}")
            # In this case, it should find the kaizen-agent directory
            assert runner.workspace_root == kaizen_project
            print("✅ Test 4 passed: Found workspace root in kaizen-agent project")
        
        # Test 5: Fallback to current directory (no indicators)
        empty_dir = temp_path / "empty_dir"
        empty_dir.mkdir()
        
        with patch('pathlib.Path.cwd', return_value=empty_dir):
            config = {
                'name': 'test',
                'file_path': 'test.py',
                'tests': []
            }
            runner = TestRunner(config)
            assert runner.workspace_root == empty_dir
            print("✅ Test 5 passed: Fallback to current directory")

def test_real_world_scenarios():
    """Test real-world scenarios where the SDK might be used."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Scenario 1: User's project with pyproject.toml
        user_project = temp_path / "my_app"
        user_project.mkdir()
        (user_project / "pyproject.toml").touch()
        (user_project / "src").mkdir()
        (user_project / "src" / "main.py").touch()
        
        # Test from src directory
        with patch('pathlib.Path.cwd', return_value=user_project / "src"):
            config = {
                'name': 'test',
                'file_path': 'main.py',
                'tests': []
            }
            runner = TestRunner(config)
            assert runner.workspace_root == user_project
            print("✅ Real-world test 1 passed: Found project root from src subdirectory")
        
        # Scenario 2: User's project with requirements.txt
        flask_app = temp_path / "flask_app"
        flask_app.mkdir()
        (flask_app / "requirements.txt").touch()
        (flask_app / "app.py").touch()
        
        with patch('pathlib.Path.cwd', return_value=flask_app):
            config = {
                'name': 'test',
                'file_path': 'app.py',
                'tests': []
            }
            runner = TestRunner(config)
            assert runner.workspace_root == flask_app
            print("✅ Real-world test 2 passed: Found project root with requirements.txt")
        
        # Scenario 3: Simple script directory (fallback)
        script_dir = temp_path / "scripts"
        script_dir.mkdir()
        (script_dir / "script.py").touch()
        
        with patch('pathlib.Path.cwd', return_value=script_dir):
            config = {
                'name': 'test',
                'file_path': 'script.py',
                'tests': []
            }
            runner = TestRunner(config)
            assert runner.workspace_root == script_dir
            print("✅ Real-world test 3 passed: Fallback to script directory")

if __name__ == "__main__":
    print("Testing workspace root detection...")
    test_workspace_root_detection()
    print("\nTesting real-world scenarios...")
    test_real_world_scenarios()
    print("\n🎉 All workspace root detection tests passed!") 