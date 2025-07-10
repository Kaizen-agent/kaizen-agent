import ast
import os
import re
import logging
import importlib
import sys
from datetime import datetime
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

def clean_markdown_notations(code: str) -> str:
    """
    Remove markdown notations from the beginning and end of the code.
    
    Args:
        code (str): The code to clean
        
    Returns:
        str: The cleaned code
    """
    try:
        # Log the initial state with structured data
        logger.debug("Starting markdown notation cleaning", extra={
            'code_length': len(code),
            'timestamp': datetime.utcnow().isoformat(),
            'operation': 'markdown_cleaning'
        })
        
        # Remove markdown code block notations
        code = re.sub(r'^```(?:python)?\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'\s*```$', '', code, flags=re.MULTILINE)
        
        # Remove any remaining markdown formatting
        code = re.sub(r'^#+\s*', '', code, flags=re.MULTILINE)  # Remove headers
        code = re.sub(r'\*\*(.*?)\*\*', r'\1', code)  # Remove bold
        code = re.sub(r'\*(.*?)\*', r'\1', code)  # Remove italic
        code = re.sub(r'`(.*?)`', r'\1', code)  # Remove inline code
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        # Log the final state with structured data
        logger.debug("Completed markdown notation cleaning", extra={
            'cleaned_code_length': len(code),
            'timestamp': datetime.utcnow().isoformat(),
            'operation': 'markdown_cleaning',
            'changes_made': {
                'code_blocks_removed': bool(re.search(r'```', code)),
                'headers_removed': bool(re.search(r'^#+\s*', code, re.MULTILINE)),
                'formatting_removed': bool(re.search(r'\*\*|\*|`', code))
            }
        })
        
        return code
        
    except Exception as e:
        error_context = {
            'original_code_length': len(code),
            'timestamp': datetime.utcnow().isoformat(),
            'operation': 'markdown_cleaning'
        }
        logger.error("Error in markdown notation cleaning", extra={
            'error': str(e),
            'context': error_context
        })
        raise

