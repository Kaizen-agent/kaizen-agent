"""Simple import resolver that analyzes files and loads all needed imports into namespace."""

import ast
import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Set
import runpy

logger = logging.getLogger(__name__)


class SimpleImportResolver:
    """Simple import resolver that analyzes files and loads all imports."""
    
    def __init__(self, workspace_root: Path):
        """Initialize the simple import resolver.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = workspace_root
        self._processed_files: Set[Path] = set()
        self._loaded_modules: Dict[str, Any] = {}
    
    def resolve_imports_for_file(self, file_path: Path) -> Dict[str, Any]:
        """Resolve all imports needed for a file and its dependencies.
        
        Args:
            file_path: Path to the main file to analyze
            
        Returns:
            Dictionary containing all resolved imports
        """
        namespace = {}
        
        # Reset state for new resolution
        self._processed_files.clear()
        self._loaded_modules.clear()
        
        # Process the main file and all its dependencies
        self._process_file_and_dependencies(file_path, namespace)
        
        # For the main file, import it as a module and extract its classes
        self._import_main_file_classes(file_path, namespace)
        
        logger.info(f"Resolved {len(namespace)} imports for {file_path.name}")
        return namespace
    
    def _process_file_and_dependencies(self, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Process a file and all its dependencies recursively.
        
        Args:
            file_path: Path to the file to process
            namespace: Dictionary to add imports to
        """
        if file_path in self._processed_files:
            return
        
        self._processed_files.add(file_path)
        logger.debug(f"Processing file: {file_path}")
        
        try:
            # Read and parse the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract all imports from this file
            imports = self._extract_imports_from_ast(tree)
            
            # Process each import
            for import_info in imports:
                self._process_import(import_info, namespace, file_path)
            
            # Find and process local file dependencies
            local_deps = self._find_local_dependencies(tree, file_path)
            for dep_path in local_deps:
                if dep_path.exists():
                    self._import_local_file_as_module(dep_path)
                    self._process_file_and_dependencies(dep_path, namespace)
        except Exception as e:
            logger.warning(f"Failed to process {file_path}: {str(e)}")
    
    def _import_main_file_classes(self, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Import the main file as a module using runpy and extract its classes into the namespace."""
        import runpy
        import sys
        
        # Validate that file_path is within the workspace root
        try:
            # Compute module name relative to workspace root
            rel_path = file_path.relative_to(self.workspace_root)
            module_name = '.'.join(rel_path.with_suffix('').parts)
        except ValueError as e:
            # File is not in the workspace root - this can happen when users specify
            # files from different workspaces or use absolute paths incorrectly
            logger.warning(f"File {file_path} is not in the workspace root {self.workspace_root}. "
                          f"This may indicate a configuration issue. Error: {str(e)}")
            
            # Try to handle this gracefully by using the file name as module name
            module_name = file_path.stem
            logger.info(f"Using file name '{module_name}' as module name for {file_path}")
        
        # Ensure __init__.py exists in all parent directories
        try:
            parent = file_path.parent
            while parent != self.workspace_root and not (parent / '__init__.py').exists():
                try:
                    (parent / '__init__.py').touch()
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not create __init__.py in {parent}: {str(e)}")
                    break
                parent = parent.parent
            if not (self.workspace_root / '__init__.py').exists():
                try:
                    (self.workspace_root / '__init__.py').touch()
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not create __init__.py in workspace root: {str(e)}")
        except Exception as e:
            logger.warning(f"Error setting up __init__.py files: {str(e)}")
        
        try:
            original_sys_path = sys.path.copy()
            sys.path.insert(0, str(self.workspace_root))
            try:
                module_namespace = runpy.run_module(module_name, run_name="__main__", alter_sys=True)
                # Extract classes from runpy namespace
                for name, obj in module_namespace.items():
                    if isinstance(obj, type) and not name.startswith('_'):
                        namespace[name] = obj
                        logger.debug(f"Added class {name} from {file_path.name} (runpy)")
                # Also extract classes from sys.modules[module_name] if present
                mod = sys.modules.get(module_name)
                if mod:
                    for name, obj in mod.__dict__.items():
                        if isinstance(obj, type) and not name.startswith('_'):
                            namespace[name] = obj
                            logger.debug(f"Added class {name} from sys.modules[{module_name}] (runpy)")
            finally:
                sys.path = original_sys_path
        except Exception as e:
            logger.warning(f"Failed to import main file as module with runpy: {file_path}: {str(e)}")
            # Fallback: extract classes directly from AST
            self._extract_classes_from_ast_fallback(file_path, namespace)
    
    def _extract_classes_from_ast_fallback(self, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Fallback method: extract classes directly from AST and evaluate them in a namespace with dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Create a namespace with all dependencies
            fallback_namespace = {}
            
            # Add all existing imports to the fallback namespace
            for name, obj in namespace.items():
                if isinstance(obj, type) or callable(obj):
                    fallback_namespace[name] = obj
            
            # Add essential built-ins
            import builtins
            fallback_namespace.update({
                '__builtins__': builtins.__dict__,
                '__name__': '__main__',
                '__file__': str(file_path),
                '__package__': None
            })
            
            # Extract classes from all processed files (dependencies)
            logger.debug(f"DEBUG: Processing {len(self._processed_files)} files for fallback extraction")
            for processed_file in self._processed_files:
                logger.debug(f"DEBUG: Processing dependency file: {processed_file}")
                if processed_file != file_path:  # Skip the main file itself
                    self._extract_classes_from_file_to_namespace(processed_file, fallback_namespace)
            
            # Extract and evaluate each class definition from the main file
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Get the class source code
                    class_source = ast.unparse(node)
                    
                    # Execute the class definition in the fallback namespace
                    try:
                        exec(class_source, fallback_namespace)
                        # Add the class to the main namespace
                        if node.name in fallback_namespace:
                            namespace[node.name] = fallback_namespace[node.name]
                            logger.debug(f"Added class {node.name} from {file_path.name} (fallback AST)")
                    except Exception as e:
                        logger.warning(f"Failed to evaluate class {node.name} from {file_path.name}: {str(e)}")
            
            # Add all classes from fallback namespace to main namespace
            for name, obj in fallback_namespace.items():
                if isinstance(obj, type) and not name.startswith('_'):
                    namespace[name] = obj
                    logger.debug(f"Added class {name} from fallback namespace to main namespace")
                        
        except Exception as e:
            logger.warning(f"Failed to extract classes from AST fallback for {file_path}: {str(e)}")
    
    def _extract_classes_from_file_to_namespace(self, file_path: Path, namespace: Dict[str, Any]) -> None:
        """Extract classes from a file and add them to the given namespace."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Extract and evaluate each class definition
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Get the class source code
                    class_source = ast.unparse(node)
                    
                    # Execute the class definition in the namespace
                    try:
                        exec(class_source, namespace)
                        logger.debug(f"Added class {node.name} from {file_path.name} (fallback dependency)")
                    except Exception as e:
                        logger.warning(f"Failed to evaluate class {node.name} from {file_path.name}: {str(e)}")
                        
        except Exception as e:
            logger.warning(f"Failed to extract classes from {file_path}: {str(e)}")
    
    def _extract_imports_from_ast(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract all import statements from AST.
        
        Args:
            tree: AST to analyze
            
        Returns:
            List of import information dictionaries
        """
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname or alias.name,
                        'level': 0
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append({
                        'type': 'from',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname or alias.name,
                        'level': node.level
                    })
        
        return imports
    
    def _find_local_dependencies(self, tree: ast.AST, current_file: Path) -> Set[Path]:
        """Find local file dependencies from import statements.
        
        Args:
            tree: AST to analyze
            current_file: Current file being processed
            
        Returns:
            Set of local file paths that are imported
        """
        local_deps = set()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep_path = self._resolve_local_path(alias.name, current_file)
                        if dep_path:
                            local_deps.add(dep_path)
                else:  # ImportFrom
                    if node.module:
                        dep_path = self._resolve_local_path(node.module, current_file)
                        if dep_path:
                            local_deps.add(dep_path)
        
        return local_deps
    
    def _resolve_local_path(self, module_name: str, current_file: Path) -> Path:
        """Resolve a module name to a local file path.
        
        Args:
            module_name: Name of the module
            current_file: Current file being processed
            
        Returns:
            Path to the local file if found, None otherwise
        """
        # Skip standard library and third-party modules
        if self._is_external_module(module_name):
            return None
        
        # Handle relative imports
        if module_name.startswith('.'):
            # Convert relative import to absolute path
            parts = module_name.split('.')
            level = len([p for p in parts if p == ''])
            
            # Build path from current file
            base_path = current_file.parent
            for _ in range(level):
                base_path = base_path.parent
            
            # Add the module parts
            module_parts = [p for p in parts if p]
            if module_parts:
                module_path = base_path / '/'.join(module_parts)
            else:
                module_path = base_path
        else:
            # Absolute import from workspace
            module_path = self.workspace_root / module_name.replace('.', '/')
        
        # Try different file extensions
        for ext in ['.py', '/__init__.py']:
            test_path = module_path.with_suffix(ext) if ext == '.py' else module_path / '__init__.py'
            if test_path.exists():
                return test_path
        
        return None
    
    def _is_external_module(self, module_name: str) -> bool:
        """Check if a module is external (standard library or third-party).
        
        Args:
            module_name: Name of the module
            
        Returns:
            True if external, False if local
        """
        # Standard library modules
        stdlib_modules = {
            'os', 'sys', 'pathlib', 'typing', 'logging', 'json', 'datetime', 
            'time', 're', 'math', 'random', 'collections', 'dataclasses', 
            'enum', 'importlib', 'ast', 'contextlib', 'itertools', 'functools'
        }
        
        # Get the base module name (first part)
        base_name = module_name.split('.')[0]
        
        # Check if it's a standard library module
        if base_name in stdlib_modules:
            return True
        
        # Check if it's already loaded in sys.modules (third-party)
        if base_name in sys.modules:
            # But don't treat local modules as external
            module = sys.modules[base_name]
            if hasattr(module, '__file__') and module.__file__:
                module_path = Path(module.__file__)
                if self.workspace_root in module_path.parents:
                    return False
        
        # For local modules, check if they exist in workspace
        if not module_name.startswith('.'):
            module_path = self.workspace_root / module_name.replace('.', '/')
            py_file = module_path.with_suffix('.py')
            init_file = module_path / '__init__.py'
            if py_file.exists() or init_file.exists():
                return False
        
        return True
    
    def _process_import(self, import_info: Dict[str, Any], namespace: Dict[str, Any], current_file: Path) -> None:
        """Process a single import statement.
        
        Args:
            import_info: Import information dictionary
            namespace: Dictionary to add imports to
            current_file: Current file being processed
        """
        try:
            if import_info['type'] == 'import':
                self._process_import_statement(import_info['module'], import_info['alias'], namespace, current_file)
            elif import_info['type'] == 'from':
                self._process_from_import(import_info['module'], import_info['name'], 
                                        import_info['alias'], namespace, import_info['level'], current_file)
        except Exception as e:
            logger.debug(f"Failed to process import {import_info}: {str(e)}")
    
    def _process_import_statement(self, module_name: str, alias: str, namespace: Dict[str, Any], current_file: Path) -> None:
        """Process an 'import module' statement.
        
        Args:
            module_name: Name of the module to import
            alias: Alias for the module
            namespace: Dictionary to add imports to
            current_file: Current file being processed
        """
        if module_name in self._loaded_modules:
            module = self._loaded_modules[module_name]
        else:
            module = self._try_import_module(module_name, current_file)
            if module:
                self._loaded_modules[module_name] = module
        
        if module:
            namespace[alias] = module
            
            # Also add all classes from the module
            self._add_classes_from_module(module, module_name, namespace)
    
    def _process_from_import(self, module_name: str, name: str, alias: str, 
                           namespace: Dict[str, Any], level: int = 0, current_file: Path = None) -> None:
        """Process a 'from module import name' statement.
        
        Args:
            module_name: Name of the module
            name: Name to import from the module
            alias: Alias for the imported name
            namespace: Dictionary to add imports to
            level: Level of relative import
            current_file: Current file being processed
        """
        if level > 0:
            # Handle relative imports
            if current_file:
                # Convert relative import to absolute
                parts = module_name.split('.')
                level_count = len([p for p in parts if p == ''])
                
                base_path = current_file.parent
                for _ in range(level_count):
                    base_path = base_path.parent
                
                module_parts = [p for p in parts if p]
                if module_parts:
                    module_name = '.'.join(module_parts)
                else:
                    module_name = ''
            else:
                logger.debug(f"Relative imports not supported without current_file: {module_name}")
                return
        
        if name == '*':
            # Handle star imports
            module = self._try_import_module(module_name, current_file)
            if module:
                self._add_classes_from_module(module, module_name, namespace)
        else:
            # Handle specific imports
            module = self._try_import_module(module_name, current_file)
            if module and hasattr(module, name):
                namespace[alias] = getattr(module, name)
    
    def _try_import_module(self, module_name: str, current_file: Path = None) -> Any:
        """Try to import a module.
        
        Args:
            module_name: Name of the module to import
            current_file: Current file being processed
            
        Returns:
            Imported module or None if import failed
        """
        try:
            # Try standard import
            module = __import__(module_name)
            return module
        except ImportError:
            # Try to import from workspace
            return self._try_import_from_workspace(module_name, current_file)
    
    def _try_import_from_workspace(self, module_name: str, current_file: Path = None) -> Any:
        """Try to import a module from the workspace.
        
        Args:
            module_name: Name of the module to import
            current_file: Current file being processed
            
        Returns:
            Imported module or None if import failed
        """
        try:
            # Convert module name to file path
            if current_file and module_name.startswith('.'):
                # Handle relative imports
                parts = module_name.split('.')
                level_count = len([p for p in parts if p == ''])
                
                base_path = current_file.parent
                for _ in range(level_count):
                    base_path = base_path.parent
                
                module_parts = [p for p in parts if p]
                if module_parts:
                    module_path = base_path / '/'.join(module_parts)
                else:
                    module_path = base_path
            else:
                # Absolute import from workspace
                module_path = self.workspace_root / module_name.replace('.', '/')
            
            # Try as Python file
            py_file = module_path.with_suffix('.py')
            if py_file.exists():
                return self._import_module_from_file(module_name, py_file)
            
            # Try as package
            init_file = module_path / '__init__.py'
            if init_file.exists():
                return self._import_module_from_file(module_name, init_file)
            
            return None
        except Exception as e:
            logger.debug(f"Failed to import {module_name} from workspace: {str(e)}")
            return None
    
    def _import_module_from_file(self, module_name: str, file_path: Path) -> Any:
        """Import a module from a file.
        
        Args:
            module_name: Name for the module
            file_path: Path to the module file
            
        Returns:
            Imported module
        """
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            logger.debug(f"Failed to import module from {file_path}: {str(e)}")
        
        return None
    
    def _add_classes_from_module(self, module: Any, module_name: str, namespace: Dict[str, Any]) -> None:
        """Add all classes from a module to the namespace.
        
        Args:
            module: The module to extract classes from
            module_name: Name of the module
            namespace: Dictionary to add classes to
        """
        if hasattr(module, '__dict__'):
            for name, obj in module.__dict__.items():
                if isinstance(obj, type) and not name.startswith('_'):
                    namespace[name] = obj
                    logger.debug(f"Added class {name} from {module_name}")
    
    def _import_local_file_as_module(self, file_path: Path) -> None:
        """Import a local file as a module and register it in sys.modules under its correct module name and stem if in root."""
        import importlib.util
        import sys
        
        # Validate that file_path is within the workspace root
        try:
            # Compute module name relative to workspace root
            rel_path = file_path.relative_to(self.workspace_root)
            module_name = '.'.join(rel_path.with_suffix('').parts)
        except ValueError as e:
            # File is not in the workspace root - this can happen when users specify
            # files from different workspaces or use absolute paths incorrectly
            logger.warning(f"File {file_path} is not in the workspace root {self.workspace_root}. "
                          f"This may indicate a configuration issue. Error: {str(e)}")
            
            # Try to handle this gracefully by using the file name as module name
            module_name = file_path.stem
            logger.info(f"Using file name '{module_name}' as module name for {file_path}")
        
        stem_name = file_path.stem
        
        # Ensure __init__.py exists in all parent directories
        try:
            parent = file_path.parent
            while parent != self.workspace_root and not (parent / '__init__.py').exists():
                try:
                    (parent / '__init__.py').touch()
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not create __init__.py in {parent}: {str(e)}")
                    break
                parent = parent.parent
            if not (self.workspace_root / '__init__.py').exists():
                try:
                    (self.workspace_root / '__init__.py').touch()
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not create __init__.py in workspace root: {str(e)}")
        except Exception as e:
            logger.warning(f"Error setting up __init__.py files: {str(e)}")
        
        if module_name in sys.modules and (file_path.parent != self.workspace_root or stem_name in sys.modules):
            return
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            # Also register under stem if in workspace root
            if file_path.parent == self.workspace_root:
                sys.modules[stem_name] = module
            try:
                original_sys_path = sys.path.copy()
                sys.path.insert(0, str(self.workspace_root))
                try:
                    spec.loader.exec_module(module)
                finally:
                    sys.path = original_sys_path
            except Exception as e:
                logger.warning(f"Failed to import local file as module: {file_path}: {str(e)}")


def resolve_imports_for_code(code: str, file_path: Path, workspace_root: Path) -> Dict[str, Any]:
    """Simple function to resolve all imports for a piece of code.
    
    Args:
        code: The code to analyze
        file_path: Path to the source file
        workspace_root: Root directory of the workspace
        
    Returns:
        Dictionary containing all resolved imports
    """
    resolver = SimpleImportResolver(workspace_root)
    return resolver.resolve_imports_for_file(file_path) 