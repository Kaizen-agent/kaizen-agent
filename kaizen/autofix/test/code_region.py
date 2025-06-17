"""Code region extraction and execution."""

# Standard library imports
import ast
import logging
import os
import sys
import importlib
import importlib.util
import importlib.machinery
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Set, FrozenSet, Union
from collections import defaultdict

# Third-party imports
# (none in this file)

# Local application imports
# (none in this file)

logger = logging.getLogger(__name__)

class RegionType(Enum):
    """Types of code regions that can be tested."""
    CLASS = 'class'
    FUNCTION = 'function'
    MODULE = 'module'

class ImportType(Enum):
    """Types of imports that can be handled."""
    SIMPLE = 'simple'  # import x
    FROM = 'from'      # from x import y
    RELATIVE = 'relative'  # from . import x
    ALIAS = 'alias'    # import x as y
    STAR = 'star'      # from x import *

@dataclass(frozen=True)
class ImportInfo:
    """Information about an import statement."""
    type: ImportType
    module: str
    names: List[str]
    aliases: Dict[str, str]  # Maps original names to aliases
    level: int = 0  # For relative imports

@dataclass(frozen=True)
class ModuleInfo:
    """Information about a Python module."""
    name: str
    path: Path
    is_package: bool
    is_third_party: bool
    version: Optional[str] = None
    dependencies: FrozenSet[str] = frozenset()

@dataclass
class RegionInfo:
    """Information about a code region."""
    type: RegionType
    name: str
    code: str
    start_line: int
    end_line: int
    imports: List[ImportInfo]
    dependencies: FrozenSet[ModuleInfo]
    class_methods: List[str] = None
    file_path: Optional[Path] = None

class DependencyResolver:
    """Resolves module dependencies and handles import cycles."""
    
    def __init__(self, workspace_root: Path):
        """Initialize the dependency resolver.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = workspace_root
        self._module_cache: Dict[str, ModuleInfo] = {}
        self._import_graph: Dict[str, Set[str]] = defaultdict(set)
        self._visited: Set[str] = set()
        self._temp_visited: Set[str] = set()
    
    def resolve_dependencies(self, file_path: Path) -> FrozenSet[ModuleInfo]:
        """Resolve all dependencies for a file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            FrozenSet of ModuleInfo objects representing all dependencies
            
        Raises:
            ValueError: If circular dependencies are detected
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = self._extract_imports(tree)
            
            # Reset state for new resolution
            self._visited.clear()
            self._temp_visited.clear()
            self._import_graph.clear()
            
            # Build import graph
            for imp in imports:
                self._import_graph[file_path.name].add(imp)
            
            # Check for cycles
            self._check_cycles(file_path.name)
            
            # Resolve all dependencies
            dependencies = set()
            for imp in imports:
                module_info = self._resolve_module(imp)
                if module_info:
                    dependencies.add(module_info)
            
            return frozenset(dependencies)
            
        except Exception as e:
            raise ValueError(f"Failed to resolve dependencies for {file_path}: {str(e)}")
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract all imports from the AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                else:
                    module = node.module or ''
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")
        return imports
    
    def _check_cycles(self, module_name: str) -> None:
        """Check for circular dependencies using DFS.
        
        Args:
            module_name: Name of the module to check
            
        Raises:
            ValueError: If a circular dependency is detected
        """
        if module_name in self._temp_visited:
            cycle = list(self._temp_visited)
            cycle.append(module_name)
            raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        if module_name in self._visited:
            return
        
        self._temp_visited.add(module_name)
        
        for dep in self._import_graph[module_name]:
            self._check_cycles(dep)
        
        self._temp_visited.remove(module_name)
        self._visited.add(module_name)
    
    def _resolve_module(self, module_name: str) -> Optional[ModuleInfo]:
        """Resolve a module to its file path and metadata.
        
        Args:
            module_name: Name of the module to resolve
            
        Returns:
            ModuleInfo if module is found, None otherwise
        """
        if module_name in self._module_cache:
            return self._module_cache[module_name]
        
        try:
            # Try to import the module
            spec = importlib.util.find_spec(module_name)
            if spec and spec.origin:
                path = Path(spec.origin)
                is_package = spec.submodule_search_locations is not None
                is_third_party = not str(path).startswith(str(self.workspace_root))
                
                module_info = ModuleInfo(
                    name=module_name,
                    path=path,
                    is_package=is_package,
                    is_third_party=is_third_party
                )
                
                self._module_cache[module_name] = module_info
                return module_info
            
            # Try relative to workspace root
            module_path = self.workspace_root / module_name.replace('.', '/')
            if module_path.with_suffix('.py').exists():
                path = module_path.with_suffix('.py')
                module_info = ModuleInfo(
                    name=module_name,
                    path=path,
                    is_package=False,
                    is_third_party=False
                )
                self._module_cache[module_name] = module_info
                return module_info
            elif module_path.is_dir() and (module_path / '__init__.py').exists():
                path = module_path / '__init__.py'
                module_info = ModuleInfo(
                    name=module_name,
                    path=path,
                    is_package=True,
                    is_third_party=False
                )
                self._module_cache[module_name] = module_info
                return module_info
            
            return None
            
        except ImportError:
            return None

