"""Test the simple import resolver."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Use absolute imports for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kaizen.autofix.test.simple_import_resolver import SimpleImportResolver


class TestSimpleImportResolver(unittest.TestCase):
    """Test the simple import resolver functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.workspace_root = Path(__file__).parent.parent.parent
        self.resolver = SimpleImportResolver(self.workspace_root)
    
    def test_initialization(self):
        """Test that the resolver initializes correctly."""
        self.assertIsNotNone(self.resolver)
        self.assertEqual(self.resolver.workspace_root, self.workspace_root)
        self.assertIsInstance(self.resolver._processed_files, set)
        self.assertIsInstance(self.resolver._loaded_modules, dict)
    
    def test_extract_imports_from_ast(self):
        """Test import extraction from AST."""
        test_code = """
import os
from typing import List, Dict
from pathlib import Path as PathLib
"""
        
        import ast
        tree = ast.parse(test_code)
        imports = self.resolver._extract_imports_from_ast(tree)
        
        # Should extract all imports
        self.assertEqual(len(imports), 4)
        import_types = [imp['type'] for imp in imports]
        self.assertIn('import', import_types)
        self.assertIn('from', import_types)
        modules = [imp['module'] for imp in imports]
        self.assertIn('os', modules)
        self.assertIn('typing', modules)
        self.assertIn('pathlib', modules)
        names = [imp.get('name') for imp in imports if imp['type'] == 'from']
        self.assertIn('List', names)
        self.assertIn('Dict', names)
        self.assertIn('Path', names)
    
    def _parse_ast(self, code):
        """Helper method to parse AST."""
        import ast
        return ast.parse(code)
    
    def test_is_external_module(self):
        """Test external module detection."""
        self.assertTrue(self.resolver._is_external_module('os'))
        self.assertTrue(self.resolver._is_external_module('sys'))
        self.assertTrue(self.resolver._is_external_module('typing'))
        self.assertFalse(self.resolver._is_external_module('my_local_module'))
    
    def test_resolve_local_path(self):
        """Test local path resolution."""
        current_file = Path(__file__)
        
        # Test relative import
        relative_path = self.resolver._resolve_local_path('.utils', current_file)
        self.assertIsNone(relative_path)  # Should not find .utils in this context
        
        # Test external module
        external_path = self.resolver._resolve_local_path('os', current_file)
        self.assertIsNone(external_path)  # os is external
    
    def test_add_classes_from_module(self):
        """Test adding classes from module."""
        # Mock module with classes
        mock_module = MagicMock()
        mock_module.__dict__ = {
            'TestClass': type('TestClass', (), {}),
            'AnotherClass': type('AnotherClass', (), {}),
            '_private_class': type('_PrivateClass', (), {}),
            'function': lambda: None
        }
        
        namespace = {}
        self.resolver._add_classes_from_module(mock_module, 'test_module', namespace)
        
        # Should add public classes
        self.assertIn('TestClass', namespace)
        self.assertIn('AnotherClass', namespace)
        self.assertNotIn('_private_class', namespace)
        self.assertNotIn('function', namespace)
    
    def test_process_file_and_dependencies(self):
        """Test processing file and dependencies."""
        # Create a temporary test file
        test_file = Path(__file__).parent / "temp_test_file.py"
        test_content = """
import os
from typing import List

class TestClass:
    def __init__(self):
        self.data = []
"""
        
        try:
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            namespace = {}
            self.resolver._process_file_and_dependencies(test_file, namespace)
            
            # Should have processed the file
            self.assertIn(test_file, self.resolver._processed_files)
            
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()
    
    def test_resolve_imports_for_file(self):
        """Test resolving imports for a file."""
        # Create a temporary test file
        test_file = Path(__file__).parent / "temp_test_file.py"
        test_content = """
import os
from typing import List

class TestClass:
    def __init__(self):
        self.data = []
"""
        
        try:
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            namespace = self.resolver.resolve_imports_for_file(test_file)
            
            # Should have resolved some imports
            self.assertIsInstance(namespace, dict)
            
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()


if __name__ == '__main__':
    unittest.main() 