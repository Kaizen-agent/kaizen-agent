"""Dependency management for test execution.

This module provides functionality for managing dependencies and referenced files
specified in test configurations. It handles importing Python packages, local modules,
and ensuring all required dependencies are available before test execution.
"""

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field

from .errors import DependencyError, ConfigurationError
from .result import Result

logger = logging.getLogger(__name__)

@dataclass
class DependencyInfo:
    """Information about a dependency.
    
    Attributes:
        name: Name of the dependency
        type: Type of dependency (package, local_file, module)
        path: Path to the dependency (for local files)
        version: Version requirement (for packages)
        imported: Whether the dependency was successfully imported
        error: Error message if import failed
    """
    name: str
    type: str  # 'package', 'local_file', 'module'
    path: Optional[Path] = None
    version: Optional[str] = None
    imported: bool = False
    error: Optional[str] = None

@dataclass
class ImportResult:
    """Result of dependency import operation.
    
    Attributes:
        success: Whether all dependencies were imported successfully
        dependencies: List of dependency information
        namespace: Dictionary containing imported modules
        errors: List of import errors
    """
    success: bool
    dependencies: List[DependencyInfo] = field(default_factory=list)
    namespace: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

class DependencyManager:
    """Manages dependencies and imports for test execution.
    
    This class handles importing Python packages, local modules, and referenced files
    specified in test configurations. It ensures all dependencies are available
    before test execution begins.
    """
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the dependency manager.
        
        Args:
            workspace_root: Root directory of the workspace (for resolving relative paths)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self._original_sys_path = sys.path.copy()
        self._imported_modules: Dict[str, Any] = {}
        self._processed_files: Set[Path] = set()
    
    def import_dependencies(
        self, 
        dependencies: List[str], 
        referenced_files: List[str],
        config_path: Path
    ) -> Result[ImportResult]:
        """Import all dependencies and referenced files.
        
        Args:
            dependencies: List of package dependencies to import
            referenced_files: List of local files to import
            config_path: Path to the configuration file (for resolving relative paths)
            
        Returns:
            Result containing import result or error
        """
        try:
            logger.info(f"Importing {len(dependencies)} dependencies and {len(referenced_files)} referenced files")
            
            result = ImportResult(success=True)
            
            # Import package dependencies
            for dep in dependencies:
                dep_info = self._import_package_dependency(dep)
                result.dependencies.append(dep_info)
                if not dep_info.imported:
                    result.success = False
                    result.errors.append(f"Failed to import package {dep}: {dep_info.error}")
            
            # Import referenced files
            for file_path in referenced_files:
                dep_info = self._import_referenced_file(file_path, config_path)
                result.dependencies.append(dep_info)
                if not dep_info.imported:
                    result.success = False
                    result.errors.append(f"Failed to import file {file_path}: {dep_info.error}")
            
            # Build namespace from imported modules
            result.namespace = self._build_namespace()
            
            if result.success:
                logger.info("All dependencies imported successfully")
            else:
                logger.warning(f"Some dependencies failed to import: {result.errors}")
            
            return Result.success(result)
            
        except Exception as e:
            logger.error(f"Error importing dependencies: {str(e)}")
            return Result.failure(DependencyError(f"Failed to import dependencies: {str(e)}"))
    
    def _import_package_dependency(self, dependency: str) -> DependencyInfo:
        """Import a package dependency.
        
        Args:
            dependency: Package name (may include version specifier)
            
        Returns:
            DependencyInfo with import result
        """
        # Parse package name and version
        if '==' in dependency:
            name, version = dependency.split('==', 1)
        elif '>=' in dependency:
            name, version = dependency.split('>=', 1)
        elif '<=' in dependency:
            name, version = dependency.split('<=', 1)
        elif '>' in dependency:
            name, version = dependency.split('>', 1)
        elif '<' in dependency:
            name, version = dependency.split('<', 1)
        else:
            name, version = dependency, None
        
        name = name.strip()
        version = version.strip() if version else None
        
        try:
            # Try to import the package
            module = importlib.import_module(name)
            self._imported_modules[name] = module
            
            logger.info(f"Successfully imported package: {name}")
            return DependencyInfo(
                name=name,
                type='package',
                version=version,
                imported=True
            )
            
        except ImportError as e:
            error_msg = f"Package not found: {name}"
            logger.warning(f"{error_msg}: {str(e)}")
            return DependencyInfo(
                name=name,
                type='package',
                version=version,
                imported=False,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Error importing package {name}: {str(e)}"
            logger.error(error_msg)
            return DependencyInfo(
                name=name,
                type='package',
                version=version,
                imported=False,
                error=error_msg
            )
    
    def _import_referenced_file(self, file_path: str, config_path: Path) -> DependencyInfo:
        """Import a referenced file.
        
        Args:
            file_path: Path to the file to import
            config_path: Path to the configuration file (for resolving relative paths)
            
        Returns:
            DependencyInfo with import result
        """
        try:
            # Resolve file path relative to config file
            if Path(file_path).is_absolute():
                resolved_path = Path(file_path)
            else:
                resolved_path = config_path.parent / file_path
            
            resolved_path = resolved_path.resolve()
            
            if not resolved_path.exists():
                error_msg = f"File not found: {resolved_path}"
                logger.warning(error_msg)
                return DependencyInfo(
                    name=file_path,
                    type='local_file',
                    path=resolved_path,
                    imported=False,
                    error=error_msg
                )
            
            if not resolved_path.is_file():
                error_msg = f"Path is not a file: {resolved_path}"
                logger.warning(error_msg)
                return DependencyInfo(
                    name=file_path,
                    type='local_file',
                    path=resolved_path,
                    imported=False,
                    error=error_msg
                )
            
            # Generate module name from file path
            module_name = self._generate_module_name(resolved_path)
            
            # Add file's directory to Python path if not already there
            file_dir = resolved_path.parent
            if str(file_dir) not in sys.path:
                sys.path.insert(0, str(file_dir))
            
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, resolved_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._imported_modules[module_name] = module
                
                # Also add the module with the original file path as key for easier access
                # This helps when the code tries to import using the original path
                try:
                    path_key = str(resolved_path.relative_to(self.workspace_root)).replace('/', '.').replace('.py', '')
                except ValueError as e:
                    # File is not in the workspace root - this can happen when users specify
                    # files from different workspaces or use absolute paths incorrectly
                    logger.warning(f"File {resolved_path} is not in the workspace root {self.workspace_root}. "
                                  f"This may indicate a configuration issue. Error: {str(e)}")
                    
                    # Try to handle this gracefully by using the file name as the path key
                    path_key = resolved_path.stem
                    logger.info(f"Using file name '{path_key}' as path key for {resolved_path}")
                
                if path_key not in self._imported_modules:
                    self._imported_modules[path_key] = module
                
                logger.info(f"Successfully imported file: {resolved_path} as {module_name}")
                return DependencyInfo(
                    name=file_path,
                    type='local_file',
                    path=resolved_path,
                    imported=True
                )
            else:
                error_msg = f"Could not create module spec for: {resolved_path}"
                logger.error(error_msg)
                return DependencyInfo(
                    name=file_path,
                    type='local_file',
                    path=resolved_path,
                    imported=False,
                    error=error_msg
                )
                
        except Exception as e:
            error_msg = f"Error importing file {file_path}: {str(e)}"
            logger.error(error_msg)
            return DependencyInfo(
                name=file_path,
                type='local_file',
                path=resolved_path if 'resolved_path' in locals() else None,
                imported=False,
                error=error_msg
            )
    
    def _generate_module_name(self, file_path: Path) -> str:
        """Generate a module name from a file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Generated module name
        """
        # Remove .py extension
        name = file_path.stem
        
        # Replace invalid characters
        name = name.replace('-', '_').replace(' ', '_')
        
        # Ensure it's a valid Python identifier
        if not name.isidentifier():
            name = f"module_{name}"
        
        return name
    
    def _build_namespace(self) -> Dict[str, Any]:
        """Build a namespace dictionary from imported modules.
        
        Returns:
            Dictionary containing imported modules and their functions
        """
        namespace = {}
        
        # Add standard library modules
        standard_modules = [
            'os', 'sys', 'pathlib', 'typing', 'logging', 'json', 
            'datetime', 'time', 're', 'math', 'random', 'itertools',
            'collections', 'dataclasses', 'enum', 'importlib', 'ast',
            'contextlib', 'functools'
        ]
        
        for module_name in standard_modules:
            try:
                module = importlib.import_module(module_name)
                namespace[module_name] = module
            except ImportError:
                pass  # Skip if module not available
        
        # Add imported modules and extract their functions
        for module_name, module in self._imported_modules.items():
            namespace[module_name] = module
            
            # Extract functions from local modules (not standard library or third-party)
            if hasattr(module, '__file__') and module.__file__:
                module_path = Path(module.__file__)
                # Check if this is a local module (not in site-packages or similar)
                if not any(part in str(module_path) for part in ['site-packages', 'dist-packages', 'lib/python']):
                    # Extract all attributes from the module (not just callable functions)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # Add all attributes that don't start with underscore (including constants)
                        if not attr_name.startswith('_'):
                            namespace[attr_name] = attr
                            if callable(attr):
                                logger.debug(f"Added function {attr_name} from module {module_name}")
                            else:
                                logger.debug(f"Added constant/variable {attr_name} from module {module_name}")
        
        # Add common aliases for better compatibility
        if 'pathlib' in namespace:
            namespace['Path'] = namespace['pathlib'].Path
        
        if 'typing' in namespace:
            # Add common typing imports
            typing_module = namespace['typing']
            for attr in ['List', 'Dict', 'Tuple', 'Set', 'Optional', 'Any', 'Union']:
                if hasattr(typing_module, attr):
                    namespace[attr] = getattr(typing_module, attr)
        
        return namespace
    
    def cleanup(self) -> None:
        """Clean up any modifications made to the Python environment."""
        # Restore original sys.path
        sys.path.clear()
        sys.path.extend(self._original_sys_path)
        
        # Clear imported modules
        self._imported_modules.clear()
        self._processed_files.clear()
        
        logger.debug("Dependency manager cleanup completed")
    
    def get_import_status(self) -> Dict[str, Any]:
        """Get the current import status.
        
        Returns:
            Dictionary containing import status information
        """
        return {
            'imported_modules': list(self._imported_modules.keys()),
            'sys_path': sys.path.copy(),
            'workspace_root': str(self.workspace_root)
        } 