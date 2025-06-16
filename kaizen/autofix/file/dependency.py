import os
import ast
import logging
import importlib
from typing import Set, Dict, List, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def collect_referenced_files(file_path: str, processed_files: set = None, base_dir: str = None, 
                           failure_data: List[Dict] = None, llm_checked_files: set = None,
                           patterns: Optional[Dict] = None) -> set:
    """
    Recursively collect all Python files referenced by imports in the given file.
    Also uses heuristics and LLM to check if files might be relevant for fixes even if not directly imported.
    
    Args:
        file_path: Path to the main file
        processed_files: Set of already processed files to avoid cycles
        base_dir: Base directory for resolving relative imports
        failure_data: List of test failures to check relevance against
        llm_checked_files: Set of files that have already been checked by LLM
        patterns: Configuration for file pattern matching
        
    Returns:
        set: Set of all referenced file paths
    """
    if processed_files is None:
        processed_files = set()
    if llm_checked_files is None:
        llm_checked_files = set()
    
    if file_path in processed_files:
        return processed_files
    
    processed_files.add(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse the file to find imports
        tree = ast.parse(content)
        
        # Get the directory of the current file for relative imports
        file_dir = os.path.dirname(os.path.abspath(file_path))
        if base_dir is None:
            base_dir = file_dir
        
        # Collect all Python files in the same directory
        dir_python_files = {
            os.path.join(file_dir, f) for f in os.listdir(file_dir)
            if f.endswith('.py') and f != os.path.basename(file_path)
        }
        
        # Find all imports
        imported_files = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        module_name = name.name
                        try:
                            spec = importlib.util.find_spec(module_name)
                            if spec is not None and spec.origin is not None and spec.origin.endswith('.py'):
                                imported_files.add(spec.origin)
                        except (ImportError, ValueError) as e:
                            logger.warning(f"Failed to find module {module_name}: {str(e)}")
                else:  # ImportFrom
                    if node.module:
                        try:
                            module_name = (f"{os.path.basename(file_dir)}.{node.module}" 
                                        if node.level > 0 else node.module)
                            spec = importlib.util.find_spec(module_name)
                            if spec is not None and spec.origin is not None and spec.origin.endswith('.py'):
                                imported_files.add(spec.origin)
                        except (ImportError, ValueError) as e:
                            logger.warning(f"Failed to find module {module_name}: {str(e)}")
        
        # Process all collected files
        for imported_file in imported_files:
            if imported_file not in processed_files:
                collect_referenced_files(imported_file, processed_files, base_dir, 
                                      failure_data, llm_checked_files, patterns)
    
    except Exception as e:
        logger.warning(f"Error processing imports in {file_path}: {str(e)}")
    
    return processed_files

def map_modules(file_paths: set) -> Dict[str, str]:
    """
    Create a mapping of module names to file paths.
    
    Args:
        file_paths: Set of file paths to map
        
    Returns:
        Dict mapping module names to file paths
    """
    module_to_file = {}
    for file_path in file_paths:
        path = Path(file_path)
        # Map the module name (filename without extension)
        module_name = path.stem
        module_to_file[module_name] = file_path
        
        # Map package paths (without .py suffix)
        package_parts = path.with_suffix("").parts
        for i in range(len(package_parts)):
            module_name = '.'.join(package_parts[i:])
            module_to_file[module_name] = file_path
            
    return module_to_file

def analyze_failure_dependencies(failure_data: List[Dict], referenced_files: set) -> Dict[str, List[Dict]]:
    """
    Analyze test failures to determine which files need to be fixed.
    
    Args:
        failure_data: List of test failures
        referenced_files: Set of referenced files
        
    Returns:
        Dict mapping file paths to lists of failures that affect them
    """
    file_failures = {file_path: [] for file_path in referenced_files}
    
    # Create module mapping
    module_to_file = map_modules(referenced_files)
    
    for failure in failure_data:
        # Create error context
        error_context = {
            'error_message': failure.get('error_message', ''),
            'test_name': failure.get('test_name', ''),
            'output': failure.get('output', ''),
            'region': failure.get('region', ''),
            'details': failure.get('details', ''),
            'raw_failure': failure
        }
        
        # Skip if we have no useful information
        if not any([error_context['error_message'], error_context['test_name'], 
                   error_context['output'], error_context['details']]):
            logger.warning(f"Skipping failure with no useful information: {failure}")
            continue
        
        # Match failure to affected files
        affected_files = match_failure(failure, module_to_file, referenced_files)
        
        # Add the failure to all affected files
        for file_path in affected_files:
            file_failures[file_path].append({
                **failure,
                'error_context': error_context
            })
            logger.info(f"Added failure to {os.path.basename(file_path)} with context: {error_context}")
    
    return file_failures

def match_failure(failure: Dict, module_to_file: Dict[str, str], referenced_files: set) -> set:
    """
    Match a failure to affected files based on error context.
    
    Args:
        failure: Test failure data
        module_to_file: Mapping of module names to file paths
        referenced_files: Set of all referenced files
        
    Returns:
        Set of affected file paths
    """
    affected_files = set()
    
    # Extract failure information
    error_message = failure.get('error_message', '')
    test_name = failure.get('test_name', '')
    output = failure.get('output', '')
    region = failure.get('region', '')
    details = failure.get('details', '')
    
    # Check error message for module references
    if error_message:
        for module_name, file_path in module_to_file.items():
            if module_name in error_message:
                affected_files.add(file_path)
                logger.info(f"Found module {module_name} in error message: {error_message}")
    
    # Check test name for module references
    if test_name:
        for module_name, file_path in module_to_file.items():
            if module_name in test_name:
                affected_files.add(file_path)
                logger.info(f"Found module {module_name} in test name: {test_name}")
    
    # Check output for module references
    if output:
        for module_name, file_path in module_to_file.items():
            if module_name in output:
                affected_files.add(file_path)
                logger.info(f"Found module {module_name} in output: {output}")
    
    # Check details for module references
    if details:
        for module_name, file_path in module_to_file.items():
            if module_name in details:
                affected_files.add(file_path)
                logger.info(f"Found module {module_name} in details: {details}")
    
    # Check region information
    if region:
        for file_path in referenced_files:
            if region in file_path:
                affected_files.add(file_path)
                logger.info(f"Found region {region} in file path: {file_path}")
    
    # If no files were matched, try to infer from the test name
    if not affected_files and test_name:
        test_parts = test_name.split('.')
        for i in range(len(test_parts)):
            module_name = '.'.join(test_parts[:i+1])
            if module_name in module_to_file:
                affected_files.add(module_to_file[module_name])
                logger.info(f"Inferred module {module_name} from test name: {test_name}")
    
    # If still no files were matched, add to all referenced files
    if not affected_files:
        logger.warning("No specific files matched for failure, adding to all referenced files")
        affected_files = referenced_files
    
    return affected_files 