import os
import ast
import logging
import importlib
from typing import Set, Dict, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ImportError:
    """Represents an error during import processing."""
    module_name: str
    error_message: str
    file_path: Path

def collect_referenced_files(
    file_path: Union[str, Path],
    processed_files: Optional[Set[Path]] = None,
    base_dir: Optional[Union[str, Path]] = None,
    failure_data: Optional[List[Dict]] = None,
    llm_checked_files: Optional[Set[Path]] = None,
    patterns: Optional[Dict] = None
) -> Set[Path]:
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
        Set of all referenced file paths as Path objects
        
    Raises:
        FileNotFoundError: If the input file doesn't exist
        PermissionError: If there are permission issues accessing files
        ValueError: If the file path is invalid
    """
    # Initialize sets if None
    processed_files = processed_files or set()
    llm_checked_files = llm_checked_files or set()
    
    # Convert inputs to Path objects
    file_path = Path(file_path).resolve()
    base_dir = Path(base_dir).resolve() if base_dir else file_path.parent
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if file_path in processed_files:
        return processed_files
    
    processed_files.add(file_path)
    
    try:
        # Read and parse file
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
        
        # Collect Python files in the same directory
        dir_python_files = {
            f.resolve() for f in file_path.parent.glob('*.py')
            if f != file_path
        }
        
        # Find all imports
        imported_files: Set[Path] = set()
        import_errors: List[ImportError] = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                try:
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            module_name = name.name
                            spec = importlib.util.find_spec(module_name)
                            if spec and spec.origin and spec.origin.endswith('.py'):
                                imported_files.add(Path(spec.origin).resolve())
                    else:  # ImportFrom
                        if node.module:
                            module_name = (
                                f"{file_path.parent.name}.{node.module}"
                                if node.level > 0 else node.module
                            )
                            spec = importlib.util.find_spec(module_name)
                            if spec and spec.origin and spec.origin.endswith('.py'):
                                imported_files.add(Path(spec.origin).resolve())
                except (ImportError, ValueError) as e:
                    import_errors.append(ImportError(
                        module_name=module_name,
                        error_message=str(e),
                        file_path=file_path
                    ))
                    logger.warning(
                        "Failed to find module",
                        extra={
                            'module_name': module_name,
                            'error': str(e),
                            'file_path': str(file_path)
                        }
                    )
        
        # Log import errors if any
        if import_errors:
            logger.warning(
                "Import errors encountered",
                extra={
                    'file_path': str(file_path),
                    'errors': [vars(e) for e in import_errors]
                }
            )
        
        # Process all collected files
        for imported_file in imported_files:
            if imported_file not in processed_files:
                try:
                    collect_referenced_files(
                        imported_file,
                        processed_files,
                        base_dir,
                        failure_data,
                        llm_checked_files,
                        patterns
                    )
                except (FileNotFoundError, PermissionError) as e:
                    logger.error(
                        "Error processing imported file",
                        extra={
                            'file_path': str(imported_file),
                            'error': str(e),
                            'error_type': type(e).__name__
                        }
                    )
    
    except FileNotFoundError as e:
        logger.error(
            "File not found",
            extra={
                'file_path': str(file_path),
                'error': str(e)
            }
        )
        raise
    except PermissionError as e:
        logger.error(
            "Permission denied",
            extra={
                'file_path': str(file_path),
                'error': str(e)
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Unexpected error processing imports",
            extra={
                'file_path': str(file_path),
                'error': str(e),
                'error_type': type(e).__name__
            }
        )
        raise ValueError(f"Failed to process imports in {file_path}: {str(e)}")
    
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