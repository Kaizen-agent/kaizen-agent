"""Test to demonstrate and fix class loading issues."""

import unittest
from pathlib import Path
import tempfile
import os

# Use absolute imports for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kaizen.autofix.test.simple_import_resolver import SimpleImportResolver


class TestClassLoading(unittest.TestCase):
    """Test that classes from other files are properly loaded into namespace."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.workspace_root = Path(__file__).parent.parent.parent
        self.resolver = SimpleImportResolver(self.workspace_root)
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_workspace = Path(self.temp_dir)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_class_loading_from_local_file(self):
        """Test that classes from local files are properly loaded."""
        # Create a test file with a class
        models_file = self.temp_workspace / "models.py"
        models_content = """
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class User:
    name: str
    email: str
    age: int

class Product:
    def __init__(self, name: str, price: float):
        self.name = name
        self.price = price
    
    def get_price(self) -> float:
        return self.price

class Status:
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        
        with open(models_file, 'w') as f:
            f.write(models_content)
        
        # Create main file that imports from models
        main_file = self.temp_workspace / "main.py"
        main_content = """
from models import User, Product, Status

class MainClass:
    def __init__(self):
        self.user = User("John", "john@example.com", 30)
        self.product = Product("Book", 29.99)
        self.status = Status.ACTIVE
"""
        
        with open(main_file, 'w') as f:
            f.write(main_content)
        
        # Test the resolver
        temp_resolver = SimpleImportResolver(self.temp_workspace)
        namespace = temp_resolver.resolve_imports_for_file(main_file)
        
        # Check that classes are loaded
        self.assertIn('User', namespace)
        self.assertIn('Product', namespace)
        self.assertIn('Status', namespace)
        self.assertIn('MainClass', namespace)
        
        # Check that classes are actually callable
        user = namespace['User']("Test", "test@example.com", 25)
        self.assertEqual(user.name, "Test")
        
        product = namespace['Product']("Test Product", 10.0)
        self.assertEqual(product.get_price(), 10.0)
        
        self.assertEqual(namespace['Status'].ACTIVE, "active")
    
    def test_relative_import_class_loading(self):
        """Test that classes from relative imports are properly loaded."""
        # Create a package structure
        package_dir = self.temp_workspace / "my_package"
        package_dir.mkdir()
        
        # Create __init__.py
        init_file = package_dir / "__init__.py"
        init_file.write_text("")
        
        # Create models.py in package
        models_file = package_dir / "models.py"
        models_content = """
from dataclasses import dataclass

@dataclass
class Config:
    api_key: str
    base_url: str
"""
        
        with open(models_file, 'w') as f:
            f.write(models_content)
        
        # Create main.py with relative import
        main_file = package_dir / "main.py"
        main_content = """
from .models import Config

class App:
    def __init__(self, config: Config):
        self.config = config
"""
        
        with open(main_file, 'w') as f:
            f.write(main_content)
        
        # Test the resolver
        temp_resolver = SimpleImportResolver(self.temp_workspace)
        namespace = temp_resolver.resolve_imports_for_file(main_file)
        
        # Check that classes are loaded
        self.assertIn('Config', namespace)
        self.assertIn('App', namespace)
        
        # Check that classes are callable
        config = namespace['Config']("test-key", "https://api.example.com")
        self.assertEqual(config.api_key, "test-key")
    
    def test_dataclass_loading(self):
        """Test that dataclasses are properly loaded."""
        # Create a file with dataclasses
        data_file = self.temp_workspace / "data.py"
        data_content = """
from dataclasses import dataclass, field
from typing import List

@dataclass
class Person:
    name: str
    age: int
    hobbies: List[str] = field(default_factory=list)

@dataclass
class Company:
    name: str
    employees: List[Person] = field(default_factory=list)
"""
        
        with open(data_file, 'w') as f:
            f.write(data_content)
        
        # Create main file
        main_file = self.temp_workspace / "main.py"
        main_content = """
from data import Person, Company

def create_sample_data():
    person = Person("Alice", 30, ["reading", "swimming"])
    company = Company("Tech Corp", [person])
    return company
"""
        
        with open(main_file, 'w') as f:
            f.write(main_content)
        
        # Test the resolver
        temp_resolver = SimpleImportResolver(self.temp_workspace)
        namespace = temp_resolver.resolve_imports_for_file(main_file)
        
        # Check that dataclasses are loaded
        self.assertIn('Person', namespace)
        self.assertIn('Company', namespace)
        
        # Check that dataclasses work
        person = namespace['Person']("Bob", 25, ["coding"])
        self.assertEqual(person.name, "Bob")
        self.assertEqual(person.hobbies, ["coding"])
        
        company = namespace['Company']("Startup", [person])
        self.assertEqual(company.name, "Startup")
        self.assertEqual(len(company.employees), 1)


if __name__ == '__main__':
    unittest.main() 