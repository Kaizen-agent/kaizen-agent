"""Code region extraction and execution."""

# Standard library imports
import ast
import logging
import os
import sys
import importlib
import importlib.util
import importlib.machinery
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Set, FrozenSet, Union, Type, TypeVar, Generic
from collections import defaultdict
import typing
import builtins
import re
import tempfile
import json
import subprocess
import shutil
import hashlib
import time

# Third-party imports
# (none in this file)

# Local application imports
from .input_parser import InputParser, InputParsingError
from .variable_tracker import VariableTracker, track_variables, safe_serialize_value
from .simple_import_resolver import SimpleImportResolver

# Configure colored logging
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors."""
    
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',   # Green
        'WARNING': '\033[33m', # Yellow
        'ERROR': '\033[31m',   # Red
        'CRITICAL': '\033[41m', # Red background
        'RESET': '\033[0m'    # Reset
    }
    
    def format(self, record):
        # Only color the level name, not the entire message
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)  # Default to INFO level

def set_log_level(level: str) -> None:
    """Set the logging level.
    
    Args:
        level: One of 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))

# Type variables for generic types
T = TypeVar('T')

# Constants
STANDARD_MODULES = frozenset({
    'typing', 'os', 'sys', 'pathlib', 'collections', 'dataclasses', 
    'enum', 'logging', 'importlib', 'ast', 'contextlib', 'json',
    'datetime', 'time', 're', 'math', 'random', 'itertools', 'functools'
})

class CodeRegionError(Exception):
    """Base exception for code region related errors."""
    pass

class RegionExtractionError(CodeRegionError):
    """Exception raised when region extraction fails."""
    pass

class DependencyResolutionError(CodeRegionError):
    """Exception raised when dependency resolution fails."""
    pass

class ImportError(CodeRegionError):
    """Exception raised when import handling fails."""
    pass

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

class ImportErrorType(Enum):
    """Types of import errors that can occur."""
    MODULE_NOT_FOUND = "module_not_found"
    IMPORT_ERROR = "import_error"
    ATTRIBUTE_ERROR = "attribute_error"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass(frozen=True)
class ImportInfo:
    """Information about an import statement.
    
    Attributes:
        type: Type of import statement
        module: Module being imported
        names: List of names being imported
        aliases: Dictionary mapping original names to aliases
        level: Level of relative import (0 for absolute)
    """
    type: ImportType
    module: str
    names: List[str]
    aliases: Dict[str, str]
    level: int = 0

@dataclass(frozen=True)
class ModuleInfo:
    """Information about a Python module.
    
    Attributes:
        name: Name of the module
        path: Path to the module file
        is_package: Whether the module is a package
        is_third_party: Whether the module is third-party
        version: Optional version information
        dependencies: Set of module dependencies
    """
    name: str
    path: Path
    is_package: bool
    is_third_party: bool
    version: Optional[str] = None
    dependencies: FrozenSet[str] = frozenset()

@dataclass
class AgentEntryPoint:
    """Configuration for agent entry point without markers.
    
    Attributes:
        module: Module path (e.g., 'path.to.module')
        class_name: Class name to instantiate (optional)
        method: Method name to call (optional)
        fallback_to_function: Whether to fallback to function if class/method not found
    """
    module: str
    class_name: Optional[str] = None
    method: Optional[str] = None
    fallback_to_function: bool = True

@dataclass
class RegionInfo:
    """Information about a code region.
    
    Attributes:
        type: Type of the region
        name: Name of the region
        code: The actual code content
        start_line: Starting line number
        end_line: Ending line number
        imports: List of imports in the region
        dependencies: Set of module dependencies
        class_methods: Optional list of class methods
        file_path: Optional path to the source file
        entry_point: Optional agent entry point configuration
    """
    type: RegionType
    name: str
    code: str
    start_line: int
    end_line: int
    imports: List[ImportInfo]
    dependencies: FrozenSet[ModuleInfo]
    class_methods: Optional[List[str]] = None
    file_path: Optional[Path] = None
    entry_point: Optional[AgentEntryPoint] = None

@dataclass
class ImportError:
    """Detailed information about an import error."""
    type: ImportErrorType
    module_name: str
    message: str
    original_error: Optional[Exception] = None

@dataclass
class PackageConfig:
    """Configuration for package imports."""
    name: str
    import_name: str  # The actual name used in import statements
    required: bool = False
    fallback_names: List[str] = field(default_factory=list)
    special_import: Optional[str] = None  # Special import statement if needed

