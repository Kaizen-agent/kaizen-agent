"""Test runner implementation for Kaizen."""

import os
import sys
import logging
import yaml
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Protocol
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """Enum for test status values."""
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    ERROR = 'error'
    COMPLETED = 'completed'
    UNKNOWN = 'unknown'

@dataclass
class TestSummary:
    """Data class for test summary statistics."""
    total_regions: int = 0
    passed_regions: int = 0
    failed_regions: int = 0
    error_regions: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Convert summary to dictionary."""
        return {
            'total_regions': self.total_regions,
            'passed_regions': self.passed_regions,
            'failed_regions': self.failed_regions,
            'error_regions': self.error_regions
        }

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

class ImportManager:
    """Manages Python imports and namespace creation."""
    
    def __init__(self, workspace_root: Path):
        """
        Initialize the import manager.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = workspace_root
        self._setup_python_path()
    
    def _setup_python_path(self) -> None:
        """Set up Python path with workspace root."""
        if str(self.workspace_root) not in sys.path:
            sys.path.insert(0, str(self.workspace_root))
    
    @contextmanager
    def create_namespace(self, imports: List[str], file_path: Path) -> Dict:
        """
        Create a safe namespace for code execution.
        
        Args:
            imports: List of imports to include
            file_path: Path to the file being tested
            
        Yields:
            Dict containing the safe namespace
        """
        namespace = {}
        
        for imp in imports:
            try:
                if imp.startswith('.'):
                    self._handle_relative_import(imp, file_path, namespace)
                elif '.' in imp:
                    self._handle_absolute_import(imp, namespace)
                else:
                    self._handle_simple_import(imp, file_path, namespace)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to import {imp}: {str(e)}")
        
        yield namespace
    
    def _handle_relative_import(self, imp: str, file_path: Path, namespace: Dict) -> None:
        """Handle relative imports."""
        module_path = str(file_path.parent)
        if module_path not in sys.path:
            sys.path.insert(0, module_path)
        module = importlib.import_module(imp, package=file_path.parent.name)
        namespace[imp.split('.')[-1]] = module
    
    def _handle_absolute_import(self, imp: str, namespace: Dict) -> None:
        """Handle absolute imports with attributes."""
        module_name, attr_name = imp.rsplit('.', 1)
        module = importlib.import_module(module_name)
        namespace[attr_name] = getattr(module, attr_name)
    
    def _handle_simple_import(self, imp: str, file_path: Path, namespace: Dict) -> None:
        """Handle simple imports with fallback to local directory."""
        try:
            namespace[imp] = importlib.import_module(imp)
        except ImportError:
            module_path = str(file_path.parent)
            if module_path not in sys.path:
                sys.path.insert(0, module_path)
            namespace[imp] = importlib.import_module(imp)

