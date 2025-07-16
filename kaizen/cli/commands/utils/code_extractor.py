"""Code extraction utilities for surgical fixing.

This module provides utilities to extract relevant code sections from files
for use in surgical code fixing with memory-based learning.
"""

import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import importlib.util
import sys


def extract_relevant_functions(file_content: str, file_path: str = None, agent_config: Dict = None) -> Dict[str, str]:
    """Extract relevant function definitions from code content.
    
    Args:
        file_content: The source code content
        file_path: Optional file path for context
        agent_config: Optional agent configuration containing class information
        
    Returns:
        Dictionary mapping function names to their code sections
    """
    relevant_sections = {}
    
    try:
        # Parse the code to get function definitions
        tree = ast.parse(file_content)
        
        # If agent config is provided, use it to extract targeted functions
        if agent_config and 'agent' in agent_config:
            relevant_sections = extract_targeted_functions(tree, file_content, agent_config['agent'])
        else:
            # Fallback to extracting all functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = node.name
                    # Get the function's source code
                    func_code = ast.unparse(node)
                    relevant_sections[func_name] = func_code
                    
                elif isinstance(node, ast.ClassDef):
                    class_name = node.name
                    # Get the class's source code
                    class_code = ast.unparse(node)
                    relevant_sections[class_name] = class_code
                
    except SyntaxError:
        # Fallback to regex-based extraction for non-Python files or syntax errors
        relevant_sections = extract_functions_regex(file_content, agent_config)
    
    return relevant_sections


def extract_targeted_functions(tree: ast.AST, file_content: str, agent_info: Dict) -> Dict[str, str]:
    """Extract functions and imports needed to run the target class.
    
    Args:
        tree: Parsed AST of the code
        file_content: Original source code content
        agent_info: Agent configuration containing module, class, method info
        
    Returns:
        Dictionary mapping function/class names to their code sections
    """
    relevant_sections = {}
    target_class = agent_info.get('class')
    target_method = agent_info.get('method')
    
    # Extract all imports first
    imports = extract_all_imports(tree)
    for import_name, import_code in imports.items():
        relevant_sections[import_name] = import_code
    
    # Extract the target class if specified
    if target_class:
        class_code = extract_class_with_dependencies(tree, file_content, target_class, target_method)
        if class_code:
            relevant_sections[target_class] = class_code
    
    # Extract helper functions that might be needed (but not methods of the target class)
    helper_functions = extract_helper_functions(tree, target_class, target_method)
    for func_name, func_code in helper_functions.items():
        # Avoid duplicates with class methods
        if func_name not in relevant_sections:
            relevant_sections[func_name] = func_code
    
    return relevant_sections


def extract_all_imports(tree: ast.AST) -> Dict[str, str]:
    """Extract all import statements from the AST.
    
    Args:
        tree: Parsed AST of the code
        
    Returns:
        Dictionary mapping import names to their code
    """
    imports = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # Handle: import module
            for alias in node.names:
                import_name = f"import_{alias.name}"
                import_code = ast.unparse(node)
                imports[import_name] = import_code
                
        elif isinstance(node, ast.ImportFrom):
            # Handle: from module import name
            module_name = node.module or ""
            for alias in node.names:
                import_name = f"from_{module_name}_{alias.name}"
                import_code = ast.unparse(node)
                imports[import_name] = import_code
    
    return imports