@dataclass
class ImportManagerConfig:
    """Configuration for the ImportManager."""
    common_packages: Dict[str, PackageConfig] = field(default_factory=dict)
    standard_libs: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Initialize with default configurations if not provided."""
        if not self.common_packages:
            self._load_default_package_config()
        if not self.standard_libs:
            self._load_default_standard_libs()
    
    def _load_default_package_config(self):
        """Load default package configuration."""
        # This can be overridden by external configuration files
        self.common_packages = {
            'python-dotenv': PackageConfig(
                name='python-dotenv',
                import_name='dotenv',
                required=True,
                fallback_names=['dotenv'],
                special_import='from dotenv import load_dotenv'
            ),
            'google-generativeai': PackageConfig(
                name='google-generativeai',
                import_name='google.generativeai',
                required=True,
                fallback_names=['genai'],
                special_import='import google.generativeai as genai'
            ),
            'openai': PackageConfig(
                name='openai',
                import_name='openai',
                required=True
            ),
            'click': PackageConfig(
                name='click',
                import_name='click',
                required=True
            ),
            'pyyaml': PackageConfig(
                name='pyyaml',
                import_name='yaml',
                required=True,
                fallback_names=['yaml']
            ),
            'PyGithub': PackageConfig(
                name='PyGithub',
                import_name='github',
                required=False,
                fallback_names=['github']
            ),
            'anthropic': PackageConfig(
                name='anthropic',
                import_name='anthropic',
                required=False
            ),
            'typing_extensions': PackageConfig(
                name='typing_extensions',
                import_name='typing_extensions',
                required=False
            )
        }
    
    def _load_default_standard_libs(self):
        """Load default standard library configuration."""
        self.standard_libs = {
            'typing', 'os', 'sys', 'pathlib', 'collections', 'dataclasses', 
            'enum', 'logging', 'importlib', 'ast', 'contextlib', 'json',
            'datetime', 'time', 're', 'math', 'random', 'itertools', 'functools'
        }
    
    def load_from_file(self, config_path: Path) -> None:
        """Load configuration from a file."""
        try:
            import yaml
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if 'packages' in config_data:
                for package_name, package_data in config_data['packages'].items():
                    self.common_packages[package_name] = PackageConfig(**package_data)
            
            if 'standard_libs' in config_data:
                self.standard_libs = set(config_data['standard_libs'])
                
        except Exception as e:
            logger.warning(f"Failed to load ImportManagerConfig from {config_path}: {str(e)}")

class DependencyResolver:
    """Resolves module dependencies and handles import cycles."""
    
    def __init__(self, workspace_root: Path) -> None:
        """Initialize the dependency resolver."""
        self.workspace_root = workspace_root
        self._module_cache: Dict[str, ModuleInfo] = {}
        self._import_graph: Dict[str, Set[str]] = defaultdict(set)
        self._visited: Set[str] = set()
        self._temp_visited: Set[str] = set()
        self._builtin_modules = frozenset(sys.builtin_module_names)
        self._typing_types = frozenset({
            'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet', 
            'Union', 'Any', 'Callable', 'TypeVar', 'Generic', 'Type',
            'Protocol', 'runtime_checkable', 'overload', 'final',
            'Literal', 'TypedDict', 'cast', 'get_type_hints'
        })
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract all imports from the AST.
        
        Args:
            tree: AST to analyze
            
        Returns:
            List of import statements
        """
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        # Handle typing imports specially
                        if name.name.startswith('typing.'):
                            base_name = name.name.split('.')[0]
                            imports.append(base_name)
                        else:
                            imports.append(name.name)
                else:  # ImportFrom
                    module = node.module or ''
                    for name in node.names:
                        # Handle typing imports specially
                        if module == 'typing' or module.startswith('typing.'):
                            imports.append('typing')
                        else:
                            imports.append(f"{module}.{name.name}")
        return list(set(imports))  # Remove duplicates
    
    def resolve_dependencies(self, file_path: Path) -> FrozenSet[ModuleInfo]:
        """Resolve all dependencies for a file."""
        logger.info(f"Resolving dependencies: {file_path.name}")
        try:
            logger.debug(f"DEBUG: Opening file for dependency resolution: {file_path}")
            with open(file_path, 'r') as f:
                content = f.read()
            logger.debug(f"DEBUG: Successfully read file for dependency resolution ({len(content)} characters)")
            
            logger.debug(f"DEBUG: Parsing AST for dependency resolution")
            tree = ast.parse(content)
            logger.debug(f"DEBUG: AST parsing completed for dependency resolution")
            
            logger.debug(f"DEBUG: Extracting imports for dependency resolution")
            imports = self._extract_imports(tree)
            logger.debug(f"DEBUG: Found {len(imports)} imports for dependency resolution: {imports}")
            
            logger.debug(f"DEBUG: Resetting dependency resolver state")
            self._reset_state()
            
            logger.debug(f"DEBUG: Building import graph")
            self._build_import_graph(file_path.name, imports)
            logger.debug(f"DEBUG: Import graph built")
            
            logger.debug(f"DEBUG: Checking for cycles")
            self._check_cycles(file_path.name)
            logger.debug(f"DEBUG: Cycle check completed")
            
            logger.debug(f"DEBUG: Resolving all dependencies")
            dependencies = self._resolve_all_dependencies(imports)
            logger.debug(f"DEBUG: Dependency resolution completed, found {len(dependencies)} dependencies")
            
            logger.debug(f"✓ Dependencies resolved: {len(dependencies)} found")
            return frozenset(dependencies)
            
        except (IOError, SyntaxError) as e:
            logger.error(f"✗ Failed to read/parse: {file_path.name}")
            raise RegionExtractionError(f"Failed to read or parse file {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"✗ Dependency resolution failed: {file_path.name}")
            logger.error(f"DEBUG: Full traceback for dependency resolution error: {traceback.format_exc()}")
            raise DependencyResolutionError(f"Failed to resolve dependencies for {file_path}: {str(e)}")
    
    def _reset_state(self) -> None:
        """Reset the internal state for a new resolution."""
        self._visited.clear()
        self._temp_visited.clear()
        self._import_graph.clear()
    
    def _build_import_graph(self, file_name: str, imports: List[str]) -> None:
        """Build the import graph for a file.
        
        Args:
            file_name: Name of the file
            imports: List of imports to add to the graph
        """
        for imp in imports:
            self._import_graph[file_name].add(imp)
    
    def _resolve_all_dependencies(self, imports: List[str]) -> Set[ModuleInfo]:
        """Resolve all dependencies from a list of imports.
        
        Args:
            imports: List of import statements
            
        Returns:
            Set of resolved ModuleInfo objects
        """
        logger.debug(f"DEBUG: Starting to resolve {len(imports)} dependencies")
        dependencies = set()
        for i, imp in enumerate(imports):
            logger.debug(f"DEBUG: Resolving dependency {i+1}/{len(imports)}: {imp}")
            module_info = self._resolve_module(imp)
            if module_info:
                logger.debug(f"DEBUG: Successfully resolved {imp} -> {module_info.name}")
                dependencies.add(module_info)
            else:
                logger.debug(f"DEBUG: Could not resolve {imp}")
        logger.debug(f"DEBUG: Completed resolving dependencies, found {len(dependencies)} modules")
        return dependencies
    
    def _resolve_module(self, module_name: str) -> Optional[ModuleInfo]:
        """Resolve a module to its file path and metadata.
        
        Args:
            module_name: Name of the module to resolve
            
        Returns:
            ModuleInfo if module is found, None otherwise
        """
        logger.debug(f"DEBUG: Resolving module: {module_name}")
        
        if module_name in self._module_cache:
            logger.debug(f"DEBUG: Found {module_name} in cache")
            return self._module_cache[module_name]
        
        try:
            # Handle typing module specially
            if module_name == 'typing':
                logger.debug(f"DEBUG: Handling typing module specially")
                return self._resolve_typing_module()
            
            # Handle standard library modules
            if module_name in STANDARD_MODULES:
                logger.debug(f"DEBUG: {module_name} is a standard module")
                module_info = self._resolve_standard_module(module_name)
                self._module_cache[module_name] = module_info
                return module_info
            
            # Check if this is a local module that should be handled
            # We need to handle local modules to import user-defined classes
            if '.' in module_name:
                logger.debug(f"DEBUG: Handling local module resolution for {module_name}")
                return self._resolve_workspace_module(module_name)
            
            # Handle third-party modules
            logger.debug(f"DEBUG: {module_name} is a third-party module")
            return self._resolve_third_party_module(module_name)
            
        except Exception as e:
            logger.debug(f"Failed to resolve module {module_name}: {str(e)}")
            logger.debug(f"DEBUG: Exception details for {module_name}: {traceback.format_exc()}")
            return None
    
    def _resolve_typing_module(self) -> ModuleInfo:
        """Resolve the typing module with special handling.
        
        Returns:
            ModuleInfo for the typing module
        """
        return ModuleInfo(
            name='typing',
            path=Path('typing'),
            is_package=False,
            is_third_party=False,
            version=sys.version,
            dependencies=frozenset()
        )
    
    def _resolve_standard_module(self, module_name: str) -> ModuleInfo:
        """Resolve a standard library module.
        
        Args:
            module_name: Name of the standard library module
            
        Returns:
            ModuleInfo for the standard library module
        """
        try:
            # Handle built-in modules
            if module_name in self._builtin_modules:
                return ModuleInfo(
                    name=module_name,
                    path=Path(f"<built-in module {module_name}>"),
                    is_package=False,
                    is_third_party=False,
                    version=sys.version
                )
            
            # Handle standard library modules
            if module_name in sys.modules:
                module = sys.modules[module_name]
                try:
                    path = Path(module.__file__) if hasattr(module, '__file__') else Path(module_name)
                except (builtins.AttributeError, TypeError):
                    path = Path(module_name)
                
                return ModuleInfo(
                    name=module_name,
                    path=path,
                    is_package=hasattr(module, '__path__'),
                    is_third_party=False,
                    version=getattr(module, '__version__', None)
                )
            
            # Try importing the module
            try:
                module = __import__(module_name)
                path = Path(module.__file__) if hasattr(module, '__file__') else Path(module_name)
                return ModuleInfo(
                    name=module_name,
                    path=path,
                    is_package=hasattr(module, '__path__'),
                    is_third_party=False,
                    version=getattr(module, '__version__', None)
                )
            except builtins.ImportError:
                logger.warning(f"Could not import standard module: {module_name}")
                return ModuleInfo(
                    name=module_name,
                    path=Path(module_name),
                    is_package=False,
                    is_third_party=False
                )
                
        except Exception as e:
            logger.error(f"Failed to resolve standard module {module_name}: {str(e)}")
            raise DependencyResolutionError(f"Failed to resolve standard module {module_name}: {str(e)}")
    
    def _resolve_third_party_module(self, module_name: str) -> Optional[ModuleInfo]:
        """Resolve a third-party module.
        
        Args:
            module_name: Name of the third-party module
            
        Returns:
            ModuleInfo if module is found, None otherwise
        """
        # Try to import the module
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            return self._create_module_info(module_name, spec)
        
        # Try relative to workspace root
        return self._resolve_workspace_module(module_name)
    
    def _create_module_info(self, module_name: str, spec: importlib.machinery.ModuleSpec) -> ModuleInfo:
        """Create a ModuleInfo object from a module spec.
        
        Args:
            module_name: Name of the module
            spec: Module specification
            
        Returns:
            ModuleInfo object
        """
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
    
    def _resolve_workspace_module(self, module_name: str) -> Optional[ModuleInfo]:
        """Resolve a module from the workspace.
        
        Args:
            module_name: Name of the module
            
        Returns:
            ModuleInfo if module is found, None otherwise
        """
        # Handle different module path formats
        if '.' in module_name:
            # Convert module path to file path
            module_parts = module_name.split('.')
            module_path = self.workspace_root
            
            # Build the path by joining parts
            for part in module_parts:
                module_path = module_path / part
            
            logger.debug(f"DEBUG: Resolving workspace module {module_name} to path {module_path}")
        else:
            module_path = self.workspace_root / module_name
        
        # Try as a Python file
        py_file = module_path.with_suffix('.py')
        if py_file.exists():
            logger.debug(f"DEBUG: Found Python file: {py_file}")
            return ModuleInfo(
                name=module_name,
                path=py_file,
                is_package=False,
                is_third_party=False
            )
        
        # Try as a package (directory with __init__.py)
        if module_path.is_dir():
            init_file = module_path / '__init__.py'
            if init_file.exists():
                logger.debug(f"DEBUG: Found package: {init_file}")
                return ModuleInfo(
                    name=module_name,
                    path=init_file,
                    is_package=True,
                    is_third_party=False
                )
        
        # Try alternative paths (common patterns)
        alternative_paths = [
            self.workspace_root / module_name.replace('.', '/') / '__init__.py',
            self.workspace_root / module_name.replace('.', '/').with_suffix('.py'),
            self.workspace_root / 'src' / module_name.replace('.', '/') / '__init__.py',
            self.workspace_root / 'src' / module_name.replace('.', '/').with_suffix('.py'),
        ]
        
        for alt_path in alternative_paths:
            if alt_path.exists():
                logger.debug(f"DEBUG: Found module at alternative path: {alt_path}")
                return ModuleInfo(
                    name=module_name,
                    path=alt_path,
                    is_package=alt_path.name == '__init__.py',
                    is_third_party=False
                )
        
        logger.debug(f"DEBUG: Module {module_name} not found in workspace")
        return None
    
    def _check_cycles(self, module_name: str) -> None:
        """Check for circular dependencies using DFS.
        
        Args:
            module_name: Name of the module to check
            
        Raises:
            DependencyResolutionError: If a circular dependency is detected
        """
        if module_name in self._temp_visited:
            cycle = list(self._temp_visited)
            cycle.append(module_name)
            raise DependencyResolutionError(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        if module_name in self._visited:
            return
        
        self._temp_visited.add(module_name)
        
        for dep in self._import_graph[module_name]:
            self._check_cycles(dep)
        
        self._temp_visited.remove(module_name)
        self._visited.add(module_name)

class ImportAnalyzer:
    """Analyzes code to identify all required imports."""
    
    def __init__(self):
        self._standard_libs = {
            'typing', 'os', 'sys', 'pathlib', 'collections', 'dataclasses', 
            'enum', 'logging', 'importlib', 'ast', 'contextlib', 'json',
            'datetime', 'time', 're', 'math', 'random', 'itertools', 'functools'
        }
    
    def analyze_imports(self, code: str) -> Tuple[Set[str], Set[str]]:
        """Analyze code to identify all required imports.
        
        Returns:
            Tuple[Set[str], Set[str]]: (standard_lib_imports, third_party_imports)
        """
        try:
            tree = ast.parse(code)
            standard_imports = set()
            third_party_imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            module_name = name.name.split('.')[0]
                            if module_name in self._standard_libs:
                                standard_imports.add(module_name)
                            else:
                                # Skip local modules with dots (they'll be handled by CLI dependency manager)
                                if '.' not in module_name or module_name.startswith(('google', 'openai', 'anthropic', 'click', 'rich', 'yaml')):
                                    third_party_imports.add(module_name)
                    else:  # ImportFrom
                        if node.module:
                            module_name = node.module.split('.')[0]
                            if module_name in self._standard_libs:
                                standard_imports.add(module_name)
                            else:
                                # Skip local modules with dots (they'll be handled by CLI dependency manager)
                                if '.' not in module_name or module_name.startswith(('google', 'openai', 'anthropic', 'click', 'rich', 'yaml')):
                                    third_party_imports.add(module_name)
            
            return standard_imports, third_party_imports
            
        except SyntaxError as e:
            logger.error(f"Syntax error in code: {str(e)}")
            return set(), set()
        except Exception as e:
            logger.error(f"Error analyzing imports: {str(e)}")
            return set(), set()

class ImportManager:
    """Manages imports for code region execution."""
    
    def __init__(self, workspace_root: Path, config: Optional[ImportManagerConfig] = None):
        """Initialize the import manager.
        
        Args:
            workspace_root: Root directory of the workspace
            config: Optional configuration for the import manager
        """
        self.workspace_root = workspace_root
        self.config = config or ImportManagerConfig()
        
        # Try to load configuration from file
        config_path = Path(__file__).parent / "package_config.yaml"
        if config_path.exists():
            self.config.load_from_file(config_path)
        
        self._original_sys_path = sys.path.copy()
        self._added_paths: Set[str] = set()
        self._processed_files: Set[Path] = set()
        self._module_cache: Dict[str, Any] = {}
        self._import_analyzer = ImportAnalyzer()
        self._import_errors: List[ImportError] = []
    
    @contextmanager
    def managed_imports(self, region_info: RegionInfo) -> Dict[str, Any]:
        """Context manager for managing imports during execution."""
        try:
            # First analyze all required imports
            standard_imports, third_party_imports = self._import_analyzer.analyze_imports(region_info.code)
            logger.debug(f"standard_imports: {standard_imports}")
            logger.debug(f"third_party_imports: {third_party_imports}")
            # Add configured third-party packages to imports
            third_party_imports.update(self.config.common_packages.keys())
            
            # Create namespace with all required imports
            namespace = self._create_namespace(standard_imports, third_party_imports)
            
            # Set up import environment
            self._setup_import_environment(region_info)
            
            # Process dependencies
            self._process_dependencies(region_info, namespace)
            
            # Check for required package import errors
            self._check_required_imports()
            
            yield namespace
            
        finally:
            self.cleanup()
    
    def _create_namespace(self, standard_imports: Set[str], third_party_imports: Set[str]) -> Dict[str, Any]:
        """Create namespace with all required imports."""
        # Import builtins module to ensure we have proper access to all built-in types
        import builtins
        
        namespace = {
            '__name__': '__main__',
            '__file__': None,
            '__package__': None,
            # Use the builtins module directly instead of __builtins__
            '__builtins__': builtins.__dict__,
        }
        
        # Also explicitly add the built-in exception types to ensure they're available
        namespace['Exception'] = builtins.Exception
        namespace['ValueError'] = builtins.ValueError
        namespace['TypeError'] = builtins.TypeError
        namespace['AttributeError'] = builtins.AttributeError
        namespace['ImportError'] = builtins.ImportError
        namespace['BaseException'] = builtins.BaseException
        
        # Always add typing module and its common types first
        namespace['typing'] = typing
        self._add_typing_imports(namespace)
        
        # Add standard library imports
        for module_name in standard_imports:
            try:
                module = __import__(module_name)
                namespace[module_name] = module
            except builtins.ImportError as e:
                self._record_import_error(
                    ImportErrorType.IMPORT_ERROR,
                    module_name,
                    f"Failed to import standard library {module_name}",
                    e
                )
        
        # Add third-party imports with better error handling
        for module_name in third_party_imports:
            self._import_package(module_name, namespace)
        
        return namespace
    
    def _import_package(self, package_name: str, namespace: Dict[str, Any]) -> None:
        """Import a package with proper error handling and fallbacks."""
        if package_name not in self.config.common_packages:
            # Handle unknown packages
            try:
                module = __import__(package_name)
                namespace[package_name] = module
            except builtins.ImportError as e:
                self._record_import_error(
                    ImportErrorType.IMPORT_ERROR,
                    package_name,
                    f"Failed to import unknown package {package_name}",
                    e
                )
            return
        
        config = self.config.common_packages[package_name]
        
        # Try primary import
        try:
            if config.special_import:
                # Execute special import statement
                exec(config.special_import, namespace)
            else:
                module = __import__(config.import_name)
                namespace[config.import_name] = module
            return
        except builtins.ImportError as e:
            self._record_import_error(
                ImportErrorType.IMPORT_ERROR,
                package_name,
                f"Failed to import {package_name} using primary method",
                e
            )
        
        # Try fallback imports
        for fallback_name in config.fallback_names:
            try:
                module = __import__(fallback_name)
                namespace[fallback_name] = module
                return
            except builtins.ImportError:
                continue
        
        # If we get here, all import attempts failed
        if config.required:
            self._record_import_error(
                ImportErrorType.MODULE_NOT_FOUND,
                package_name,
                f"Required package {package_name} could not be imported"
            )
    
    def _record_import_error(self, error_type: ImportErrorType, module_name: str, 
                           message: str, original_error: Optional[Exception] = None) -> None:
        """Record an import error for later analysis."""
        error = ImportError(
            type=error_type,
            module_name=module_name,
            message=message,
            original_error=original_error
        )
        self._import_errors.append(error)
        logger.warning(f"Import error: {message}")
        if original_error:
            logger.debug(f"Original error: {str(original_error)}")
    
    def _check_required_imports(self) -> None:
        """Check if all required imports were successful."""
        failed_required = [
            error for error in self._import_errors
            if error.module_name in self.config.common_packages
            and self.config.common_packages[error.module_name].required
        ]
        
        if failed_required:
            error_messages = [f"{error.module_name}: {error.message}" for error in failed_required]
            raise builtins.ImportError(
                f"Failed to import required packages:\n" + "\n".join(error_messages)
            )
    
    def _add_typing_imports(self, namespace: Dict[str, Any]) -> None:
        """Add all common typing imports to namespace."""
        # Common typing imports that are frequently used
        typing_imports = {
            'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet', 
            'Union', 'Any', 'Callable', 'TypeVar', 'Generic', 'Type',
            'Protocol', 'runtime_checkable', 'overload', 'final',
            'Literal', 'TypedDict', 'cast', 'get_type_hints',
            'Sequence', 'Mapping', 'Iterable', 'Iterator', 'AsyncIterator',
            'Awaitable', 'Coroutine', 'AsyncGenerator', 'AsyncIterable'
        }
        
        # Add each typing import to the namespace
        for name in typing_imports:
            try:
                namespace[name] = getattr(typing, name)
            except builtins.AttributeError:
                logger.warning(f"Type {name} not found in typing module")
        
        # Also add typing module itself
        namespace['typing'] = typing
    
    def _setup_import_environment(self, region_info: RegionInfo) -> None:
        """Set up the import environment for execution."""
        if region_info.file_path:
            self._add_to_python_path(region_info.file_path.parent)
    
    def _add_to_python_path(self, directory: Path) -> None:
        """Add directory to Python path if not already present."""
        dir_str = str(directory)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)
            self._added_paths.add(dir_str)
    
    def _process_dependencies(self, region_info: RegionInfo, namespace: Dict[str, Any]) -> None:
        """Process all dependencies recursively."""
        if region_info.file_path in self._processed_files:
            return
        
        self._processed_files.add(region_info.file_path)
        
        # Process dependencies
        for dep in region_info.dependencies:
            if not dep.is_third_party:
                self._add_to_python_path(dep.path.parent)
                if dep.path not in self._processed_files:
                    self._process_file_dependencies(dep.path, namespace)
        
        # Process imports
        for import_info in region_info.imports:
            self._execute_import(import_info, namespace)
    
    def _is_system_module(self, file_path: Path) -> bool:
        """Check if the file path represents a system or built-in module.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if the path represents a system module
        """
        return (str(file_path).startswith('<built-in module') or 
                str(file_path).startswith('/') or
                not file_path.exists())

    def _process_imports(self, imports: Set[str], namespace: Dict[str, Any], is_standard: bool) -> None:
        """Process a set of imports and add them to the namespace.
        
        Args:
            imports: Set of import names to process
            namespace: Dictionary to add imports to
            is_standard: Whether these are standard library imports
        """
        for module_name in imports:
            if module_name not in namespace:
                try:
                    module = __import__(module_name)
                    namespace[module_name] = module
                    if is_standard and module_name == 'typing':
                        self._add_typing_imports(namespace)
                except builtins.ImportError as e:
                    logger.warning(f"Failed to import {module_name}: {str(e)}")

    def _process_file_dependencies(self, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Process dependencies of a single file.
        
        Args:
            file_path: Path to the file to process
            namespace: Dictionary to add imports to
            
        Raises:
            IOError: If the file cannot be read
            SyntaxError: If the file contains invalid Python code
        """
        try:
            # Skip system and built-in modules
            if self._is_system_module(file_path):
                logger.debug(f"Skipping system module: {file_path}")
                return

            # Read and parse file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except IOError as e:
                logger.error(f"Failed to read file {file_path}: {str(e)}")
                raise

            # Analyze imports
            try:
                standard_imports, third_party_imports = self._import_analyzer.analyze_imports(content)
            except SyntaxError as e:
                logger.error(f"Invalid Python code in {file_path}: {str(e)}")
                raise

            # Process imports
            self._process_imports(standard_imports, namespace, is_standard=True)
            self._process_imports(third_party_imports, namespace, is_standard=False)

        except (IOError, SyntaxError) as e:
            # Re-raise specific exceptions
            raise
        except Exception as e:
            # Log unexpected errors but don't break execution
            logger.error(f"Unexpected error processing {file_path}: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def _execute_import(self, import_info: ImportInfo, namespace: Dict[str, Any]) -> None:
        """Execute a single import statement in the namespace."""
        try:
            if import_info.module in self._module_cache:
                module = self._module_cache[import_info.module]
            else:
                module = self._load_module(import_info)
                self._module_cache[import_info.module] = module
            
            # Special handling for typing imports
            if import_info.module == 'typing':
                self._handle_typing_import(import_info, module, namespace)
            else:
                self._add_to_namespace(import_info, module, namespace)
            
        except builtins.ImportError as e:
            logger.warning(f"Failed to import {import_info}: {str(e)}")
            self._try_find_module_in_workspace(import_info, namespace)
    
    def _handle_typing_import(self, import_info: ImportInfo, module: Any, namespace: Dict[str, Any]) -> None:
        """Handle typing imports specially to ensure all types are available."""
        if import_info.type == ImportType.FROM:
            for name in import_info.names:
                if name == '*':
                    # Add all common typing types
                    typing_imports = {
                        'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet', 
                        'Union', 'Any', 'Callable', 'TypeVar', 'Generic', 'Type',
                        'Protocol', 'runtime_checkable', 'overload', 'final',
                        'Literal', 'TypedDict', 'cast', 'get_type_hints'
                    }
                    for type_name in typing_imports:
                        try:
                            namespace[type_name] = getattr(module, type_name)
                        except builtins.AttributeError:
                            logger.warning(f"Type {type_name} not found in typing module")
                else:
                    try:
                        namespace[name] = getattr(module, name)
                    except builtins.AttributeError:
                        logger.warning(f"Type {name} not found in typing module")
        else:
            namespace['typing'] = module
    
    def _load_module(self, import_info: ImportInfo) -> Any:
        """Load a module using Python's import system."""
        if import_info.type == ImportType.SIMPLE:
            return __import__(import_info.module)
        elif import_info.type in (ImportType.FROM, ImportType.STAR):
            return __import__(import_info.module, fromlist=['*'])
        elif import_info.type == ImportType.RELATIVE:
            return __import__(import_info.module.lstrip('.'), fromlist=['*'])
        else:
            return __import__(import_info.module)
    
    def _add_to_namespace(self, import_info: ImportInfo, module: Any, namespace: Dict[str, Any]) -> None:
        """Add imported items to the namespace."""
        if import_info.type == ImportType.SIMPLE:
            namespace[import_info.module] = module
        elif import_info.type == ImportType.FROM:
            for name in import_info.names:
                if hasattr(module, name):
                    namespace[name] = getattr(module, name)
        elif import_info.type == ImportType.RELATIVE:
            namespace[import_info.module] = module
        elif import_info.type == ImportType.ALIAS:
            for orig_name, alias in import_info.aliases.items():
                if hasattr(module, orig_name):
                    namespace[alias] = getattr(module, orig_name)
        elif import_info.type == ImportType.STAR:
            for name in dir(module):
                if not name.startswith('_'):
                    namespace[name] = getattr(module, name)
    
    def _try_find_module_in_workspace(self, import_info: ImportInfo, namespace: Dict[str, Any]) -> None:
        """Try to find and import a module from the workspace."""
        try:
            module_name = import_info.module
            # Try to find the module file
            module_path = self.workspace_root / module_name.replace('.', '/')
            
            # Try as a Python file
            if module_path.with_suffix('.py').exists():
                self._load_module_from_file(module_name, module_path.with_suffix('.py'), namespace)
            # Try as a package
            elif module_path.is_dir() and (module_path / '__init__.py').exists():
                self._load_module_from_file(module_name, module_path / '__init__.py', namespace)
            else:
                logger.warning(f"Module {module_name} not found in workspace")
                
        except Exception as e:
            logger.warning(f"Failed to find module {import_info.module} in workspace: {str(e)}")
    
    def _load_module_from_file(self, module_name: str, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Load a module from a file."""
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                # Remove module from sys.modules if it exists to force reload
                if module_name in sys.modules:
                    del sys.modules[module_name]
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                namespace[module_name] = module
        except Exception as e:
            logger.error(f"Failed to load module {module_name} from {file_path}: {str(e)}")
    
    def cleanup(self) -> None:
        """Clean up any modifications made to the Python environment."""
        # Restore original sys.path
        sys.path.clear()
        sys.path.extend(self._original_sys_path)
        self._added_paths.clear()
        self._processed_files.clear()
        self._module_cache.clear()
        self._import_errors.clear()

class CodeRegionExtractor:
    """Extracts and analyzes code regions from files."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the code region extractor."""
        self.workspace_root = workspace_root or Path.cwd()
        self.dependency_resolver = DependencyResolver(self.workspace_root)
        logger.debug(f"Initialized CodeRegionExtractor with workspace root: {self.workspace_root}")
    
    def extract_region(self, file_path: Path, region_name: str) -> RegionInfo:
        """Extract a code region from a file."""
        logger.debug(f"Extracting region '{region_name}' from file: {file_path}")
        try:
            logger.debug(f"DEBUG: Opening file: {file_path}")
            with open(file_path, 'r') as f:
                content = f.read()
            logger.debug(f"DEBUG: Successfully read file: {file_path} ({len(content)} characters)")
            
            # If region_name is 'main', use the entire file
            if region_name == 'main':
                logger.debug("Using entire file as region (main)")
                code = content
                logger.debug(f"DEBUG: About to analyze region (main)")
                return self._analyze_region(code, region_name, file_path)
            
            # Otherwise look for region markers
            start_marker = f"# kaizen:start:{region_name}"
            end_marker = f"# kaizen:end:{region_name}"
            
            logger.debug(f"DEBUG: Looking for start marker: {start_marker}")
            start_idx = content.find(start_marker)
            if start_idx == -1:
                logger.error(f"Start marker not found: {start_marker}")
                raise ValueError(f"Start marker for region '{region_name}' not found")
            
            logger.debug(f"DEBUG: Looking for end marker: {end_marker}")
            end_idx = content.find(end_marker)
            if end_idx == -1:
                logger.error(f"End marker not found: {end_marker}")
                raise ValueError(f"End marker for region '{region_name}' not found")
            
            logger.debug(f"DEBUG: Found markers at positions {start_idx} and {end_idx}")
            
            # Extract imports from the entire file
            logger.debug(f"DEBUG: Extracting imports from file")
            import_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(('import ', 'from ')) and not line.startswith('#'):
                    # Skip relative imports since dependencies are handled by the dependency manager
                    if line.startswith('from .'):
                        logger.debug(f"Skipping relative import: {line}")
                        continue
                    import_lines.append(line)
            
            logger.debug(f"DEBUG: Found {len(import_lines)} import lines")
            
            # Extract the region code
            start_idx = content.find('\n', start_idx) + 1
            if start_idx == 0:  # find() returned -1, no newline found
                logger.error(f"No newline found after start marker: {start_marker}")
                raise ValueError(f"Invalid start marker format for region '{region_name}'")
            region_code = content[start_idx:end_idx].strip()
            
            # Combine imports with region code
            if import_lines:
                logger.debug(f"Including {len(import_lines)} import statements in region")
                code = '\n'.join(import_lines) + '\n\n' + region_code
            else:
                code = region_code
            
            logger.debug(f"Extracted code region: {len(code)} characters")
            logger.debug(f"DEBUG: About to analyze region: {region_name}")
            
            return self._analyze_region(code, region_name, file_path)
            
        except IOError as e:
            logger.error(f"IOError reading file {file_path}: {str(e)}")
            raise IOError(f"Failed to read file {file_path}: {str(e)}")
        except ValueError as e:
            logger.error(f"ValueError extracting region '{region_name}': {str(e)}")
            raise ValueError(f"Failed to extract region '{region_name}': {str(e)}")
        except SyntaxError as e:
            logger.error(f"SyntaxError in region '{region_name}': {str(e)}")
            raise SyntaxError(f"Invalid Python code in region '{region_name}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error extracting region '{region_name}': {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Unexpected error extracting region '{region_name}': {str(e)}")
    
    def _analyze_region(self, code: str, region_name: str, file_path: Path) -> RegionInfo:
        """Analyze the code region to determine its type, structure, and dependencies."""
        logger.debug(f"Analyzing region '{region_name}' from file: {file_path}")
        try:
            logger.debug("DEBUG: Parsing AST")
            tree = ast.parse(code)
            logger.debug("DEBUG: AST parsing completed")
            
            logger.debug("DEBUG: Extracting imports")
            imports = self._extract_imports(tree)
            logger.debug(f"DEBUG: Found {len(imports)} imports")
            
            logger.debug("DEBUG: Determining region type")
            region_type, name, methods = self._determine_region_type(tree)
            logger.debug(f"DEBUG: Region type: {region_type}, name: {name}, methods: {methods}")
            
            try:
                logger.debug("DEBUG: About to resolve dependencies")
                dependencies = self.dependency_resolver.resolve_dependencies(file_path)
                logger.debug(f"DEBUG: Found {len(dependencies)} dependencies")
            except ValueError as e:
                logger.error(f"Failed to resolve dependencies: {str(e)}")
                raise ValueError(f"Failed to resolve dependencies: {str(e)}")
            
            logger.debug("DEBUG: Creating RegionInfo object")
            region_info = RegionInfo(
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
            logger.debug(f"Successfully analyzed region '{region_name}'")
            logger.debug("DEBUG: _analyze_region completed successfully")
            return region_info
            
        except SyntaxError as e:
            logger.error(f"SyntaxError analyzing region '{region_name}': {str(e)}")
            raise SyntaxError(f"Invalid Python code in region '{region_name}': {str(e)}")
        except ValueError as e:
            logger.error(f"ValueError analyzing region '{region_name}': {str(e)}")
            raise ValueError(f"Failed to analyze region '{region_name}': {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error analyzing region '{region_name}': {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Unexpected error analyzing region '{region_name}': {str(e)}")
    
    def _extract_imports(self, tree: ast.AST) -> List[ImportInfo]:
        """Extract all imports from the AST."""
        logger.debug("Starting import extraction")
        try:
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            import_info = ImportInfo(
                                type=ImportType.SIMPLE,
                                module=name.name,
                                names=[name.name],
                                aliases={name.name: name.asname} if name.asname else {}
                            )
                            logger.debug(f"Found simple import: {import_info}")
                            imports.append(import_info)
                    else:  # ImportFrom
                        module = node.module or ''
                        names = []
                        aliases = {}
                        for name in node.names:
                            names.append(name.name)
                            if name.asname:
                                aliases[name.name] = name.asname
                        import_info = ImportInfo(
                            type=ImportType.FROM,
                            module=module,
                            names=names,
                            aliases=aliases,
                            level=node.level
                        )
                        logger.debug(f"Found from import: {import_info}")
                        imports.append(import_info)
            logger.debug(f"Extracted {len(imports)} imports")
            return imports
        except Exception as e:
            logger.error(f"Error extracting imports: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Failed to extract imports: {str(e)}")
    
    def _determine_region_type(self, tree: ast.AST) -> Tuple[RegionType, str, List[str]]:
        """Determine the type, name, and methods of the region."""
        logger.debug("Determining region type")
        try:
            methods = []
            classes = []
            
            # First pass: collect all classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    classes.append((node.name, class_methods))
                    logger.debug(f"Found class: {node.name} with methods: {class_methods}")
            
            # If we found classes, choose the best one
            if classes:
                # Prefer classes with methods over dataclasses/empty classes
                # Sort by number of methods (descending) and then by name
                classes.sort(key=lambda x: (len(x[1]), x[0]), reverse=True)
                best_class_name, best_class_methods = classes[0]
                
                logger.debug(f"Selected class '{best_class_name}' with {len(best_class_methods)} methods")
                return RegionType.CLASS, best_class_name, best_class_methods
            
            # Check for functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    logger.debug(f"Found function: {node.name}")
                    return RegionType.FUNCTION, node.name, []
            
            logger.debug("No class or function found, treating as module")
            return RegionType.MODULE, "module", []
            
        except Exception as e:
            logger.error(f"Error determining region type: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Failed to determine region type: {str(e)}")

    def extract_region_by_entry_point(self, file_path: Path, entry_point: AgentEntryPoint) -> RegionInfo:
        """Extract a code region using agent entry point configuration instead of markers.
        
        Args:
            file_path: Path to the file containing the agent
            entry_point: Agent entry point configuration
            
        Returns:
            RegionInfo object with the extracted region
            
        Raises:
            RegionExtractionError: If region extraction fails
            ImportError: If module/class/method cannot be imported
        """
        logger.debug(f"Extracting region using entry point: {entry_point}")
        try:
            # Read the entire file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract imports from the entire file
            import_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(('import ', 'from ')) and not line.startswith('#'):
                    if line.startswith('from .'):
                        logger.debug(f"Skipping relative import: {line}")
                        continue
                    import_lines.append(line)
            
            # Use the entire file content as the region
            code = content
            if import_lines:
                logger.debug(f"Found {len(import_lines)} import lines in file")
            
            # Analyze the region to determine type and structure
            region_info = self._analyze_region(code, entry_point.module, file_path)
            
            # Set the entry point configuration
            region_info.entry_point = entry_point
            
            logger.debug(f"Successfully extracted region using entry point: {entry_point}")
            return region_info
            
        except IOError as e:
            logger.error(f"IOError reading file {file_path}: {str(e)}")
            raise RegionExtractionError(f"Failed to read file {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error extracting region with entry point: {str(e)}")
            raise RegionExtractionError(f"Failed to extract region with entry point: {str(e)}")

    def validate_entry_point_ts(self, entry_point: AgentEntryPoint, file_path: Path) -> bool:
        """Validate that the specified TypeScript entry point exists and is callable.
        
        Args:
            entry_point: Agent entry point configuration
            file_path: Path to the TypeScript file containing the agent
            
        Returns:
            True if entry point is valid, False otherwise
        """
        try:
            # Read the TypeScript file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # For TypeScript, we'll do basic validation by checking if the file exists
            # and contains the expected patterns, rather than trying to import it
            if not file_path.exists():
                logger.error(f"TypeScript file does not exist: {file_path}")
                return False
            
            # Check if the file contains TypeScript content
            if not content.strip():
                logger.error(f"TypeScript file is empty: {file_path}")
                return False
            
            # For TypeScript agents, we're more lenient with validation
            # since the actual validation will happen during execution
            logger.debug(f"TypeScript entry point validation successful: {entry_point}")
            return True
            
        except IOError as e:
            logger.error(f"IOError reading TypeScript file {file_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating TypeScript entry point: {str(e)}")
            return False

    def validate_entry_point(self, entry_point: AgentEntryPoint, file_path: Path) -> bool:
        """Validate that the specified entry point exists and is callable.
        
        Args:
            entry_point: Agent entry point configuration
            file_path: Path to the file containing the agent
            
        Returns:
            True if entry point is valid, False otherwise
        """
        try:
            # Add the file's directory to Python path temporarily
            file_dir = str(file_path.parent)
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)
            
            try:
                # Import the module using importlib for better control
                module_name = entry_point.module
                if '.' in module_name:
                    # Handle nested modules
                    module_parts = module_name.split('.')
                    base_module = module_parts[0]
                    
                    # Try to import the base module
                    try:
                        module = importlib.import_module(base_module)
                    except builtins.ImportError:
                        logger.error(f"Base module '{base_module}' not found")
                        return False
                    
                    # Navigate to the nested module
                    for part in module_parts[1:]:
                        if hasattr(module, part):
                            module = getattr(module, part)
                        else:
                            logger.error(f"Module part '{part}' not found in {module}")
                            return False
                else:
                    # For simple module names, try to import directly
                    try:
                        module = importlib.import_module(module_name)
                    except builtins.ImportError:
                        # If direct import fails, try to load from file
                        if file_path.exists():
                            spec = importlib.util.spec_from_file_location(module_name, file_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                            else:
                                logger.error(f"Could not load module from file: {file_path}")
                                return False
                        else:
                            logger.error(f"Module '{module_name}' not found and file does not exist: {file_path}")
                            return False
                
                # If class is specified, check if it exists
                if entry_point.class_name:
                    if not hasattr(module, entry_point.class_name):
                        logger.error(f"Class '{entry_point.class_name}' not found in module '{module_name}'")
                        if entry_point.fallback_to_function:
                            logger.info(f"Falling back to function lookup for '{entry_point.class_name}'")
                            return hasattr(module, entry_point.class_name)
                        return False
                    
                    class_obj = getattr(module, entry_point.class_name)
                    
                    # If method is specified, check if it exists
                    if entry_point.method:
                        if not hasattr(class_obj, entry_point.method):
                            logger.error(f"Method '{entry_point.method}' not found in class '{entry_point.class_name}'")
                            return False
                        
                        method_obj = getattr(class_obj, entry_point.method)
                        if not callable(method_obj):
                            logger.error(f"'{entry_point.method}' is not callable in class '{entry_point.class_name}'")
                            return False
                
                # If no class specified but method is, check if it's a function in the module
                elif entry_point.method:
                    if not hasattr(module, entry_point.method):
                        logger.error(f"Function '{entry_point.method}' not found in module '{module_name}'")
                        return False
                    
                    func_obj = getattr(module, entry_point.method)
                    if not callable(func_obj):
                        logger.error(f"'{entry_point.method}' is not callable in module '{module_name}'")
                        return False
                
                logger.debug(f"Entry point validation successful: {entry_point}")
                return True
                
            finally:
                # Clean up: remove the added path
                if file_dir in sys.path:
                    sys.path.remove(file_dir)
                    
        except builtins.ImportError as e:
            logger.error(f"Import error validating entry point: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating entry point: {str(e)}")
            return False

    def extract_region_ts(self, file_path: Path, region_name: str) -> RegionInfo:
        """Extract a code region from a TypeScript file.
        
        Args:
            file_path: Path to the TypeScript file
            region_name: Name of the region to extract (optional)
            
        Returns:
            RegionInfo object with extracted code and metadata
        """
        logger.debug(f"Extracting TypeScript region '{region_name}' from file: {file_path}")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # If region_name is 'main', use the entire file
            if region_name == 'main':
                logger.debug("Using entire TypeScript file as region (main)")
                code = content
                return self._analyze_region_ts(code, region_name, file_path)
            
            # Look for region markers (same format as Python)
            start_marker = f"// kaizen:start:{region_name}"
            end_marker = f"// kaizen:end:{region_name}"
            
            logger.debug(f"Looking for TypeScript start marker: {start_marker}")
            start_idx = content.find(start_marker)
            if start_idx == -1:
                logger.error(f"TypeScript start marker not found: {start_marker}")
                raise ValueError(f"Start marker for region '{region_name}' not found")
            
            logger.debug(f"Looking for TypeScript end marker: {end_marker}")
            end_idx = content.find(end_marker)
            if end_idx == -1:
                logger.error(f"TypeScript end marker not found: {end_marker}")
                raise ValueError(f"End marker for region '{region_name}' not found")
            
            # Extract imports from the entire file
            import_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(('import ', 'export ')) and not line.startswith('//'):
                    import_lines.append(line)
            
            # Extract the region code
            start_idx = content.find('\n', start_idx) + 1
            if start_idx == 0:  # find() returned -1, no newline found
                logger.error(f"No newline found after start marker: {start_marker}")
                raise ValueError(f"Invalid start marker format for region '{region_name}'")
            region_code = content[start_idx:end_idx].strip()
            
            # Combine imports with region code
            if import_lines:
                code = '\n'.join(import_lines) + '\n\n' + region_code
            else:
                code = region_code
            
            logger.debug(f"Extracted TypeScript code region: {len(code)} characters")
            return self._analyze_region_ts(code, region_name, file_path)
            
        except IOError as e:
            logger.error(f"IOError reading TypeScript file {file_path}: {str(e)}")
            raise IOError(f"Failed to read TypeScript file {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error extracting TypeScript region '{region_name}': {str(e)}")
            raise ValueError(f"Unexpected error extracting TypeScript region '{region_name}': {str(e)}")

    def extract_region_by_entry_point_ts(self, file_path: Path, entry_point: AgentEntryPoint) -> RegionInfo:
        """Extract a TypeScript code region using agent entry point configuration.
        
        Args:
            file_path: Path to the TypeScript file containing the agent
            entry_point: Agent entry point configuration
            
        Returns:
            RegionInfo object with the extracted region
            
        Raises:
            RegionExtractionError: If region extraction fails
        """
        logger.debug(f"Extracting TypeScript region using entry point: {entry_point}")
        try:
            # Read the entire file content
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract imports from the entire file
            import_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(('import ', 'export ')) and not line.startswith('//'):
                    import_lines.append(line)
            
            # Use the entire file content as the region
            code = content
            if import_lines:
                logger.debug(f"Found {len(import_lines)} import lines in TypeScript file")
            
            # Analyze the region to determine type and structure
            region_info = self._analyze_region_ts(code, entry_point.module, file_path)
            
            # Set the entry point configuration
            region_info.entry_point = entry_point
            
            logger.debug(f"Successfully extracted TypeScript region using entry point: {entry_point}")
            return region_info
            
        except IOError as e:
            logger.error(f"IOError reading TypeScript file {file_path}: {str(e)}")
            raise RegionExtractionError(f"Failed to read TypeScript file {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error extracting TypeScript region with entry point: {str(e)}")
            raise RegionExtractionError(f"Failed to extract TypeScript region with entry point: {str(e)}")

    def extract_region_ts_by_name(self, file_path: Path, function_name: str) -> RegionInfo:
        """Extract a single named function from a TypeScript file.
        
        Args:
            file_path: Path to the TypeScript file
            function_name: Name of the function to extract
            
        Returns:
            RegionInfo object with the extracted function
        """
        logger.debug(f"Extracting TypeScript function '{function_name}' from file: {file_path}")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Simple regex to find function definitions
            import re
            
            # Pattern to match function declarations (including async, export, etc.)
            function_patterns = [
                rf'export\s+(?:async\s+)?function\s+{re.escape(function_name)}\s*\(',
                rf'(?:async\s+)?function\s+{re.escape(function_name)}\s*\(',
                rf'export\s+(?:async\s+)?const\s+{re.escape(function_name)}\s*=\s*(?:async\s+)?\(',
                rf'(?:async\s+)?const\s+{re.escape(function_name)}\s*=\s*(?:async\s+)?\(',
                rf'export\s+(?:async\s+)?const\s+{re.escape(function_name)}\s*=\s*(?:async\s+)?function\s*\(',
                rf'(?:async\s+)?const\s+{re.escape(function_name)}\s*=\s*(?:async\s+)?function\s*\(',
            ]
            
            function_code = None
            failed_patterns = []
            for pattern in function_patterns:
                match = re.search(pattern, content)
                if match:
                    start_pos = match.start()
                    # Find the end of the function by counting braces, skipping those in strings
                    brace_count = 0
                    in_function = False
                    end_pos = start_pos
                    in_string = False
                    string_char = None
                    in_comment = False
                    
                    for i, char in enumerate(content[start_pos:], start_pos):
                        # Handle string literals
                        if char in ['"', "'"] and not in_comment:
                            if not in_string:
                                in_string = True
                                string_char = char
                            elif string_char == char:
                                in_string = False
                                string_char = None
                        
                        # Handle comments (simplified - just skip // comments)
                        elif char == '/' and i + 1 < len(content) and content[i + 1] == '/' and not in_string:
                            in_comment = True
                        elif char == '\n' and in_comment:
                            in_comment = False
                        
                        # Only count braces when not in string or comment
                        elif not in_string and not in_comment:
                            if char == '{':
                                if not in_function:
                                    in_function = True
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if in_function and brace_count == 0:
                                    end_pos = i + 1
                                    break
                    
                    if end_pos > start_pos:
                        function_code = content[start_pos:end_pos]
                        break
                else:
                    failed_patterns.append(pattern)
            
            if not function_code:
                logger.error(f"Function '{function_name}' not found in TypeScript file")
                logger.debug(f"Failed patterns: {failed_patterns}")
                raise ValueError(f"Function '{function_name}' not found in TypeScript file")
            
            # Extract imports from the entire file
            import_lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(('import ', 'export ')) and not line.startswith('//'):
                    import_lines.append(line)
            
            # Combine imports with function code
            if import_lines:
                code = '\n'.join(import_lines) + '\n\n' + function_code
            else:
                code = function_code
            
            logger.debug(f"Extracted TypeScript function: {len(code)} characters")
            return self._analyze_region_ts(code, function_name, file_path)
            
        except IOError as e:
            logger.error(f"IOError reading TypeScript file {file_path}: {str(e)}")
            raise IOError(f"Failed to read TypeScript file {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error extracting TypeScript function '{function_name}': {str(e)}")
            raise ValueError(f"Unexpected error extracting TypeScript function '{function_name}': {str(e)}")

    def _analyze_region_ts(self, code: str, region_name: str, file_path: Path) -> RegionInfo:
        """Analyze the TypeScript code region to determine its type and structure.
        
        Args:
            code: The TypeScript code content
            region_name: Name of the region
            file_path: Path to the source file
            
        Returns:
            RegionInfo object with analyzed metadata
        """
        logger.debug(f"Analyzing TypeScript region '{region_name}' from file: {file_path}")
        try:
            # Extract imports from TypeScript code
            imports = self._extract_imports_ts(code)
            logger.debug(f"Found {len(imports)} TypeScript imports")
            
            # Determine region type and name
            region_type, name, methods = self._determine_region_type_ts(code)
            logger.debug(f"TypeScript region type: {region_type}, name: {name}, methods: {methods}")
            
            # For TypeScript, we'll use empty dependencies for now
            # In a full implementation, you might want to parse package.json and resolve dependencies
            dependencies = frozenset()
            
            # Create RegionInfo object
            region_info = RegionInfo(
                type=region_type,
                name=name or region_name,
                code=code,
                start_line=1,  # We don't have precise line info for TypeScript
                end_line=len(code.split('\n')),
                imports=imports,
                dependencies=dependencies,
                class_methods=methods,
                file_path=file_path
            )
            
            logger.debug(f"Successfully analyzed TypeScript region '{region_name}'")
            return region_info
            
        except Exception as e:
            logger.error(f"Unexpected error analyzing TypeScript region '{region_name}': {str(e)}")
            raise ValueError(f"Failed to analyze TypeScript region '{region_name}': {str(e)}")

    def _extract_imports_ts(self, code: str) -> List[ImportInfo]:
        """Extract import statements from TypeScript code.
        
        Args:
            code: TypeScript code content
            
        Returns:
            List of ImportInfo objects
        """
        imports = []
        import re
        
        # Pattern for TypeScript imports
        import_patterns = [
            # import { x, y } from 'module'
            r'import\s*\{([^}]+)\}\s*from\s*[\'"]([^\'"]+)[\'"]',
            # import x from 'module'
            r'import\s+(\w+)\s+from\s*[\'"]([^\'"]+)[\'"]',
            # import * as x from 'module'
            r'import\s*\*\s+as\s+(\w+)\s+from\s*[\'"]([^\'"]+)[\'"]',
            # import 'module'
            r'import\s*[\'"]([^\'"]+)[\'"]',
        ]
        
        # Skip import type statements and export statements
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('//') or line.startswith('/*'):
                continue
            
            # Skip import type statements
            if line.startswith('import type'):
                logger.debug(f"Skipping import type statement at line {line_num}: {line}")
                continue
            
            # Skip export statements (unless they're export import aliases)
            if line.startswith('export ') and not line.startswith('export import'):
                logger.debug(f"Skipping export statement at line {line_num}: {line}")
                continue
            
            # Check if line matches any import pattern
            matched = False
            for pattern in import_patterns:
                match = re.match(pattern, line)
                if match:
                    matched = True
                    try:
                        if len(match.groups()) >= 2:
                            # Named imports
                            names_str = match.group(1).strip()
                            module = match.group(2)
                            
                            if names_str:
                                names = [name.strip() for name in names_str.split(',')]
                                aliases = {}
                                for name in names:
                                    if ' as ' in name:
                                        original, alias = name.split(' as ')
                                        aliases[original.strip()] = alias.strip()
                                
                                import_info = ImportInfo(
                                    type=ImportType.FROM,
                                    module=module,
                                    names=names,
                                    aliases=aliases
                                )
                                imports.append(import_info)
                                logger.debug(f"Found import at line {line_num}: {import_info}")
                        elif len(match.groups()) == 1:
                            # Default import or module-only import
                            if match.group(1) and not match.group(1).startswith('.'):
                                # Default import
                                import_info = ImportInfo(
                                    type=ImportType.SIMPLE,
                                    module=match.group(1),
                                    names=[match.group(1)],
                                    aliases={}
                                )
                                imports.append(import_info)
                                logger.debug(f"Found import at line {line_num}: {import_info}")
                    except Exception as e:
                        logger.debug(f"Failed to parse import at line {line_num}: {line} - {str(e)}")
                    break
            
            if not matched and (line.startswith('import ') or line.startswith('export import')):
                logger.debug(f"Malformed import/export line at line {line_num}: {line}")
        
        return imports

    def _determine_region_type_ts(self, code: str) -> Tuple[RegionType, str, List[str]]:
        """Determine the type, name, and methods of a TypeScript region.
        
        Args:
            code: TypeScript code content
            
        Returns:
            Tuple of (region_type, name, methods)
        """
        import re
        
        methods = []
        classes = []
        
        # Pattern for class definitions
        class_pattern = r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)'
        class_matches = re.finditer(class_pattern, code)
        
        for match in class_matches:
            class_name = match.group(1)
            # Find methods in this class (simplified)
            class_start = match.start()
            # Look for method definitions after class start
            method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:{]\s*'
            class_methods = []
            
            # This is a simplified approach - in a full implementation you'd parse the AST
            for method_match in re.finditer(method_pattern, code[class_start:]):
                method_name = method_match.group(1)
                if method_name not in ['constructor', 'get', 'set']:
                    class_methods.append(method_name)
            
            classes.append((class_name, class_methods))
        
        # Check for function definitions FIRST (prioritize functions)
        function_patterns = [
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
            r'(?:export\s+)?(?:async\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(',
            r'(?:export\s+)?(?:async\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(',
        ]
        
        for pattern in function_patterns:
            match = re.search(pattern, code)
            if match:
                function_name = match.group(1)
                return RegionType.FUNCTION, function_name, []
        
        # If we found classes, choose the best one
        if classes:
            # Prefer classes with methods
            classes.sort(key=lambda x: (len(x[1]), x[0]), reverse=True)
            best_class_name, best_class_methods = classes[0]
            return RegionType.CLASS, best_class_name, best_class_methods
        
        # Check for modern agent patterns (like Mastra agents)
        agent_patterns = [
            # export const emailFixAgent = new Agent({...})
            r'export\s+const\s+(\w+)\s*=\s*new\s+Agent\s*\(',
            # const emailFixAgent = new Agent({...})
            r'const\s+(\w+)\s*=\s*new\s+Agent\s*\(',
            # export const agent = new SomeAgent({...})
            r'export\s+const\s+(\w+)\s*=\s*new\s+\w+Agent\s*\(',
            # const agent = new SomeAgent({...})
            r'const\s+(\w+)\s*=\s*new\s+\w+Agent\s*\(',
        ]
        
        for pattern in agent_patterns:
            match = re.search(pattern, code)
            if match:
                agent_name = match.group(1)
                # For agents, we'll treat them as modules since they're typically instantiated objects
                return RegionType.MODULE, agent_name, []
        
        # Check for default exports
        default_export_patterns = [
            r'export\s+default\s+(\w+)',
            r'export\s+default\s+function\s+(\w+)',
            r'export\s+default\s+class\s+(\w+)',
        ]
        
        for pattern in default_export_patterns:
            match = re.search(pattern, code)
            if match:
                export_name = match.group(1)
                return RegionType.MODULE, export_name, []
        
        # Default to module
        return RegionType.MODULE, "module", []

class CodeRegionExecutor:
    """Executes code regions with variable tracking and import management."""
    
    def __init__(self, workspace_root: Path, imported_dependencies: Optional[Dict[str, Any]] = None):
        """Initialize the code region executor.
        
        Args:
            workspace_root: Root directory of the workspace
            imported_dependencies: Optional pre-imported dependencies
        """
        self.workspace_root = workspace_root
        self.imported_dependencies = imported_dependencies or {}
        self._execution_cache: Dict[str, Any] = {}
        self._compiled_modules: Dict[str, str] = {}
        self._ts_node_cache_dir: Optional[Path] = None
        self._setup_ts_node_cache()
        
        # Initialize import manager
        self.import_manager = ImportManager(workspace_root)
    
    def _setup_ts_node_cache(self):
        """Set up TypeScript compilation cache for faster loading."""
        try:
            # Create a cache directory for ts-node
            cache_dir = Path.home() / '.kaizen' / 'ts-cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._ts_node_cache_dir = cache_dir
            
            # Set environment variables for ts-node optimization
            os.environ['TS_NODE_CACHE_DIRECTORY'] = str(cache_dir)
            os.environ['TS_NODE_CACHE'] = 'true'
            os.environ['TS_NODE_COMPILER_OPTIONS'] = '{"module": "commonjs", "target": "es2020", "esModuleInterop": true}'
            
            logger.debug(f"TypeScript cache directory set to: {cache_dir}")
        except Exception as e:
            logger.warning(f"Failed to setup TypeScript cache: {str(e)}")
    
    def _get_cache_key(self, region_info: RegionInfo, method_name: Optional[str], input_data: List[Any]) -> str:
        """Generate a cache key for the execution."""
        import hashlib
        
        # Create a hash of the code, method, and input
        content = f"{region_info.code}:{method_name}:{str(input_data)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_mastra_agent(self, region_info: RegionInfo) -> bool:
        """Detect if the code contains Mastra agent patterns."""
        code = region_info.code.lower()
        mastra_patterns = [
            '@mastra/core/agent',
            'new agent(',
            '@ai-sdk/google',
            'google(',
            'gemini-',
            'openai(',
            'anthropic('
        ]
        return any(pattern in code for pattern in mastra_patterns)
    


    def execute_region_with_tracking(
        self, 
        region_info: RegionInfo, 
        method_name: Optional[str] = None,
        input_data: Optional[List[Any]] = None,
        tracked_variables: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """Execute a code region with variable tracking.
        
        Args:
            region_info: Information about the code region to execute
            method_name: Optional method name to call (for class regions)
            input_data: Optional input data to pass to the method
            tracked_variables: Optional set of variable names to track
            
        Returns:
            Dictionary containing execution result and tracked values
        """
        tracked_variables = tracked_variables or set()
        input_data = input_data or []
        
        try:
            # If entry point is specified, use it for execution
            if region_info.entry_point:
                return self._execute_with_entry_point(
                    region_info, input_data, tracked_variables
                )
            
            # Otherwise use the traditional region-based execution
            with self.import_manager.managed_imports(region_info) as namespace:
                # Add imported dependencies to namespace
                namespace.update(self.imported_dependencies)
                
                # Execute the code region
                if region_info.type == RegionType.CLASS:
                    return self._execute_class_region(
                        region_info, method_name, input_data, tracked_variables, namespace
                    )
                elif region_info.type == RegionType.FUNCTION:
                    return self._execute_function_region(
                        region_info, input_data, tracked_variables, namespace
                    )
                elif region_info.type == RegionType.MODULE:
                    return self._execute_module_region(
                        region_info, tracked_variables, namespace
                    )
                else:
                    raise ValueError(f"Unsupported region type: {region_info.type}")
                    
        except Exception as e:
            logger.error(f"Error executing region {region_info.name}: {str(e)}")
            return {
                'result': None,
                'tracked_values': {},
                'tracked_variables': tracked_variables,
                'error': str(e),
                'error_details': traceback.format_exc()
            }

    def _execute_with_entry_point(
        self,
        region_info: RegionInfo,
        input_data: List[Any],
        tracked_variables: Set[str]
    ) -> Dict[str, Any]:
        """Execute code using agent entry point configuration.
        
        Args:
            region_info: Region info with entry point configuration
            input_data: Input data to pass to the method/function
            tracked_variables: Variables to track during execution
            
        Returns:
            Dictionary containing execution result and tracked values
        """
        entry_point = region_info.entry_point
        if not entry_point:
            raise ValueError("No entry point specified in region info")
        
        try:
            # Add the file's directory to Python path temporarily
            file_dir = str(region_info.file_path.parent) if region_info.file_path else str(self.workspace_root)
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)
            
            try:
                # Import the module using importlib for better control
                module_name = entry_point.module
                if '.' in module_name:
                    # Handle nested modules
                    module_parts = module_name.split('.')
                    base_module = module_parts[0]
                    
                    # Try to import the base module
                    try:
                        module = importlib.import_module(base_module)
                    except builtins.ImportError:
                        logger.error(f"Base module '{base_module}' not found")
                        raise
                    
                    # Navigate to the nested module
                    for part in module_parts[1:]:
                        if hasattr(module, part):
                            module = getattr(module, part)
                        else:
                            logger.error(f"Module part '{part}' not found in {module}")
                            raise AttributeError(f"Module part '{part}' not found")
                else:
                    # For simple module names, try to import directly
                    try:
                        module = importlib.import_module(module_name)
                    except builtins.ImportError:
                        # If direct import fails, try to load from file
                        if region_info.file_path and region_info.file_path.exists():
                            spec = importlib.util.spec_from_file_location(module_name, region_info.file_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                            else:
                                logger.error(f"Could not load module from file: {region_info.file_path}")
                                raise
                        else:
                            logger.error(f"Module '{module_name}' not found and file does not exist: {region_info.file_path}")
                            raise
                
                # Execute with variable tracking
                with track_variables(tracked_variables) as tracker:
                    result = None
                    
                    # If class is specified, instantiate and call method
                    if entry_point.class_name:
                        if not hasattr(module, entry_point.class_name):
                            if entry_point.fallback_to_function:
                                # Fallback to function if class not found
                                if hasattr(module, entry_point.class_name):
                                    func = getattr(module, entry_point.class_name)
                                    if callable(func):
                                        if len(input_data) == 1:
                                            result = func(input_data[0])
                                        else:
                                            result = func(*input_data)
                                else:
                                    raise AttributeError(f"Neither class nor function '{entry_point.class_name}' found in module '{module_name}'")
                            else:
                                raise AttributeError(f"Class '{entry_point.class_name}' not found in module '{module_name}'")
                        else:
                            class_obj = getattr(module, entry_point.class_name)
                            instance = class_obj()
                            
                            # If method is specified, call it
                            if entry_point.method:
                                if not hasattr(instance, entry_point.method):
                                    raise AttributeError(f"Method '{entry_point.method}' not found in class '{entry_point.class_name}'")
                                
                                method = getattr(instance, entry_point.method)
                                if len(input_data) == 1:
                                    result = method(input_data[0])
                                else:
                                    result = method(*input_data)
                            else:
                                # If no method specified, try to call the instance directly
                                if callable(instance):
                                    if len(input_data) == 1:
                                        result = instance(input_data[0])
                                    else:
                                        result = instance(*input_data)
                                else:
                                    raise ValueError(f"Instance of '{entry_point.class_name}' is not callable and no method specified")
                    
                    # If no class specified but method is, call it as a function
                    elif entry_point.method:
                        if not hasattr(module, entry_point.method):
                            raise AttributeError(f"Function '{entry_point.method}' not found in module '{module_name}'")
                        
                        func = getattr(module, entry_point.method)
                        if not callable(func):
                            raise ValueError(f"'{entry_point.method}' is not callable in module '{module_name}'")
                        
                        if len(input_data) == 1:
                            result = func(input_data[0])
                        else:
                            result = func(*input_data)
                    
                    # If neither class nor method specified, raise error
                    else:
                        raise ValueError("Either class_name or method must be specified in entry point")
                    
                    # Get tracked values
                    tracked_values = {}
                    for var_name in tracked_variables:
                        value = tracker.get_variable_value(var_name)
                        if value is not None:
                            tracked_values[var_name] = value
                    
                    return {
                        'result': result,
                        'tracked_values': tracked_values,
                        'tracked_variables': tracked_variables
                    }
                    
            finally:
                # Clean up: remove the added path
                if file_dir in sys.path:
                    sys.path.remove(file_dir)
                    
        except Exception as e:
            logger.error(f"Error executing with entry point {entry_point}: {str(e)}")
            raise

    def _execute_class_region(
        self, 
        region_info: RegionInfo, 
        method_name: str,
        input_data: List[Any],
        tracked_variables: Set[str],
        namespace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a class region by calling a specific method."""
        # Execute the class definition
        exec(region_info.code, namespace)
        
        # Get the class from namespace
        class_obj = namespace.get(region_info.name)
        if not class_obj:
            raise ValueError(f"Class '{region_info.name}' not found in namespace")
        
        # Create instance
        instance = class_obj()
        
        # Get the method
        method = getattr(instance, method_name, None)
        if not method:
            raise ValueError(f"Method '{method_name}' not found in class '{region_info.name}'")
        
        # Execute with variable tracking
        with track_variables(tracked_variables) as tracker:
            # Call the method with input data
            if len(input_data) == 1:
                result = method(input_data[0])
            else:
                result = method(*input_data)
            
            # Get tracked values
            tracked_values = {}
            for var_name in tracked_variables:
                value = tracker.get_variable_value(var_name)
                if value is not None:
                    tracked_values[var_name] = value
            
            return {
                'result': result,
                'tracked_values': tracked_values,
                'tracked_variables': tracked_variables
            }
    
    def _execute_function_region(
        self, 
        region_info: RegionInfo,
        input_data: List[Any],
        tracked_variables: Set[str],
        namespace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a function region."""
        # Execute the function definition
        exec(region_info.code, namespace)
        
        # Get the function from namespace
        func = namespace.get(region_info.name)
        if not func:
            raise ValueError(f"Function '{region_info.name}' not found in namespace")
        
        # Execute with variable tracking
        with track_variables(tracked_variables) as tracker:
            # Call the function with input data
            if len(input_data) == 1:
                result = func(input_data[0])
            else:
                result = func(*input_data)
            
            # Get tracked values
            tracked_values = {}
            for var_name in tracked_variables:
                value = tracker.get_variable_value(var_name)
                if value is not None:
                    tracked_values[var_name] = value
            
            return {
                'result': result,
                'tracked_values': tracked_values,
                'tracked_variables': tracked_variables
            }
    
    def _execute_module_region(
        self, 
        region_info: RegionInfo,
        tracked_variables: Set[str],
        namespace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a module region."""
        # Execute the module code
        exec(region_info.code, namespace)
        
        # For module regions, we don't have a specific return value
        # but we can track variables that were assigned
        with track_variables(tracked_variables) as tracker:
            # Get tracked values
            tracked_values = {}
            for var_name in tracked_variables:
                value = tracker.get_variable_value(var_name)
                if value is not None:
                    tracked_values[var_name] = value
            
            return {
                'result': None,  # Module execution doesn't return a specific value
                'tracked_values': tracked_values,
                'tracked_variables': tracked_variables
            }

    def execute_typescript_region_with_tracking(
        self, 
        region_info: RegionInfo, 
        method_name: Optional[str] = None,
        input_data: Optional[List[Any]] = None,
        tracked_variables: Optional[Set[str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a TypeScript code region with variable tracking and optimizations.
        
        Args:
            region_info: Information about the TypeScript code region to execute
            method_name: Optional method name to call (for class regions)
            input_data: Optional input data to pass to the method
            tracked_variables: Optional set of variable names to track
            timeout: Optional timeout for the TypeScript execution
            
        Returns:
            Dictionary containing execution result and tracked values
        """
        import time
        start_time = time.time()
        
        tracked_variables = tracked_variables or set()
        input_data = input_data or []
        
        logger.info(f"🚀 Starting TypeScript execution for region: {region_info.name}")
        logger.info(f"   Method: {method_name or 'auto-detect'}")
        logger.info(f"   Input data: {input_data}")
        logger.info(f"   Code length: {len(region_info.code)} characters")
        
        # Check cache first
        cache_key = self._get_cache_key(region_info, method_name, input_data)
        if cache_key in self._execution_cache:
            logger.info(f"✅ Using cached result for TypeScript execution: {region_info.name}")
            return self._execution_cache[cache_key]
        
        # Detect if this is a Mastra agent for optimizations
        is_mastra = self._is_mastra_agent(region_info)
        if is_mastra:
            logger.info(f"🤖 Detected Mastra agent, applying optimizations: {region_info.name}")
        else:
            logger.info(f"📝 Regular TypeScript code detected: {region_info.name}")
        
        # Execute with Mastra-specific strategy
        try:
            logger.info(f"🤖 Using Mastra-specific execution strategy...")
            strategy_start = time.time()
            
            result = self._execute_with_mastra_specific_handling(
                region_info, method_name, input_data, tracked_variables, timeout, is_mastra
            )
            
            strategy_time = time.time() - strategy_start
            logger.info(f"✅ Mastra-specific execution succeeded (took {strategy_time:.2f}s)")
            
            # Cache successful results
            self._execution_cache[cache_key] = result
            return result
            
        except subprocess.TimeoutExpired as e:
            strategy_time = time.time() - strategy_start
            logger.error(f"⏰ Mastra-specific execution timed out (took {strategy_time:.2f}s)")
            raise e
        except Exception as e:
            strategy_time = time.time() - strategy_start
            logger.error(f"❌ Mastra-specific execution failed (took {strategy_time:.2f}s): {str(e)}")
            raise e

    def _execute_with_entry_point(
        self,
        region_info: RegionInfo,
        input_data: List[Any],
        tracked_variables: Set[str]
    ) -> Dict[str, Any]:
        """Execute code using agent entry point configuration.
        
        Args:
            region_info: Region info with entry point configuration
            input_data: Input data to pass to the method/function
            tracked_variables: Variables to track during execution
            
        Returns:
            Dictionary containing execution result and tracked values
        """
        entry_point = region_info.entry_point
        if not entry_point:
            raise ValueError("No entry point specified in region info")
        
        try:
            # Add the file's directory to Python path temporarily
            file_dir = str(region_info.file_path.parent) if region_info.file_path else str(self.workspace_root)
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)
            
            try:
                # Import the module using importlib for better control
                module_name = entry_point.module
                if '.' in module_name:
                    # Handle nested modules
                    module_parts = module_name.split('.')
                    base_module = module_parts[0]
                    
                    # Try to import the base module
                    try:
                        module = importlib.import_module(base_module)
                    except builtins.ImportError:
                        logger.error(f"Base module '{base_module}' not found")
                        raise
                    
                    # Navigate to the nested module
                    for part in module_parts[1:]:
                        if hasattr(module, part):
                            module = getattr(module, part)
                        else:
                            logger.error(f"Module part '{part}' not found in {module}")
                            raise AttributeError(f"Module part '{part}' not found")
                else:
                    # For simple module names, try to import directly
                    try:
                        module = importlib.import_module(module_name)
                    except builtins.ImportError:
                        # If direct import fails, try to load from file
                        if region_info.file_path and region_info.file_path.exists():
                            spec = importlib.util.spec_from_file_location(module_name, region_info.file_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                            else:
                                logger.error(f"Could not load module from file: {region_info.file_path}")
                                raise
                        else:
                            logger.error(f"Module '{module_name}' not found and file does not exist: {region_info.file_path}")
                            raise
                
                # Execute with variable tracking
                with track_variables(tracked_variables) as tracker:
                    result = None
                    
                    # If class is specified, instantiate and call method
                    if entry_point.class_name:
                        if not hasattr(module, entry_point.class_name):
                            if entry_point.fallback_to_function:
                                # Fallback to function if class not found
                                if hasattr(module, entry_point.class_name):
                                    func = getattr(module, entry_point.class_name)
                                    if callable(func):
                                        if len(input_data) == 1:
                                            result = func(input_data[0])
                                        else:
                                            result = func(*input_data)
                                else:
                                    raise AttributeError(f"Neither class nor function '{entry_point.class_name}' found in module '{module_name}'")
                            else:
                                raise AttributeError(f"Class '{entry_point.class_name}' not found in module '{module_name}'")
                        else:
                            class_obj = getattr(module, entry_point.class_name)
                            instance = class_obj()
                            
                            # If method is specified, call it
                            if entry_point.method:
                                if not hasattr(instance, entry_point.method):
                                    raise AttributeError(f"Method '{entry_point.method}' not found in class '{entry_point.class_name}'")
                                
                                method = getattr(instance, entry_point.method)
                                if len(input_data) == 1:
                                    result = method(input_data[0])
                                else:
                                    result = method(*input_data)
                            else:
                                # If no method specified, try to call the instance directly
                                if callable(instance):
                                    if len(input_data) == 1:
                                        result = instance(input_data[0])
                                    else:
                                        result = instance(*input_data)
                                else:
                                    raise ValueError(f"Instance of '{entry_point.class_name}' is not callable and no method specified")
                    
                    # If no class specified but method is, call it as a function
                    elif entry_point.method:
                        if not hasattr(module, entry_point.method):
                            raise AttributeError(f"Function '{entry_point.method}' not found in module '{module_name}'")
                        
                        func = getattr(module, entry_point.method)
                        if not callable(func):
                            raise ValueError(f"'{entry_point.method}' is not callable in module '{module_name}'")
                        
                        if len(input_data) == 1:
                            result = func(input_data[0])
                        else:
                            result = func(*input_data)
                    
                    # If neither class nor method specified, raise error
                    else:
                        raise ValueError("Either class_name or method must be specified in entry point")
                    
                    # Get tracked values
                    tracked_values = {}
                    for var_name in tracked_variables:
                        value = tracker.get_variable_value(var_name)
                        if value is not None:
                            tracked_values[var_name] = value
                    
                    return {
                        'result': result,
                        'tracked_values': tracked_values,
                        'tracked_variables': tracked_variables
                    }
                    
            finally:
                # Clean up: remove the added path
                if file_dir in sys.path:
                    sys.path.remove(file_dir)
                    
        except Exception as e:
            logger.error(f"Error executing with entry point {entry_point}: {str(e)}")
            raise

    def _execute_class_region(
        self, 
        region_info: RegionInfo, 
        method_name: str,
        input_data: List[Any],
        tracked_variables: Set[str],
        namespace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a class region by calling a specific method."""
        # Execute the class definition
        exec(region_info.code, namespace)
        
        # Get the class from namespace
        class_obj = namespace.get(region_info.name)
        if not class_obj:
            raise ValueError(f"Class '{region_info.name}' not found in namespace")
        
        # Create instance
        instance = class_obj()
        
        # Get the method
        method = getattr(instance, method_name, None)
        if not method:
            raise ValueError(f"Method '{method_name}' not found in class '{region_info.name}'")
        
        # Execute with variable tracking
        with track_variables(tracked_variables) as tracker:
            # Call the method with input data
            if len(input_data) == 1:
                result = method(input_data[0])
            else:
                result = method(*input_data)
            
            # Get tracked values
            tracked_values = {}
            for var_name in tracked_variables:
                value = tracker.get_variable_value(var_name)
                if value is not None:
                    tracked_values[var_name] = value
            
            return {
                'result': result,
                'tracked_values': tracked_values,
                'tracked_variables': tracked_variables
            }
    
    def _execute_function_region(
        self, 
        region_info: RegionInfo,
        input_data: List[Any],
        tracked_variables: Set[str],
        namespace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a function region."""
        # Execute the function definition
        exec(region_info.code, namespace)
        
        # Get the function from namespace
        func = namespace.get(region_info.name)
        if not func:
            raise ValueError(f"Function '{region_info.name}' not found in namespace")
        
        # Execute with variable tracking
        with track_variables(tracked_variables) as tracker:
            # Call the function with input data
            if len(input_data) == 1:
                result = func(input_data[0])
            else:
                result = func(*input_data)
            
            # Get tracked values
            tracked_values = {}
            for var_name in tracked_variables:
                value = tracker.get_variable_value(var_name)
                if value is not None:
                    tracked_values[var_name] = value
            
            return {
                'result': result,
                'tracked_values': tracked_values,
                'tracked_variables': tracked_variables
            }
    
    def _execute_module_region(
        self, 
        region_info: RegionInfo,
        tracked_variables: Set[str],
        namespace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a module region."""
        # Execute the module code
        exec(region_info.code, namespace)
        
        # For module regions, we don't have a specific return value
        # but we can track variables that were assigned
        with track_variables(tracked_variables) as tracker:
            # Get tracked values
            tracked_values = {}
            for var_name in tracked_variables:
                value = tracker.get_variable_value(var_name)
                if value is not None:
                    tracked_values[var_name] = value
            
            return {
                'result': None,  # Module execution doesn't return a specific value
                'tracked_values': tracked_values,
                'tracked_variables': tracked_variables
            }

    def _check_required_imports(self) -> None:
        """Check if all required imports were successful."""
        failed_required = [
            error for error in self._import_errors
            if error.module_name in self.config.common_packages
            and self.config.common_packages[error.module_name].required
        ]
        
        if failed_required:
            error_messages = [f"{error.module_name}: {error.message}" for error in failed_required]
            raise builtins.ImportError(
                f"Failed to import required packages:\n" + "\n".join(error_messages)
            )
    
    def _add_typing_imports(self, namespace: Dict[str, Any]) -> None:
        """Add all common typing imports to namespace."""
        # Common typing imports that are frequently used
        typing_imports = {
            'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet', 
            'Union', 'Any', 'Callable', 'TypeVar', 'Generic', 'Type',
            'Protocol', 'runtime_checkable', 'overload', 'final',
            'Literal', 'TypedDict', 'cast', 'get_type_hints',
            'Sequence', 'Mapping', 'Iterable', 'Iterator', 'AsyncIterator',
            'Awaitable', 'Coroutine', 'AsyncGenerator', 'AsyncIterable'
        }
        
        # Add each typing import to the namespace
        for name in typing_imports:
            try:
                namespace[name] = getattr(typing, name)
            except builtins.AttributeError:
                logger.warning(f"Type {name} not found in typing module")
        
        # Also add typing module itself
        namespace['typing'] = typing
    
    def _setup_import_environment(self, region_info: RegionInfo) -> None:
        """Set up the import environment for execution."""
        if region_info.file_path:
            self._add_to_python_path(region_info.file_path.parent)
    
    def _add_to_python_path(self, directory: Path) -> None:
        """Add directory to Python path if not already present."""
        dir_str = str(directory)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)
            self._added_paths.add(dir_str)
    
    def _process_dependencies(self, region_info: RegionInfo, namespace: Dict[str, Any]) -> None:
        """Process all dependencies recursively."""
        if region_info.file_path in self._processed_files:
            return
        
        self._processed_files.add(region_info.file_path)
        
        # Process dependencies
        for dep in region_info.dependencies:
            if not dep.is_third_party:
                self._add_to_python_path(dep.path.parent)
                if dep.path not in self._processed_files:
                    self._process_file_dependencies(dep.path, namespace)
        
        # Process imports
        for import_info in region_info.imports:
            self._execute_import(import_info, namespace)
    
    def _is_system_module(self, file_path: Path) -> bool:
        """Check if the file path represents a system or built-in module.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if the path represents a system module
        """
        return (str(file_path).startswith('<built-in module') or 
                str(file_path).startswith('/') or
                not file_path.exists())

    def _process_imports(self, imports: Set[str], namespace: Dict[str, Any], is_standard: bool) -> None:
        """Process a set of imports and add them to the namespace.
        
        Args:
            imports: Set of import names to process
            namespace: Dictionary to add imports to
            is_standard: Whether these are standard library imports
        """
        for module_name in imports:
            if module_name not in namespace:
                try:
                    module = __import__(module_name)
                    namespace[module_name] = module
                    if is_standard and module_name == 'typing':
                        self._add_typing_imports(namespace)
                except builtins.ImportError as e:
                    logger.warning(f"Failed to import {module_name}: {str(e)}")

    def _process_file_dependencies(self, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Process dependencies of a single file.
        
        Args:
            file_path: Path to the file to process
            namespace: Dictionary to add imports to
            
        Raises:
            IOError: If the file cannot be read
            SyntaxError: If the file contains invalid Python code
        """
        try:
            # Skip system and built-in modules
            if self._is_system_module(file_path):
                logger.debug(f"Skipping system module: {file_path}")
                return

            # Read and parse file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except IOError as e:
                logger.error(f"Failed to read file {file_path}: {str(e)}")
                raise

            # Analyze imports
            try:
                standard_imports, third_party_imports = self._import_analyzer.analyze_imports(content)
            except SyntaxError as e:
                logger.error(f"Invalid Python code in {file_path}: {str(e)}")
                raise

            # Process imports
            self._process_imports(standard_imports, namespace, is_standard=True)
            self._process_imports(third_party_imports, namespace, is_standard=False)

        except (IOError, SyntaxError) as e:
            # Re-raise specific exceptions
            raise
        except Exception as e:
            # Log unexpected errors but don't break execution
            logger.error(f"Unexpected error processing {file_path}: {str(e)}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def _execute_import(self, import_info: ImportInfo, namespace: Dict[str, Any]) -> None:
        """Execute a single import statement in the namespace."""
        try:
            if import_info.module in self._module_cache:
                module = self._module_cache[import_info.module]
            else:
                module = self._load_module(import_info)
                self._module_cache[import_info.module] = module
            
            # Special handling for typing imports
            if import_info.module == 'typing':
                self._handle_typing_import(import_info, module, namespace)
            else:
                self._add_to_namespace(import_info, module, namespace)
            
        except builtins.ImportError as e:
            logger.warning(f"Failed to import {import_info}: {str(e)}")
            self._try_find_module_in_workspace(import_info, namespace)
    
    def _handle_typing_import(self, import_info: ImportInfo, module: Any, namespace: Dict[str, Any]) -> None:
        """Handle typing imports specially to ensure all types are available."""
        if import_info.type == ImportType.FROM:
            for name in import_info.names:
                if name == '*':
                    # Add all common typing types
                    typing_imports = {
                        'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet', 
                        'Union', 'Any', 'Callable', 'TypeVar', 'Generic', 'Type',
                        'Protocol', 'runtime_checkable', 'overload', 'final',
                        'Literal', 'TypedDict', 'cast', 'get_type_hints'
                    }
                    for type_name in typing_imports:
                        try:
                            namespace[type_name] = getattr(module, type_name)
                        except builtins.AttributeError:
                            logger.warning(f"Type {type_name} not found in typing module")
                else:
                    try:
                        namespace[name] = getattr(module, name)
                    except builtins.AttributeError:
                        logger.warning(f"Type {name} not found in typing module")
        else:
            namespace['typing'] = module
    
    def _load_module(self, import_info: ImportInfo) -> Any:
        """Load a module using Python's import system."""
        if import_info.type == ImportType.SIMPLE:
            return __import__(import_info.module)
        elif import_info.type in (ImportType.FROM, ImportType.STAR):
            return __import__(import_info.module, fromlist=['*'])
        elif import_info.type == ImportType.RELATIVE:
            return __import__(import_info.module.lstrip('.'), fromlist=['*'])
        else:
            return __import__(import_info.module)
    
    def _add_to_namespace(self, import_info: ImportInfo, module: Any, namespace: Dict[str, Any]) -> None:
        """Add imported items to the namespace."""
        if import_info.type == ImportType.SIMPLE:
            namespace[import_info.module] = module
        elif import_info.type == ImportType.FROM:
            for name in import_info.names:
                if hasattr(module, name):
                    namespace[name] = getattr(module, name)
        elif import_info.type == ImportType.RELATIVE:
            namespace[import_info.module] = module
        elif import_info.type == ImportType.ALIAS:
            for orig_name, alias in import_info.aliases.items():
                if hasattr(module, orig_name):
                    namespace[alias] = getattr(module, orig_name)
        elif import_info.type == ImportType.STAR:
            for name in dir(module):
                if not name.startswith('_'):
                    namespace[name] = getattr(module, name)
    
    def _try_find_module_in_workspace(self, import_info: ImportInfo, namespace: Dict[str, Any]) -> None:
        """Try to find and import a module from the workspace."""
        try:
            module_name = import_info.module
            # Try to find the module file
            module_path = self.workspace_root / module_name.replace('.', '/')
            
            # Try as a Python file
            if module_path.with_suffix('.py').exists():
                self._load_module_from_file(module_name, module_path.with_suffix('.py'), namespace)
            # Try as a package
            elif module_path.is_dir() and (module_path / '__init__.py').exists():
                self._load_module_from_file(module_name, module_path / '__init__.py', namespace)
            else:
                logger.warning(f"Module {module_name} not found in workspace")
                
        except Exception as e:
            logger.warning(f"Failed to find module {import_info.module} in workspace: {str(e)}")
    
    def _load_module_from_file(self, module_name: str, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Load a module from a file."""
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                # Remove module from sys.modules if it exists to force reload
                if module_name in sys.modules:
                    del sys.modules[module_name]
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                namespace[module_name] = module
        except Exception as e:
            logger.error(f"Failed to load module {module_name} from {file_path}: {str(e)}")
    
    def cleanup(self) -> None:
        """Clean up any modifications made to the Python environment."""
        # Restore original sys.path
        sys.path.clear()
        sys.path.extend(self._original_sys_path)
        self._added_paths.clear()
        self._processed_files.clear()
        self._module_cache.clear()
        self._import_errors.clear()

    def clear_cache(self):
        """Clear the execution cache."""
        self._execution_cache.clear()
        self._compiled_modules.clear()
        logger.debug("TypeScript execution cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'execution_cache_size': len(self._execution_cache),
            'compiled_modules_size': len(self._compiled_modules),
            'ts_cache_directory': str(self._ts_node_cache_dir) if self._ts_node_cache_dir else None
        }
    
    def precompile_mastra_agent(self, region_info: RegionInfo) -> bool:
        """Precompile a Mastra agent to improve subsequent execution speed.
        
        Args:
            region_info: The region info containing the Mastra agent code
            
        Returns:
            True if precompilation was successful, False otherwise
        """
        if not self._is_mastra_agent(region_info):
            logger.debug("Not a Mastra agent, skipping precompilation")
            return False
        
        try:
            logger.debug(f"Precompiling Mastra agent: {region_info.name}")
            
            # Create a temporary file for precompilation in the workspace root
            import tempfile
            import time
            temp_file_path = self.workspace_root / f"temp_precompile_{region_info.name}_{int(time.time())}.ts"
            with open(temp_file_path, 'w') as temp_file:
                temp_file.write(region_info.code)
                
                # Run TypeScript compiler to check syntax (not ts-node which tries to execute)
                logger.debug(f"Running TypeScript syntax check for {region_info.name}")
                logger.debug(f"Working directory: {self.workspace_root}")
                logger.debug(f"Temp file: {temp_file_path}")
                
                # Check if node_modules exists in workspace
                node_modules_path = self.workspace_root / 'node_modules'
                if node_modules_path.exists():
                    logger.debug(f"node_modules found at: {node_modules_path}")
                else:
                    logger.warning(f"node_modules not found at: {node_modules_path}")
                
                # Use tsc for syntax checking instead of ts-node for execution
                result = subprocess.run(
                    ['npx', 'tsc', '--noEmit', '--skipLibCheck', str(temp_file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,  # Shorter timeout for precompilation
                    cwd=str(self.workspace_root),  # Run in workspace root to find node_modules
                    env={
                        **os.environ,
                        'NODE_ENV': 'production',
                    }
                )
                
                # Clean up
                try:
                    temp_file_path.unlink()
                except OSError:
                    pass
                
                if result.returncode == 0:
                    logger.debug(f"Successfully precompiled Mastra agent: {region_info.name}")
                    return True
                else:
                    logger.warning(f"Precompilation failed for {region_info.name}")
                    logger.warning(f"Return code: {result.returncode}")
                    logger.warning(f"stderr: {result.stderr}")
                    logger.warning(f"stdout: {result.stdout}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Error during precompilation of {region_info.name}: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up resources and clear caches."""
        self.clear_cache()
        logger.debug("CodeRegionExecutor cleanup completed")









    def diagnose_typescript_environment(self) -> Dict[str, Any]:
        """Diagnose TypeScript environment issues that might cause timeouts."""
        import subprocess
        import time
        
        logger.info("🔍 Diagnosing TypeScript environment...")
        
        diagnostics = {
            'node_version': None,
            'npm_version': None,
            'ts_node_version': None,
            'typescript_version': None,
            'cache_directory': None,
            'network_access': None,
            'basic_compilation': None,
            'mastra_dependencies': None,
            'issues': []
        }
        
        try:
            # Check Node.js version
            logger.info("📋 Checking Node.js version...")
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=10, cwd=str(self.workspace_root))
            if result.returncode == 0:
                diagnostics['node_version'] = result.stdout.strip()
                logger.info(f"✅ Node.js: {diagnostics['node_version']}")
            else:
                diagnostics['issues'].append("Node.js not found or not working")
                logger.error("❌ Node.js not found")
        except Exception as e:
            diagnostics['issues'].append(f"Node.js check failed: {str(e)}")
            logger.error(f"❌ Node.js check failed: {str(e)}")
        
        try:
            # Check npm version
            logger.info("📋 Checking npm version...")
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True, timeout=10, cwd=str(self.workspace_root))
            if result.returncode == 0:
                diagnostics['npm_version'] = result.stdout.strip()
                logger.info(f"✅ npm: {diagnostics['npm_version']}")
            else:
                diagnostics['issues'].append("npm not found or not working")
                logger.error("❌ npm not found")
        except Exception as e:
            diagnostics['issues'].append(f"npm check failed: {str(e)}")
            logger.error(f"❌ npm check failed: {str(e)}")
        
        try:
            # Check ts-node version
            logger.info("📋 Checking ts-node version...")
            result = subprocess.run(['npx', 'ts-node', '--version'], capture_output=True, text=True, timeout=30, cwd=str(self.workspace_root))
            if result.returncode == 0:
                diagnostics['ts_node_version'] = result.stdout.strip()
                logger.info(f"✅ ts-node: {diagnostics['ts_node_version']}")
            else:
                diagnostics['issues'].append("ts-node not found or not working")
                logger.error("❌ ts-node not found")
        except Exception as e:
            diagnostics['issues'].append(f"ts-node check failed: {str(e)}")
            logger.error(f"❌ ts-node check failed: {str(e)}")
        
        try:
            # Check TypeScript version
            logger.info("📋 Checking TypeScript version...")
            result = subprocess.run(['npx', 'tsc', '--version'], capture_output=True, text=True, timeout=30, cwd=str(self.workspace_root))
            if result.returncode == 0:
                diagnostics['typescript_version'] = result.stdout.strip()
                logger.info(f"✅ TypeScript: {diagnostics['typescript_version']}")
            else:
                diagnostics['issues'].append("TypeScript not found or not working")
                logger.error("❌ TypeScript not found")
        except Exception as e:
            diagnostics['issues'].append(f"TypeScript check failed: {str(e)}")
            logger.error(f"❌ TypeScript check failed: {str(e)}")
        
        # Check cache directory
        if self._ts_node_cache_dir:
            diagnostics['cache_directory'] = str(self._ts_node_cache_dir)
            if self._ts_node_cache_dir.exists():
                logger.info(f"✅ Cache directory exists: {diagnostics['cache_directory']}")
            else:
                logger.info(f"⚠️  Cache directory doesn't exist yet: {diagnostics['cache_directory']}")
        
        # Test network access
        try:
            logger.info("🌐 Testing npm registry access...")
            result = subprocess.run(['npm', 'ping'], capture_output=True, text=True, timeout=30, cwd=str(self.workspace_root))
            if result.returncode == 0:
                diagnostics['network_access'] = "OK"
                logger.info("✅ npm registry accessible")
            else:
                diagnostics['network_access'] = "Failed"
                diagnostics['issues'].append("npm registry not accessible")
                logger.error("❌ npm registry not accessible")
        except Exception as e:
            diagnostics['network_access'] = f"Error: {str(e)}"
            diagnostics['issues'].append(f"Network test failed: {str(e)}")
            logger.error(f"❌ Network test failed: {str(e)}")
        
        # Test basic compilation
        try:
            logger.info("🔨 Testing basic TypeScript compilation...")
            test_code = "console.log('Hello, World!');"
            
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
                f.write(test_code)
                f.flush()
                
                start_time = time.time()
                result = subprocess.run(
                    ['npx', 'ts-node', f.name],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(self.workspace_root)
                )
                compile_time = time.time() - start_time
                
                try:
                    os.unlink(f.name)
                except:
                    pass
                
                if result.returncode == 0:
                    diagnostics['basic_compilation'] = f"OK ({compile_time:.2f}s)"
                    logger.info(f"✅ Basic compilation successful ({compile_time:.2f}s)")
                else:
                    diagnostics['basic_compilation'] = f"Failed: {result.stderr}"
                    diagnostics['issues'].append(f"Basic compilation failed: {result.stderr}")
                    logger.error(f"❌ Basic compilation failed: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            diagnostics['basic_compilation'] = "Timeout (>60s)"
            diagnostics['issues'].append("Basic compilation timed out")
            logger.error("⏰ Basic compilation timed out")
        except Exception as e:
            diagnostics['basic_compilation'] = f"Error: {str(e)}"
            diagnostics['issues'].append(f"Basic compilation error: {str(e)}")
            logger.error(f"❌ Basic compilation error: {str(e)}")
        
        # Check for Mastra dependencies
        try:
            logger.info("🤖 Checking for Mastra dependencies...")
            
            # Check for @mastra/core
            result = subprocess.run(['npm', 'list', '@mastra/core'], capture_output=True, text=True, timeout=30, cwd=str(self.workspace_root))
            mastra_core_installed = result.returncode == 0 and '@mastra/core' in result.stdout
            
            # Check for @ai-sdk/google
            result = subprocess.run(['npm', 'list', '@ai-sdk/google'], capture_output=True, text=True, timeout=30, cwd=str(self.workspace_root))
            ai_sdk_google_installed = result.returncode == 0 and '@ai-sdk/google' in result.stdout
            
            if mastra_core_installed and ai_sdk_google_installed:
                diagnostics['mastra_dependencies'] = "Installed"
                logger.info("✅ @mastra/core and @ai-sdk/google are installed")
            elif mastra_core_installed and not ai_sdk_google_installed:
                diagnostics['mastra_dependencies'] = "Partial (@mastra/core only)"
                diagnostics['issues'].append("@ai-sdk/google is missing (required for Mastra agents)")
                logger.warning("⚠️  @mastra/core is installed but @ai-sdk/google is missing")
            elif not mastra_core_installed and ai_sdk_google_installed:
                diagnostics['mastra_dependencies'] = "Partial (@ai-sdk/google only)"
                diagnostics['issues'].append("@mastra/core is missing (required for Mastra agents)")
                logger.warning("⚠️  @ai-sdk/google is installed but @mastra/core is missing")
            else:
                diagnostics['mastra_dependencies'] = "Not installed"
                diagnostics['issues'].append("Mastra dependencies not installed (@mastra/core and @ai-sdk/google)")
                logger.info("ℹ️  Mastra dependencies not installed")
        except Exception as e:
            diagnostics['mastra_dependencies'] = f"Check failed: {str(e)}"
            logger.error(f"❌ Mastra dependency check failed: {str(e)}")
        
        # Summary
        if diagnostics['issues']:
            logger.error(f"❌ Found {len(diagnostics['issues'])} issues:")
            for issue in diagnostics['issues']:
                logger.error(f"   • {issue}")
        else:
            logger.info("✅ No obvious issues found in TypeScript environment")
        
        return diagnostics

    def validate_mastra_agent_syntax(self, region_info: RegionInfo) -> bool:
        """Validate TypeScript syntax for a Mastra agent to ensure it can be compiled.
        
        Args:
            region_info: The region info containing the Mastra agent code
            
        Returns:
            True if syntax validation was successful, False otherwise
        """

    def diagnose_import_resolution(self, module_name: str = '@ai-sdk/google') -> Dict[str, Any]:
        """Diagnose import resolution issues for a specific module.
        
        Args:
            module_name: Name of the module to diagnose (default: @ai-sdk/google)
            
        Returns:
            Dictionary with diagnostic information
        """
        import subprocess
        import time
        
        logger.info(f"🔍 Diagnosing import resolution for: {module_name}")
        
        diagnostics = {
            'module_name': module_name,
            'workspace_root': str(self.workspace_root),
            'node_modules_exists': False,
            'module_in_node_modules': False,
            'npm_list_result': None,
            'require_test': None,
            'import_test': None,
            'issues': []
        }
        
        # Check if node_modules exists
        node_modules_path = self.workspace_root / 'node_modules'
        diagnostics['node_modules_exists'] = node_modules_path.exists()
        
        if not diagnostics['node_modules_exists']:
            diagnostics['issues'].append(f"node_modules not found at {node_modules_path}")
            logger.error(f"❌ node_modules not found at {node_modules_path}")
            return diagnostics
        
        # Check if the specific module exists in node_modules
        module_path = node_modules_path / module_name
        diagnostics['module_in_node_modules'] = module_path.exists()
        
        if not diagnostics['module_in_node_modules']:
            diagnostics['issues'].append(f"Module {module_name} not found in node_modules")
            logger.error(f"❌ Module {module_name} not found in node_modules")
        else:
            logger.info(f"✅ Module {module_name} found in node_modules")
        
        # Test npm list
        try:
            logger.info(f"📋 Checking npm list for {module_name}...")
            result = subprocess.run(
                ['npm', 'list', module_name], 
                capture_output=True, 
                text=True, 
                timeout=30, 
                cwd=str(self.workspace_root)
            )
            diagnostics['npm_list_result'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                logger.info(f"✅ npm list successful for {module_name}")
                logger.debug(f"   Output: {result.stdout.strip()}")
            else:
                logger.error(f"❌ npm list failed for {module_name}")
                logger.error(f"   Error: {result.stderr.strip()}")
                diagnostics['issues'].append(f"npm list failed: {result.stderr.strip()}")
        except Exception as e:
            diagnostics['issues'].append(f"npm list check failed: {str(e)}")
            logger.error(f"❌ npm list check failed: {str(e)}")
        
        # Test require in Node.js
        try:
            logger.info(f"🧪 Testing require() for {module_name}...")
            test_script = f"""
try {{
    const module = require('{module_name}');
    console.log('SUCCESS: Module loaded successfully');
    console.log('Module type:', typeof module);
    console.log('Module keys:', Object.keys(module || {{}}));
}} catch (error) {{
    console.error('ERROR:', error.message);
    process.exit(1);
}}
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(test_script)
                f.flush()
                
                result = subprocess.run(
                    ['node', f.name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self.workspace_root)
                )
                
                try:
                    os.unlink(f.name)
                except:
                    pass
                
                diagnostics['require_test'] = {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                
                if result.returncode == 0:
                    logger.info(f"✅ require() test successful for {module_name}")
                    logger.debug(f"   Output: {result.stdout.strip()}")
                else:
                    logger.error(f"❌ require() test failed for {module_name}")
                    logger.error(f"   Error: {result.stderr.strip()}")
                    diagnostics['issues'].append(f"require() test failed: {result.stderr.strip()}")
                    
        except Exception as e:
            diagnostics['issues'].append(f"require() test failed: {str(e)}")
            logger.error(f"❌ require() test failed: {str(e)}")
        
        # Test import in TypeScript
        try:
            logger.info(f"🧪 Testing import for {module_name} in TypeScript...")
            test_script = f"""
import {{ google }} from '{module_name}';
console.log('SUCCESS: Module imported successfully');
console.log('Google object:', typeof google);
"""
            
            test_file_path = self.workspace_root / f"temp_import_test_{int(time.time())}.ts"
            with open(test_file_path, 'w') as f:
                f.write(test_script)
            
            result = subprocess.run(
                ['npx', 'ts-node', '--transpile-only', str(test_file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace_root)
            )
            
            try:
                test_file_path.unlink()
            except:
                pass
            
            diagnostics['import_test'] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if result.returncode == 0:
                logger.info(f"✅ import test successful for {module_name}")
                logger.debug(f"   Output: {result.stdout.strip()}")
            else:
                logger.error(f"❌ import test failed for {module_name}")
                logger.error(f"   Error: {result.stderr.strip()}")
                diagnostics['issues'].append(f"import test failed: {result.stderr.strip()}")
                
        except Exception as e:
            diagnostics['issues'].append(f"import test failed: {str(e)}")
            logger.error(f"❌ import test failed: {str(e)}")
        
        # Summary
        if diagnostics['issues']:
            logger.error(f"❌ Found {len(diagnostics['issues'])} import resolution issues:")
            for issue in diagnostics['issues']:
                logger.error(f"   • {issue}")
        else:
            logger.info("✅ No import resolution issues found")
        
        return diagnostics

    def _execute_with_mastra_specific_handling(
        self, region_info: 'RegionInfo', method_name: 'Optional[str]', 
        input_data: 'List[Any]', tracked_variables: 'Set[str]', 
        timeout: 'Optional[int]', is_mastra: bool
    ) -> dict:
        """Execute TypeScript with Mastra-specific handling and enhanced debug logging."""
        import json
        import subprocess
        import time
        import os
        logger.info(f"🤖 Using Mastra-specific execution strategy...")
        temp_file_path = self.workspace_root / f"temp_mastra_{region_info.name}_{int(time.time())}.ts"
        with open(temp_file_path, 'w') as temp_file:
            temp_file.write(region_info.code)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        # Create execution script using the enhanced code region module
        from .enhanced_code_region import create_enhanced_typescript_execution_script
        execution_script = create_enhanced_typescript_execution_script(
            str(temp_file_path), method_name, input_data, self.workspace_root, is_mastra=True
        )
        
        # Add comprehensive logging for Mastra execution
        logger.debug(f"🔍 MASTRA EXECUTION PREVIEW:")
        logger.debug(f"   📥 Input Data:")
        logger.debug(f"      Type: {type(input_data)}")
        logger.debug(f"      Length: {len(input_data) if isinstance(input_data, (list, tuple)) else 'N/A'}")
        logger.debug(f"      Content: {repr(input_data)}")
        logger.debug(f"   📄 Generated Mastra TypeScript Script Preview:")
        logger.debug(f"      Total length: {len(execution_script)} characters")
        logger.debug(f"      First 500 chars: {repr(execution_script[:500])}")
        logger.debug(f"      Last 200 chars: {repr(execution_script[-200:])}")
        
        # Show the actual script content for debugging
        logger.debug(f"   📋 FULL MASTRA SCRIPT:")
        logger.debug(f"      {'='*80}")
        script_lines = execution_script.split('\n')
        for i, line in enumerate(script_lines, 1):
            if i <= 20:  # Show first 20 lines
                logger.debug(f"      {i:2d}: {line}")
            elif i == 21:
                logger.debug(f"      ... (showing first 20 lines, script has {len(script_lines)} total lines)")
                break
        logger.debug(f"      {'='*80}")
        exec_file_path = self.workspace_root / f"temp_mastra_script_{region_info.name}_{int(time.time())}.ts"
        with open(exec_file_path, 'w') as exec_file:
            exec_file.write(execution_script)
            exec_file.flush()
            os.fsync(exec_file.fileno())
        try:
            ts_node_cmd = [
                'npx', 'ts-node',
                '--transpile-only',
                '--skip-project',
                '--compiler-options', '{"module":"commonjs","target":"es2020","esModuleInterop":true,"skipLibCheck":true,"moduleResolution":"node16","allowImportingTsExtensions":true}',
                str(exec_file_path)
            ]
            logger.debug(f"🚀 Starting Mastra-specific ts-node execution...")
            logger.debug(f"   Command: {' '.join(ts_node_cmd)}")
            execution_start = time.time()
            result = subprocess.run(
                ts_node_cmd,
                capture_output=True,
                text=True,
                timeout=timeout or 180,
                cwd=str(self.workspace_root),
                env={
                    **os.environ,
                    'NODE_ENV': 'production',
                    'TS_NODE_CACHE': 'true',
                    'TS_NODE_CACHE_DIRECTORY': str(self._ts_node_cache_dir) if self._ts_node_cache_dir else '',
                }
            )
            execution_time = time.time() - execution_start
            logger.debug(f"✅ Mastra-specific execution completed (took {execution_time:.2f}s)")
            if result.returncode != 0:
                logger.error(f"❌ Mastra-specific execution failed!")
                logger.error(f"   Return code: {result.returncode}")
                logger.error(f"   stderr: {result.stderr}")
                logger.error(f"   stdout: {result.stdout}")
                raise Exception(f"Mastra-specific execution failed: {result.stderr}")
            if not result.stdout.strip():
                logger.error(f"❌ Mastra-specific execution produced no output!")
                logger.error(f"   stdout is empty")
                logger.error(f"   stderr: {result.stderr}")
                raise Exception(f"Mastra-specific execution produced no output. stderr: {result.stderr}")
            output_data = json.loads(result.stdout.strip())
            return {
                'result': output_data.get('result'),
                'tracked_values': output_data.get('tracked_values', {}),
                'tracked_variables': tracked_variables,
                'execution_time': execution_time
            }
        finally:
            try:
                exec_file_path.unlink()
            except OSError:
                pass
            try:
                temp_file_path.unlink()
            except OSError:
                pass