def fix_common_syntax_issues(code: str) -> str:
    """
    Fix common syntax issues in the code.
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: The fixed code
    """
    try:
        # Log the initial state
        logger.debug("Starting common syntax fixes", extra={
            'code_length': len(code)
        })
        
        # First clean any markdown notations
        code = clean_markdown_notations(code)
        
        # Fix unclosed strings with more robust pattern
        # Handle both single and double quotes
        code = re.sub(
            r'([\'"])((?:[^\'"]|\\[\'"])*?)(?:\n|$)', 
            lambda m: m.group(1) + m.group(2) + m.group(1), 
            code
        )
        
        # Fix triple-quoted strings
        code = re.sub(
            r'(\'\'\'|\"\"\")((?:[^\'"]|\\[\'"])*?)(?:\n|$)', 
            lambda m: m.group(1) + m.group(2) + m.group(1), 
            code
        )
        
        # Fix missing colons after control structures with better pattern
        code = re.sub(
            r'(if|for|while|def|class|elif|else)\s+(?!:)([^:]+?)(?:\n|$)',
            r'\1 \2: ',
            code
        )
        
        # Fix missing parentheses in function calls with better pattern
        code = re.sub(
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s+(?=[a-zA-Z_][a-zA-Z0-9_]*(?:\s*\(|\s*\[|\s*\.|$))',
            r'\1(',
            code
        )
        
        # Fix indentation with better handling of nested structures
        lines = code.split('\n')
        fixed_lines = []
        current_indent = 0
        indent_stack = []
        bracket_stack = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                fixed_lines.append('')
                continue
            
            # Count brackets to track nesting
            for char in stripped:
                if char in '([{':
                    bracket_stack.append(char)
                elif char in ')]}':
                    if bracket_stack:
                        bracket_stack.pop()
            
            # Handle dedent keywords
            if stripped.startswith(('else:', 'elif', 'except', 'finally:')):
                if indent_stack:
                    current_indent = indent_stack[-1]
            elif stripped.startswith(('return', 'break', 'continue', 'pass')):
                if indent_stack:
                    current_indent = indent_stack.pop()
            
            # Apply current indentation
            fixed_lines.append('    ' * current_indent + stripped)
            
            # Handle indent increase
            if stripped.endswith(':'):
                indent_stack.append(current_indent)
                current_indent += 1
        
        fixed_code = '\n'.join(fixed_lines)
        
        # Log the final state
        logger.debug("Completed common syntax fixes", extra={
            'fixed_code_length': len(fixed_code)
        })
        
        return fixed_code
        
    except Exception as e:
        logger.error(f"Error in common syntax fixes: {str(e)}")
        return code  # Return original code if fixes fail

def fix_aggressive_syntax_issues(code: str) -> str:
    """
    Apply more aggressive syntax fixes when common fixes fail.
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: The fixed code
    """
    try:
        # Log the initial state
        logger.debug("Starting aggressive syntax fixes", extra={
            'code_length': len(code)
        })
        
        # Remove any non-printable characters except newlines
        code = ''.join(char for char in code if char.isprintable() or char == '\n')
        
        # Fix common string issues with more robust patterns
        code = re.sub(
            r'([\'"])((?:[^\'"]|\\[\'"])*?)(?:\n|$)',
            lambda m: m.group(1) + m.group(2) + m.group(1),
            code
        )
        
        # Fix missing parentheses and brackets with better patterns
        code = re.sub(
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s+(?=[a-zA-Z_][a-zA-Z0-9_]*(?:\s*\(|\s*\[|\s*\.|$))',
            r'\1(',
            code
        )
        code = re.sub(
            r'(\[)((?:[^\[\]]|\\[\[\]])*?)(?:\n|$)',
            lambda m: m.group(1) + m.group(2) + ']',
            code
        )
        code = re.sub(
            r'(\{)((?:[^{}]|\\[{}])*?)(?:\n|$)',
            lambda m: m.group(1) + m.group(2) + '}',
            code
        )
        
        # Fix indentation with better handling of nested structures
        lines = code.split('\n')
        fixed_lines = []
        current_indent = 0
        indent_stack = []
        bracket_stack = []
        
        for line in lines:
            stripped = line.strip()
            
            # Count brackets to track nesting
            for char in stripped:
                if char in '([{':
                    bracket_stack.append(char)
                elif char in ')]}':
                    if bracket_stack:
                        bracket_stack.pop()
            
            # Handle indentation changes
            if stripped.endswith(':'):
                fixed_lines.append('    ' * current_indent + stripped)
                indent_stack.append(current_indent)
                current_indent += 1
            elif stripped.startswith(('return', 'break', 'continue', 'pass')):
                if indent_stack:
                    current_indent = indent_stack.pop()
                fixed_lines.append('    ' * current_indent + stripped)
            elif stripped.startswith(('else:', 'elif ', 'except ', 'finally:')):
                if indent_stack:
                    current_indent = indent_stack[-1]
                fixed_lines.append('    ' * current_indent + stripped)
            else:
                fixed_lines.append('    ' * current_indent + stripped)
        
        fixed_code = '\n'.join(fixed_lines)
        
        # Log the final state
        logger.debug("Completed aggressive syntax fixes", extra={
            'fixed_code_length': len(fixed_code)
        })
        
        return fixed_code
        
    except Exception as e:
        logger.error(f"Error in aggressive syntax fixes: {str(e)}")
        return code  # Return original code if fixes fail

def fix_specific_syntax_error(code: str, error_msg: str) -> str:
    """
    Fix specific syntax errors based on the error message.
    
    Args:
        code (str): The code to fix
        error_msg (str): The syntax error message
        
    Returns:
        str: The fixed code
    """
    try:
        # Log the initial state
        logger.debug("Starting specific syntax error fix", extra={
            'error_message': error_msg,
            'code_length': len(code)
        })
        
        if "EOL while scanning string literal" in error_msg:
            # Extract line number from error message
            line_match = re.search(r'line (\d+)', error_msg)
            if line_match:
                line_num = int(line_match.group(1))
                lines = code.split('\n')
                if line_num <= len(lines):
                    # Fix unclosed string on the specified line
                    line = lines[line_num - 1]
                    if line.count('"') % 2 == 1:
                        lines[line_num - 1] = line + '"'
                    elif line.count("'") % 2 == 1:
                        lines[line_num - 1] = line + "'"
                return '\n'.join(lines)
        
        elif "unexpected EOF while parsing" in error_msg:
            # Try to fix common EOF issues
            if code.strip().endswith('('):
                return code + ')'
            elif code.strip().endswith('['):
                return code + ']'
            elif code.strip().endswith('{'):
                return code + '}'
            elif code.strip().endswith(':'):
                return code + '\n    pass'
        
        elif "invalid syntax" in error_msg:
            # Try to fix common invalid syntax issues
            if ':' in error_msg and 'expected' in error_msg:
                # Missing colon after control structure
                lines = code.split('\n')
                line_match = re.search(r'line (\d+)', error_msg)
                if line_match:
                    line_num = int(line_match.group(1))
                    if line_num <= len(lines):
                        line = lines[line_num - 1]
                        if any(keyword in line for keyword in ['if', 'for', 'while', 'def', 'class']):
                            lines[line_num - 1] = line + ':'
                return '\n'.join(lines)
        
        # Log the final state
        logger.debug("Completed specific syntax error fix", extra={
            'fixed_code_length': len(code)
        })
        
        return code
        
    except Exception as e:
        logger.error(f"Error in specific syntax error fix: {str(e)}")
        return code  # Return original code if fixes fail

    # Topological sort to determine reload order
    def topological_sort(graph):
        visited = set()
        temp = set()
        order = []
        
        def visit(node):
            if node in temp:
                # Circular dependency detected
                logger.warning(f"Circular dependency detected involving {node}")
                return
            if node in visited:
                return
            temp.add(node)
            for neighbor in graph.get(node, set()):
                visit(neighbor)
            temp.remove(node)
            visited.add(node)
            order.append(node)
        
        for node in graph:
            if node not in visited:
                visit(node)
        
        return order
    
    # Get reload order
    reload_order = topological_sort(dependency_graph)
    
    # Reload modules in order
    for module_name in reversed(reload_order):  # Reverse to handle dependencies first
        try:
            if module_name in sys.modules:
                # Get the module's file path
                module = sys.modules[module_name]
                if hasattr(module, '__file__') and module.__file__:
                    # Check if the file has been modified
                    file_path = module.__file__
                    if os.path.exists(file_path):
                        # Force reload by removing from sys.modules
                        del sys.modules[module_name]
                        # Import and reload
                        module = importlib.import_module(module_name)
                        importlib.reload(module)
                        logger.info(f"Reloaded module: {module_name}")
            else:
                # Try to import the module
                try:
                    module = importlib.import_module(module_name)
                    importlib.reload(module)
                    logger.info(f"Imported and reloaded module: {module_name}")
                except ImportError as e:
                    logger.warning(f"Failed to import module {module_name}: {str(e)}")
        except Exception as e:
            logger.warning(f"Error reloading module {module_name}: {str(e)}")
    
    # Clear any cached instances
    for module_name in reload_order:
        if module_name in sys.modules:
            module = sys.modules[module_name]
            # Clear any cached instances in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, '__dict__'):
                    # Clear instance caches if they exist
                    if hasattr(attr, '_instance'):
                        delattr(attr, '_instance')
                    if hasattr(attr, '_instances'):
                        delattr(attr, '_instances')

def apply_code_changes(current_file_path: str, fixed_codes: str) -> None:
    """
    Apply code changes to a single file and ensure they are properly reflected in the running system.
    
    Args:
        current_file_path (str): Path to the file to be modified
        fixed_codes (str): The fixed code content to write to the file
    """
    try:
        # First, write changes to disk
        try:
            with open(current_file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_codes)
            logger.info(f"Written changes to {current_file_path}")
        except Exception as e:
            logger.error(f"Failed to write changes to {current_file_path}: {str(e)}")
            raise
        
        # Verify changes were applied
        try:
            with open(current_file_path, 'r', encoding='utf-8') as f:
                current_code = f.read()
            if current_code != fixed_codes:
                logger.error(f"Changes not properly applied to {current_file_path}")
                raise ValueError(f"Changes not properly applied to {current_file_path}")
        except Exception as e:
            logger.error(f"Failed to verify changes in {current_file_path}: {str(e)}")
            raise
        
        logger.info("Code changes successfully applied and verified")
        
    except Exception as e:
        logger.error(f"Failed to apply code changes: {str(e)}")
        raise 