def extract_class_with_dependencies(tree: ast.AST, file_content: str, target_class: str, target_method: str = None) -> Optional[str]:
    """Extract a specific class and its dependencies.
    
    Args:
        tree: Parsed AST of the code
        file_content: Original source code content
        target_class: Name of the target class
        target_method: Optional specific method to focus on
        
    Returns:
        Class code as string or None if not found
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == target_class:
            # Always extract the full class code
            class_code = ast.unparse(node)
            return class_code
    
    return None


def extract_specific_method(class_node: ast.ClassDef, method_name: str) -> Optional[str]:
    """Extract a specific method from a class.
    
    Args:
        class_node: Class AST node
        method_name: Name of the method to extract
        
    Returns:
        Method code as string or None if not found
    """
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
            return ast.unparse(node)
    
    return None


def extract_helper_functions(tree: ast.AST, target_class: str, target_method: str = None) -> Dict[str, str]:
    """Extract helper functions that might be needed by the target class/method.
    
    Args:
        tree: Parsed AST of the code
        target_class: Name of the target class
        target_method: Optional specific method
        
    Returns:
        Dictionary of helper function names to their code
    """
    helper_functions = {}
    
    # Extract functions that might be called by the target class
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip if it's a method of the target class
            if hasattr(node, 'parent') and isinstance(node.parent, ast.ClassDef) and node.parent.name == target_class:
                continue
            
            # Skip if it's a method of any class (we only want top-level functions)
            if hasattr(node, 'parent') and isinstance(node.parent, ast.ClassDef):
                continue
            
            # Check if this function might be used by the target class
            if is_potentially_used_function(node, target_class, target_method):
                func_name = node.name
                func_code = ast.unparse(node)
                helper_functions[func_name] = func_code
    
    return helper_functions


def is_potentially_used_function(func_node: ast.FunctionDef, target_class: str, target_method: str = None) -> bool:
    """Check if a function might be used by the target class/method.
    
    Args:
        func_node: Function AST node
        target_class: Name of the target class
        target_method: Optional specific method
        
    Returns:
        True if the function might be used
    """
    # Simple heuristic: include functions that are not private (don't start with _)
    # and are not too long (likely utility functions)
    func_name = func_node.name
    
    # Skip private functions
    if func_name.startswith('_'):
        return False
    
    # Skip very long functions (likely not utility functions)
    if len(ast.unparse(func_node).split('\n')) > 50:
        return False
    
    # Include common utility function patterns
    utility_patterns = [
        'get_', 'set_', 'is_', 'has_', 'can_', 'should_',
        'validate_', 'format_', 'parse_', 'convert_', 'transform_',
        'load_', 'save_', 'read_', 'write_', 'create_', 'build_',
        'process_', 'handle_', 'prepare_', 'clean_', 'normalize_'
    ]
    
    for pattern in utility_patterns:
        if func_name.startswith(pattern):
            return True
    
    return True  # Include all non-private functions for now


def extract_functions_regex(content: str, agent_config: Dict = None) -> Dict[str, str]:
    """Extract function definitions using regex patterns.
    
    Args:
        content: Source code content
        agent_config: Optional agent configuration
        
    Returns:
        Dictionary mapping function names to their code sections
    """
    relevant_sections = {}
    
    # Python function patterns
    python_func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:.*?(?=\n\S|\Z)'
    python_class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*).*?(?=\n\S|\Z)'
    
    # JavaScript/TypeScript patterns
    js_func_pattern = r'(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\([^)]*\)\s*=>|([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{).*?(?=\n\S|\Z)'
    
    # Import patterns
    import_pattern = r'(?:import\s+.*?|from\s+.*?\s+import\s+.*?)(?=\n|\Z)'
    
    # Extract imports first
    for match in re.finditer(import_pattern, content, re.DOTALL):
        import_code = match.group(0)
        relevant_sections[f"import_{len(relevant_sections)}"] = import_code
    
    # If agent config is provided, focus on target class
    if agent_config and 'agent' in agent_config:
        agent_info = agent_config['agent']
        target_class = agent_info.get('class')
        target_method = agent_info.get('method')
        
        if target_class:
            # Extract the target class
            class_pattern = rf'class\s+{re.escape(target_class)}.*?(?=\n\S|\Z)'
            for match in re.finditer(class_pattern, content, re.DOTALL):
                class_code = match.group(0)
                relevant_sections[target_class] = class_code
                break
    
    # Extract all Python functions and classes
    for match in re.finditer(python_func_pattern, content, re.DOTALL):
        func_name = match.group(1)
        func_code = match.group(0)
        relevant_sections[func_name] = func_code
    
    for match in re.finditer(python_class_pattern, content, re.DOTALL):
        class_name = match.group(1)
        class_code = match.group(0)
        relevant_sections[class_name] = class_code
    
    # If no Python functions found, try JavaScript patterns
    if not relevant_sections:
        for match in re.finditer(js_func_pattern, content, re.DOTALL):
            func_name = match.group(1) or match.group(2) or match.group(3)
            if func_name:
                func_code = match.group(0)
                relevant_sections[func_name] = func_code
    
    return relevant_sections


def extract_failing_functions(error_messages: List[str]) -> List[str]:
    """Extract function names from error messages.
    
    Args:
        error_messages: List of error messages
        
    Returns:
        List of function names that are failing
    """
    failing_functions = []
    
    for error_msg in error_messages:
        # Extract function names from common error patterns
        patterns = [
            r'in ([a-zA-Z_][a-zA-Z0-9_]*)\(',
            r'function ([a-zA-Z_][a-zA-Z0-9_]*)',
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, error_msg)
            failing_functions.extend(matches)
    
    return list(set(failing_functions))


def extract_line_numbers(error_messages: List[str]) -> List[int]:
    """Extract line numbers from error messages.
    
    Args:
        error_messages: List of error messages
        
    Returns:
        List of line numbers mentioned in errors
    """
    line_numbers = []
    
    for error_msg in error_messages:
        # Extract line numbers from common patterns
        patterns = [
            r'line (\d+)',
            r':(\d+):',
            r'at line (\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, error_msg)
            line_numbers.extend([int(line) for line in matches])
    
    return list(set(line_numbers))


def extract_error_types(error_messages: List[str]) -> List[str]:
    """Extract error types from error messages.
    
    Args:
        error_messages: List of error messages
        
    Returns:
        List of error types found in messages
    """
    error_types = []
    
    for error_msg in error_messages:
        # Extract error types from common patterns
        patterns = [
            r'(TypeError|AttributeError|ValueError|IndexError|KeyError|NameError|SyntaxError|ImportError):',
            r'([A-Z][a-zA-Z]*Error):',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, error_msg)
            error_types.extend(matches)
    
    return list(set(error_types))


def get_code_context(content: str, line_number: int, context_lines: int = 5) -> str:
    """Get code context around a specific line number.
    
    Args:
        content: Source code content
        line_number: The line number to get context around
        context_lines: Number of lines before and after to include
        
    Returns:
        Code context as a string
    """
    lines = content.split('\n')
    
    start_line = max(0, line_number - context_lines - 1)
    end_line = min(len(lines), line_number + context_lines)
    
    context_lines_list = lines[start_line:end_line]
    
    # Add line numbers for clarity
    numbered_context = []
    for i, line in enumerate(context_lines_list, start_line + 1):
        marker = ">>> " if i == line_number else "    "
        numbered_context.append(f"{marker}{i:3d}: {line}")
    
    return '\n'.join(numbered_context)


def extract_test_names(error_messages: List[str]) -> List[str]:
    """Extract test names from error messages.
    
    Args:
        error_messages: List of error messages
        
    Returns:
        List of test names found in error messages
    """
    test_names = []
    
    for error_msg in error_messages:
        # Extract test names from common patterns
        patterns = [
            r'test_[a-zA-Z_][a-zA-Z0-9_]*',
            r'Test[A-Z][a-zA-Z0-9_]*',
            r'it\([\'"]([^\'"]+)[\'"]',
            r'describe\([\'"]([^\'"]+)[\'"]',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, error_msg)
            test_names.extend(matches)
    
    return list(set(test_names))


def create_surgical_context(file_content: str, error_messages: List[str], agent_config: Dict = None) -> Dict[str, any]:
    """Create surgical context for code fixing.
    
    Args:
        file_content: Source code content
        error_messages: List of error messages
        agent_config: Optional agent configuration for targeted extraction
        
    Returns:
        Dictionary containing surgical context
    """
    # Extract various components
    failing_functions = extract_failing_functions(error_messages)
    line_numbers = extract_line_numbers(error_messages)
    error_types = extract_error_types(error_messages)
    test_names = extract_test_names(error_messages)
    relevant_sections = extract_relevant_functions(file_content, agent_config=agent_config)
    
    # Get code context for failing lines
    code_contexts = {}
    for line_num in line_numbers:
        code_contexts[line_num] = get_code_context(file_content, line_num)
    
    return {
        'failing_functions': failing_functions,
        'failing_lines': line_numbers,
        'error_types': error_types,
        'test_names': test_names,
        'relevant_sections': relevant_sections,
        'code_contexts': code_contexts,
        'error_messages': error_messages
    } 