class CodeParser:
    """Parses and analyzes Python code."""
    
    @staticmethod
    def parse_region_code(code: str) -> RegionInfo:
        """
        Parse region code to determine its type and structure.
        
        Args:
            code: The code to parse
            
        Returns:
            RegionInfo object containing parsed information
            
        Raises:
            ValueError: If code cannot be parsed or is invalid
        """
        try:
            tree = ast.parse(code)
            imports = CodeParser._extract_imports(tree)
            region_type, region_name = CodeParser._determine_region_type(tree)
            
            return RegionInfo(
                type=region_type,
                name=region_name,
                code=code,
                start_line=tree.body[0].lineno if tree.body else 1,
                end_line=tree.body[-1].end_lineno if tree.body else 1,
                imports=imports
            )
        except SyntaxError as e:
            raise ValueError(f"Invalid Python code in region: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to parse region code: {str(e)}")
    
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
    def _determine_region_type(tree: ast.AST) -> tuple[RegionType, str]:
        """Determine the type and name of the region."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                return RegionType.CLASS, node.name
            elif isinstance(node, ast.FunctionDef):
                return RegionType.FUNCTION, node.name
        return RegionType.MODULE, "module"

class TestCaseValidator:
    """Validates test case configuration."""
    
    @staticmethod
    def validate_test_case(test_case: Dict) -> None:
        """
        Validate test case configuration.
        
        Args:
            test_case: Test case configuration
            
        Raises:
            ValueError: If test case is invalid
        """
        if not isinstance(test_case.get('input'), dict):
            raise ValueError(f"Invalid test input format: {test_case.get('input')}")
        
        test_input = test_case['input']
        if not all(key in test_input for key in ['region', 'method']):
            raise ValueError(f"Missing required test input fields: {test_input}")

class TestResultHandler:
    """Handles test result creation and formatting."""
    
    @staticmethod
    def create_error_result(error: Exception, context: str) -> Dict:
        """Create a standardized error result."""
        logger.error(f"Error in {context}", extra={
            'error': str(error),
            'error_type': type(error).__name__
        })
        return {
            'status': TestStatus.ERROR.value,
            'error': str(error)
        }
    
    @staticmethod
    def create_success_result(output: Any) -> Dict:
        """Create a standardized success result."""
        return {
            'status': TestStatus.PASSED.value,
            'output': output
        }

class TestRunner:
    """A class for running tests and processing results."""
    
    def __init__(self, test_config: Dict):
        """
        Initialize the test runner.
        
        Args:
            test_config: Test configuration dictionary
        """
        self.test_config = test_config
        self._validate_config()
        self.import_manager = ImportManager(self._find_workspace_root())
        self.code_parser = CodeParser()
        self.test_validator = TestCaseValidator()
        self.result_handler = TestResultHandler()
    
    def _validate_config(self) -> None:
        """Validate the test configuration structure."""
        required_fields = ['name', 'file_path']
        for field in required_fields:
            if field not in self.test_config:
                raise ValueError(f"Missing required field '{field}' in test configuration")
        
        if 'regions' not in self.test_config and 'steps' not in self.test_config:
            raise ValueError("Test configuration must contain either 'regions' or 'steps'")
    
    def _find_workspace_root(self) -> Path:
        """Find the workspace root directory."""
        current = Path.cwd()
        while current.name != 'kaizen-agent' and current.parent != current:
            current = current.parent
        if current.name != 'kaizen-agent':
            raise ValueError("Could not find workspace root directory")
        return current
    
    def _extract_region_code(self, file_path: Path, region_name: str) -> RegionInfo:
        """
        Extract code for a specific region from a file.
        
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
            
            return self.code_parser.parse_region_code(code)
            
        except Exception as e:
            raise ValueError(f"Failed to extract region '{region_name}': {str(e)}")
    
    def _create_region_function(self, region_info: RegionInfo, method_name: str, file_path: Path) -> Callable:
        """
        Create a function from region code.
        
        Args:
            region_info: Information about the region
            method_name: Name of the method to call
            file_path: Path to the file being tested
            
        Returns:
            callable: The created function
            
        Raises:
            ValueError: If function creation fails
        """
        try:
            with self.import_manager.create_namespace(region_info.imports, file_path) as namespace:
                exec(region_info.code, namespace)
                
                if region_info.type == RegionType.CLASS:
                    return self._get_class_method(namespace, region_info.name, method_name)
                elif region_info.type == RegionType.FUNCTION:
                    return self._get_function(namespace, region_info.name, method_name)
                else:  # MODULE
                    return self._get_module_function(namespace, method_name)
                
        except Exception as e:
            raise ValueError(f"Failed to create function from region '{region_info.name}': {str(e)}")
    
    def _get_class_method(self, namespace: Dict, class_name: str, method_name: str) -> Callable:
        """Get a method from a class."""
        test_class = namespace[class_name]
        if not hasattr(test_class, method_name):
            raise ValueError(f"Method '{method_name}' not found in class '{class_name}'")
        instance = test_class()
        return getattr(instance, method_name)
    
    def _get_function(self, namespace: Dict, func_name: str, method_name: str) -> Callable:
        """Get a function directly."""
        if func_name != method_name:
            raise ValueError(f"Function name '{func_name}' does not match requested method '{method_name}'")
        return namespace[func_name]
    
    def _get_module_function(self, namespace: Dict, method_name: str) -> Callable:
        """Get a function from the module."""
        if not hasattr(namespace, method_name):
            raise ValueError(f"Function '{method_name}' not found in module")
        return getattr(namespace, method_name)
    
    def _run_test_case(self, test_case: Dict, test_file_path: Path) -> Dict:
        """
        Run a single test case.
        
        Args:
            test_case: Test case configuration
            test_file_path: Path to the test file
            
        Returns:
            Dict containing test case results
        """
        try:
            self.test_validator.validate_test_case(test_case)
            
            test_input = test_case['input']
            region = test_input['region']
            method = test_input['method']
            input_text = test_input.get('input')
            
            region_info = self._extract_region_code(test_file_path, region)
            test_function = self._create_region_function(region_info, method, test_file_path)
            
            result = test_function(input_text)
            return self.result_handler.create_success_result(result)
            
        except Exception as e:
            return self.result_handler.create_error_result(e, f"test case {test_case.get('name', 'Unknown')}")
    
    def run_tests(self, test_file_path: Path) -> Dict:
        """
        Run tests and return results.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            Dict containing test results
        """
        results = self._create_initial_results()
        summary = TestSummary()
        
        try:
            if not test_file_path.exists():
                raise FileNotFoundError(f"Test file not found: {test_file_path}")
            
            for test_case in self.test_config.get('tests', []):
                test_name = test_case.get('name', 'Unknown')
                test_result = self._run_test_case(test_case, test_file_path)
                
                results[test_name] = {
                    'status': test_result['status'],
                    'test_cases': [test_result],
                    'summary': {
                        'total': 1,
                        'passed': 1 if test_result['status'] == TestStatus.PASSED.value else 0,
                        'failed': 1 if test_result['status'] == TestStatus.FAILED.value else 0,
                        'error': 1 if test_result['status'] == TestStatus.ERROR.value else 0
                    }
                }
                
                summary.total_regions += 1
                if test_result['status'] == TestStatus.PASSED.value:
                    summary.passed_regions += 1
                elif test_result['status'] == TestStatus.FAILED.value:
                    summary.failed_regions += 1
                else:
                    summary.error_regions += 1
            
            results['overall_status'] = {
                'status': TestStatus.COMPLETED.value,
                'summary': summary.to_dict()
            }
            results['_status'] = TestStatus.COMPLETED.value
            
        except Exception as e:
            results['overall_status'] = {
                'status': TestStatus.FAILED.value,
                'summary': summary.to_dict()
            }
            results['_status'] = TestStatus.ERROR.value
        
        return results

    def _create_initial_results(self) -> Dict:
        """
        Create initial results structure.
        
        Returns:
            Dict containing initial results structure
        """
        return {
            'overall_status': {
                'status': TestStatus.PENDING.value,
                'summary': TestSummary().to_dict()
            },
            '_status': TestStatus.RUNNING.value
        } 