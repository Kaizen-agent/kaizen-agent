"""Code region extraction and execution."""

# Standard library imports
import ast
import logging
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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

@dataclass
class RegionInfo:
    """Information about a code region."""
    type: RegionType
    name: str
    code: str
    start_line: int
    end_line: int
    imports: List[str]
    class_methods: List[str] = None  # List of methods if this is a class

class CodeRegionExtractor:
    """Extracts and analyzes code regions from files."""
    
    @staticmethod
    def extract_region(file_path: Path, region_name: str) -> RegionInfo:
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
                return CodeRegionExtractor._analyze_region(code, region_name)
            
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
            
            return CodeRegionExtractor._analyze_region(code, region_name)
            
        except Exception as e:
            raise ValueError(f"Failed to extract region '{region_name}': {str(e)}")
    
    @staticmethod
    def _analyze_region(code: str, region_name: str) -> RegionInfo:
        """Analyze the code region to determine its type and structure."""
        try:
            tree = ast.parse(code)
            imports = CodeRegionExtractor._extract_imports(tree)
            region_type, name, methods = CodeRegionExtractor._determine_region_type(tree)
            
            return RegionInfo(
                type=region_type,
                name=name or region_name,
                code=code,
                start_line=tree.body[0].lineno if tree.body else 1,
                end_line=tree.body[-1].end_lineno if tree.body else 1,
                imports=imports,
                class_methods=methods
            )
        except SyntaxError as e:
            raise ValueError(f"Invalid Python code in region: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to analyze region code: {str(e)}")
    
    @staticmethod
    def _extract_imports(tree: ast.AST) -> List[str]:
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
    
    @staticmethod
    def _determine_region_type(tree: ast.AST) -> tuple[RegionType, str, List[str]]:
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
        self._setup_python_path()
    
    def _setup_python_path(self) -> None:
        """Set up Python path with workspace root."""
        if str(self.workspace_root) not in sys.path:
            sys.path.insert(0, str(self.workspace_root))
    
    def _handle_simple_import(self, module_name: str, namespace: Dict) -> None:
        """Handle simple imports (e.g., 'import os')."""
        try:
            module = __import__(module_name)
            namespace[module_name] = module
        except ImportError as e:
            logger.warning(f"Failed to import {module_name}: {str(e)}")
    
    def _handle_absolute_import(self, module_path: str, namespace: Dict) -> None:
        """Handle absolute imports (e.g., 'from typing import Optional')."""
        try:
            parts = module_path.split('.')
            module_name = parts[0]
            module = __import__(module_name)
            
            # Handle nested imports
            current = module
            for part in parts[1:]:
                if hasattr(current, part):
                    current = getattr(current, part)
                else:
                    raise ImportError(f"Module {module_name} has no attribute {part}")
            
            # Add to namespace
            namespace[parts[-1]] = current
        except ImportError as e:
            logger.warning(f"Failed to import {module_path}: {str(e)}")
    
    def _handle_relative_import(self, module_path: str, namespace: Dict) -> None:
        """Handle relative imports (e.g., 'from . import module')."""
        try:
            # Remove leading dots and get the module name
            module_name = module_path.lstrip('.')
            if not module_name:
                raise ImportError("Invalid relative import path")
            
            # Import the module
            module = __import__(module_name, fromlist=['*'])
            namespace[module_name.split('.')[-1]] = module
        except ImportError as e:
            logger.warning(f"Failed to import {module_path}: {str(e)}")
    
    def execute_region(self, region_info: RegionInfo, method_name: Optional[str] = None, 
                      input_data: Any = None) -> Any:
        """
        Execute a code region and return its result.
        
        Args:
            region_info: Information about the region to execute
            method_name: Name of the method to call (if region is a class)
            input_data: Input data to pass to the function/method
            
        Returns:
            Result of the execution
            
        Raises:
            ValueError: If execution fails
        """
        try:
            with self._create_execution_context(region_info) as namespace:
                if region_info.type == RegionType.CLASS:
                    return self._execute_class_method(namespace, region_info, method_name, input_data)
                elif region_info.type == RegionType.FUNCTION:
                    return self._execute_function(namespace, region_info, input_data)
                else:
                    return self._execute_module(namespace, region_info, method_name, input_data)
        except Exception as e:
            raise ValueError(f"Failed to execute region '{region_info.name}': {str(e)}")
    
    @contextmanager
    def _create_execution_context(self, region_info: RegionInfo):
        """Create a safe execution context with required imports."""
        namespace = {
            '__name__': '__main__',
            '__file__': str(region_info.file_path) if hasattr(region_info, 'file_path') else None,
            '__package__': None,
            '__builtins__': __builtins__
        }
        
        # Add imports to namespace
        for imp in region_info.imports:
            try:
                if imp.startswith('.'):
                    self._handle_relative_import(imp, namespace)
                elif '.' in imp:
                    self._handle_absolute_import(imp, namespace)
                else:
                    self._handle_simple_import(imp, namespace)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to import {imp}: {str(e)}")
        
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