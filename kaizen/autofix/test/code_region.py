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
            region_code = content[start_idx:end_idx].strip()
            logger.debug(f"DEBUG: Extracted region code ({len(region_code)} characters)")
            
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
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise RegionExtractionError(f"Failed to extract region with entry point: {str(e)}")

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

class CodeRegionExecutor:
    """Executes code regions with import management and variable tracking."""
    
    def __init__(self, workspace_root: Path, imported_dependencies: Optional[Dict[str, Any]] = None):
        """Initialize the code region executor.
        
        Args:
            workspace_root: Root directory of the workspace
            imported_dependencies: Optional dictionary of pre-imported dependencies
        """
        self.workspace_root = workspace_root
        self.imported_dependencies = imported_dependencies or {}
        self.import_manager = ImportManager(workspace_root)
        self.simple_import_resolver = SimpleImportResolver(workspace_root)
    
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