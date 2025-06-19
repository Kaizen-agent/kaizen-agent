"""Test file for dependency manager functionality."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dependency_manager import DependencyManager, DependencyInfo, ImportResult
from errors import DependencyError
from result import Result

def test_dependency_manager_initialization():
    """Test that DependencyManager initializes correctly."""
    manager = DependencyManager()
    assert manager.workspace_root == Path.cwd()
    assert len(manager._original_sys_path) > 0
    assert manager._imported_modules == {}
    assert manager._processed_files == set()

def test_import_package_dependency_success():
    """Test successful package import."""
    manager = DependencyManager()
    
    # Test importing a standard library module
    dep_info = manager._import_package_dependency("os")
    
    assert dep_info.name == "os"
    assert dep_info.type == "package"
    assert dep_info.imported == True
    assert dep_info.error is None
    assert "os" in manager._imported_modules

def test_import_package_dependency_with_version():
    """Test package import with version specifier."""
    manager = DependencyManager()
    
    # Test with version specifier
    dep_info = manager._import_package_dependency("sys==3.8.0")
    
    assert dep_info.name == "sys"
    assert dep_info.version == "3.8.0"
    assert dep_info.imported == True
    assert dep_info.error is None

def test_import_package_dependency_failure():
    """Test package import failure."""
    manager = DependencyManager()
    
    # Test with non-existent package
    dep_info = manager._import_package_dependency("non_existent_package")
    
    assert dep_info.name == "non_existent_package"
    assert dep_info.imported == False
    assert dep_info.error is not None
    assert "Package not found" in dep_info.error

def test_generate_module_name():
    """Test module name generation."""
    manager = DependencyManager()
    
    # Test basic file name
    name = manager._generate_module_name(Path("test_file.py"))
    assert name == "test_file"
    
    # Test file with hyphens
    name = manager._generate_module_name(Path("test-file.py"))
    assert name == "test_file"
    
    # Test file with spaces
    name = manager._generate_module_name(Path("test file.py"))
    assert name == "test_file"
    
    # Test file with invalid characters
    name = manager._generate_module_name(Path("123test.py"))
    assert name == "module_123test"

def test_build_namespace():
    """Test namespace building."""
    manager = DependencyManager()
    
    # Add some test modules
    manager._imported_modules["test_module"] = MagicMock()
    manager._imported_modules["another_module"] = MagicMock()
    
    namespace = manager._build_namespace()
    
    # Check that standard modules are included
    assert "os" in namespace
    assert "sys" in namespace
    
    # Check that imported modules are included
    assert "test_module" in namespace
    assert "another_module" in namespace

def test_cleanup():
    """Test cleanup functionality."""
    manager = DependencyManager()
    original_sys_path = manager._original_sys_path.copy()
    
    # Add some test data
    manager._imported_modules["test"] = MagicMock()
    manager._processed_files.add(Path("test.py"))
    
    # Modify sys.path
    sys.path.append("/test/path")
    
    # Cleanup
    manager.cleanup()
    
    # Check that everything is cleaned up
    assert manager._imported_modules == {}
    assert manager._processed_files == set()
    assert sys.path == original_sys_path

def test_get_import_status():
    """Test import status retrieval."""
    manager = DependencyManager()
    
    # Add some test modules
    manager._imported_modules["test_module"] = MagicMock()
    
    status = manager.get_import_status()
    
    assert "imported_modules" in status
    assert "sys_path" in status
    assert "workspace_root" in status
    assert "test_module" in status["imported_modules"]

if __name__ == "__main__":
    # Run tests
    print("Running dependency manager tests...")
    
    test_dependency_manager_initialization()
    print("✅ Dependency manager initialization test passed")
    
    test_import_package_dependency_success()
    print("✅ Package import success test passed")
    
    test_import_package_dependency_with_version()
    print("✅ Package import with version test passed")
    
    test_import_package_dependency_failure()
    print("✅ Package import failure test passed")
    
    test_generate_module_name()
    print("✅ Module name generation test passed")
    
    test_build_namespace()
    print("✅ Namespace building test passed")
    
    test_cleanup()
    print("✅ Cleanup test passed")
    
    test_get_import_status()
    print("✅ Import status test passed")
    
    print("\n🎉 All tests passed!") 