class ImportResolver:
    """Resolves and manages Python imports."""
    
    def __init__(self, workspace_root: Path):
        """Initialize the import resolver.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = workspace_root
        self._module_cache: Dict[str, ModuleInfo] = {}
        self._import_cache: Dict[str, Any] = {}
        self._setup_import_hooks()
    
    def _setup_import_hooks(self) -> None:
        """Set up custom import hooks if needed."""
        # Add custom import hooks here if needed
        pass
    
    def resolve_import(self, import_info: ImportInfo) -> Optional[Any]:
        """Resolve an import to its actual module or object.
        
        Args:
            import_info: Information about the import to resolve
            
        Returns:
            The imported module or object if successful, None otherwise
        """
        try:
            if import_info.type == ImportType.SIMPLE:
                return self._resolve_simple_import(import_info)
            elif import_info.type == ImportType.FROM:
                return self._resolve_from_import(import_info)
            elif import_info.type == ImportType.RELATIVE:
                return self._resolve_relative_import(import_info)
            elif import_info.type == ImportType.ALIAS:
                return self._resolve_alias_import(import_info)
            elif import_info.type == ImportType.STAR:
                return self._resolve_star_import(import_info)
            else:
                logger.warning(f"Unsupported import type: {import_info.type}")
                return None
        except Exception as e:
            logger.warning(f"Failed to resolve import {import_info}: {str(e)}")
            return None
    
    def _resolve_simple_import(self, import_info: ImportInfo) -> Optional[Any]:
        """Resolve a simple import (import x)."""
        try:
            module = __import__(import_info.module)
            return module
        except ImportError:
            return None
    
    def _resolve_from_import(self, import_info: ImportInfo) -> Dict[str, Any]:
        """Resolve a from import (from x import y)."""
        result = {}
        try:
            module = __import__(import_info.module, fromlist=import_info.names)
            for name in import_info.names:
                if hasattr(module, name):
                    result[name] = getattr(module, name)
        except ImportError:
            pass
        return result
    
    def _resolve_relative_import(self, import_info: ImportInfo) -> Optional[Any]:
        """Resolve a relative import (from . import x)."""
        try:
            module_name = import_info.module.lstrip('.')
            if not module_name:
                raise ImportError("Invalid relative import path")
            module = __import__(module_name, fromlist=['*'])
            return module
        except ImportError:
            return None
    
    def _resolve_alias_import(self, import_info: ImportInfo) -> Dict[str, Any]:
        """Resolve an alias import (import x as y)."""
        result = {}
        try:
            module = __import__(import_info.module)
            for orig_name, alias in import_info.aliases.items():
                if hasattr(module, orig_name):
                    result[alias] = getattr(module, orig_name)
        except ImportError:
            pass
        return result
    
    def _resolve_star_import(self, import_info: ImportInfo) -> Dict[str, Any]:
        """Resolve a star import (from x import *)."""
        result = {}
        try:
            module = __import__(import_info.module, fromlist=['*'])
            for name in dir(module):
                if not name.startswith('_'):
                    result[name] = getattr(module, name)
        except ImportError:
            pass
        return result

class CodeRegionExtractor:
    """Extracts and analyzes code regions from files."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the code region extractor.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.dependency_resolver = DependencyResolver(self.workspace_root)
    
    def extract_region(self, file_path: Path, region_name: str) -> RegionInfo:
        """
        Extract a code region from a file.
        
        Args:
            file_path: Path to the file
            region_name: Name of the region to extract
            
        Returns:
            RegionInfo object containing the extracted code and metadata
            
        Raises:
            ValueError: If region markers are not found or code is invalid
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # If region_name is 'main', use the entire file
            if region_name == 'main':
                code = content
                return self._analyze_region(code, region_name, file_path)
            
            # Otherwise look for region markers
            start_marker = f"# kaizen:start:{region_name}"
            end_marker = f"# kaizen:end:{region_name}"
            
            start_idx = content.find(start_marker)
            if start_idx == -1:
                raise ValueError(f"Start marker for region '{region_name}' not found")
            
            end_idx = content.find(end_marker)
            if end_idx == -1:
                raise ValueError(f"End marker for region '{region_name}' not found")
            
            start_idx = content.find('\n', start_idx) + 1
            code = content[start_idx:end_idx].strip()
            
            return self._analyze_region(code, region_name, file_path)
            
        except Exception as e:
            raise ValueError(f"Failed to extract region '{region_name}': {str(e)}")
    
    def _analyze_region(self, code: str, region_name: str, file_path: Path) -> RegionInfo:
        """Analyze the code region to determine its type, structure, and dependencies."""
        try:
            tree = ast.parse(code)
            imports = self._extract_imports(tree)
            region_type, name, methods = self._determine_region_type(tree)
            dependencies = self.dependency_resolver.resolve_dependencies(file_path)
            
            return RegionInfo(
                type=region_type,
                name=name or region_name,
                code=code,
                start_line=tree.body[0].lineno if tree.body else 1,
                end_line=tree.body[-1].end_lineno if tree.body else 1,
                imports=imports,
                dependencies=dependencies,
                class_methods=methods,
                file_path=file_path
            )
        except SyntaxError as e:
            raise ValueError(f"Invalid Python code in region: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to analyze region code: {str(e)}")
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract all imports from the AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                else:
                    module = node.module or ''
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")
        return imports
    
    def _determine_region_type(self, tree: ast.AST) -> tuple[RegionType, str, List[str]]:
        """Determine the type, name, and methods of the region."""
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get all methods in the class
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                return RegionType.CLASS, node.name, methods
            elif isinstance(node, ast.FunctionDef):
                return RegionType.FUNCTION, node.name, []
        return RegionType.MODULE, "module", []

class CodeRegionExecutor:
    """Executes code regions and manages their execution context."""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.import_resolver = ImportResolver(workspace_root)
        self._setup_python_path()
    
    def _setup_python_path(self) -> None:
        """Set up Python path with workspace root."""
        if str(self.workspace_root) not in sys.path:
            sys.path.insert(0, str(self.workspace_root))
    
    def execute_region(self, region_info: RegionInfo, method_name: Optional[str] = None, 
                      input_data: Any = None) -> Any:
        """Execute a code region and return its result."""
        try:
            # Add all dependency paths to Python path
            for dep in region_info.dependencies:
                if not dep.is_third_party:
                    dep_dir = str(dep.path.parent)
                    if dep_dir not in sys.path:
                        sys.path.insert(0, dep_dir)
            
            with self._create_execution_context(region_info) as namespace:
                # Set up imports
                self._setup_imports(region_info, namespace)
                
                if region_info.type == RegionType.CLASS:
                    return self._execute_class_method(namespace, region_info, method_name, input_data)
                elif region_info.type == RegionType.FUNCTION:
                    return self._execute_function(namespace, region_info, input_data)
                else:
                    return self._execute_module(namespace, region_info, method_name, input_data)
        except Exception as e:
            raise ValueError(f"Failed to execute region '{region_info.name}': {str(e)}")
        finally:
            # Clean up added paths
            for dep in region_info.dependencies:
                if not dep.is_third_party:
                    dep_dir = str(dep.path.parent)
                    if dep_dir in sys.path:
                        sys.path.remove(dep_dir)
    
    def _setup_imports(self, region_info: RegionInfo, namespace: Dict) -> None:
        """Set up all necessary imports in the namespace."""
        # Add standard library imports
        for module_name in ['typing', 'os', 'sys', 'pathlib']:
            try:
                module = __import__(module_name)
                namespace[module_name] = module
            except ImportError:
                pass
        
        # Add imports from the region
        for import_info in region_info.imports:
            result = self.import_resolver.resolve_import(import_info)
            if result:
                if isinstance(result, dict):
                    namespace.update(result)
                else:
                    namespace[import_info.module] = result
    
    @contextmanager
    def _create_execution_context(self, region_info: RegionInfo):
        """Create a safe execution context."""
        namespace = {
            '__name__': '__main__',
            '__file__': str(region_info.file_path) if region_info.file_path else None,
            '__package__': None,
            '__builtins__': __builtins__
        }
        
        # Execute the code
        exec(region_info.code, namespace)
        yield namespace
    
    def _execute_class_method(self, namespace: Dict, region_info: RegionInfo, 
                            method_name: str, input_data: Any) -> Any:
        """Execute a method from a class."""
        if not method_name:
            raise ValueError(f"Method name required for class region '{region_info.name}'")
        
        if method_name not in region_info.class_methods:
            raise ValueError(f"Method '{method_name}' not found in class '{region_info.name}'")
        
        # Create instance and get method
        instance = namespace[region_info.name]()
        method = getattr(instance, method_name)
        
        # Validate input data
        if input_data is None:
            raise ValueError(f"Input data required for method '{method_name}'")
        
        # If input_data is a string, ensure it's not empty
        if isinstance(input_data, str) and not input_data.strip():
            raise ValueError(f"Input data for method '{method_name}' cannot be empty")
        
        # Execute the method
        try:
            return method(input_data)
        except Exception as e:
            raise ValueError(f"Error executing method '{method_name}': {str(e)}")
    
    def _execute_function(self, namespace: Dict, region_info: RegionInfo, 
                         input_data: Any) -> Any:
        """Execute a function."""
        func = namespace[region_info.name]
        
        # Validate input data
        if input_data is None:
            raise ValueError(f"Input data required for function '{region_info.name}'")
        
        # If input_data is a string, ensure it's not empty
        if isinstance(input_data, str) and not input_data.strip():
            raise ValueError(f"Input data for function '{region_info.name}' cannot be empty")
        
        try:
            return func(input_data)
        except Exception as e:
            raise ValueError(f"Error executing function '{region_info.name}': {str(e)}")
    
    def _execute_module(self, namespace: Dict, region_info: RegionInfo, 
                       method_name: str, input_data: Any) -> Any:
        """Execute a module-level function."""
        if not method_name:
            raise ValueError(f"Method name required for module region '{region_info.name}'")
        
        if method_name not in namespace:
            raise ValueError(f"Function '{method_name}' not found in module")
        
        func = namespace[method_name]
        
        # Validate input data
        if input_data is None:
            raise ValueError(f"Input data required for function '{method_name}'")
        
        # If input_data is a string, ensure it's not empty
        if isinstance(input_data, str) and not input_data.strip():
            raise ValueError(f"Input data for function '{method_name}' cannot be empty")
        
        try:
            return func(input_data)
        except Exception as e:
            raise ValueError(f"Error executing function '{method_name}': {str(e)}") 