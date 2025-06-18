import os
import ast
import logging
import importlib
import json
from typing import Any, Set, Dict, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from difflib import SequenceMatcher
import google.generativeai as genai

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
    failure_data: Optional[List[Dict[str, Any]]] = None,
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
    logger.info(f"Collecting referenced files for {file_path}")
    # Initialize sets if None
    processed_files = processed_files or set()
    llm_checked_files = llm_checked_files or set()
    logger.info(f"Processed files: {processed_files}")
    logger.info(f"LLM checked files: {llm_checked_files}")
    # Convert inputs to Path objects
    file_path = Path(file_path).resolve()
    base_dir = Path(base_dir).resolve() if base_dir else file_path.parent
    logger.info(f"Base directory: {base_dir}")
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if file_path in processed_files:
        logger.info(f"File {file_path} already processed")
        return processed_files
    
    logger.info(f"Adding {file_path} to processed files")
    processed_files.add(file_path)
    logger.info(f"Processed files: {processed_files}")
    try:
        logger.info(f"Reading and parsing file {file_path}")
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
        logger.info(f"Finding all imports in {file_path}")
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
        logger.info(f"Imported files: {imported_files}")
        logger.info(f"Heuristic: Finding relevant files for {file_path}")
        # Heuristic: Add relevant files based on filename similarity and failure data
        heuristic_files = find_heuristic_relevant_files(file_path, base_dir, processed_files, failure_data)
        for hf in heuristic_files:
            if hf not in processed_files:
                logger.info(f"Heuristic: Adding relevant file {hf}")
                processed_files.add(hf)
        # LLM: Add relevant files suggested by LLM
        if file_path not in llm_checked_files:
            llm_files = find_llm_relevant_files(file_path, base_dir, processed_files, llm_checked_files, failure_data, patterns)
            for lf in llm_files:
                if lf not in processed_files:
                    logger.info(f"LLM: Adding relevant file {lf}")
                    processed_files.add(lf)
            llm_checked_files.add(file_path)
        
        # Process all collected files (including heuristic and LLM additions)
        for imported_file in imported_files.union(heuristic_files):
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

def find_heuristic_relevant_files(file_path: Path, base_dir: Path, processed_files: Set[Path], failure_data: Optional[List[Dict]]) -> Set[Path]:
    """
    Heuristically find relevant files in the same directory or project based on filename similarity, common suffixes, and failure data.
    - Looks for files with similar names or common suffixes (e.g., _utils, _helper).
    - Looks for files mentioned in failure data (by name or module).
    - Searches subdirectories if project is larger.
    """
    relevant_files = set()
    common_suffixes = ['_utils', '_helper', '_helpers', '_base', '_core']
    # 1. Filename similarity and common suffixes in the same directory
    for f in base_dir.glob('*.py'):
        if f not in processed_files and f != file_path:
            ratio = SequenceMatcher(None, file_path.stem, f.stem).ratio()
            if ratio > 0.7:
                relevant_files.add(f.resolve())
            for suffix in common_suffixes:
                if file_path.stem + suffix == f.stem or f.stem + suffix == file_path.stem:
                    relevant_files.add(f.resolve())
    # 2. Failure data matching (file/module names)
    if failure_data:
        for failure in failure_data:
            for key in ['error_message', 'test_name', 'output', 'details', 'region']:
                val = failure.get(key, '')
                if not val:
                    continue
                # Check for file/module names in the value
                for f in base_dir.glob('*.py'):
                    if f not in processed_files and f != file_path:
                        if f.stem in val or f.name in val:
                            relevant_files.add(f.resolve())
                # Also check subdirectories (one level deep)
                for subdir in base_dir.iterdir():
                    if subdir.is_dir():
                        for f in subdir.glob('*.py'):
                            if f not in processed_files and f != file_path:
                                if f.stem in val or f.name in val:
                                    relevant_files.add(f.resolve())
    # 3. Neighbor files in the same package (if __init__.py exists)
    if (base_dir / '__init__.py').exists():
        for f in base_dir.glob('*.py'):
            if f not in processed_files and f != file_path:
                relevant_files.add(f.resolve())
    return relevant_files

def find_llm_relevant_files(file_path: Path, base_dir: Path, processed_files: Set[Path], llm_checked_files: Set[Path], failure_data: Optional[List[Dict]], patterns: Optional[Dict]) -> Set[Path]:
    """
    Use an LLM to suggest additional relevant files for fixes.
    
    Args:
        file_path: Path to the file being analyzed
        base_dir: Base directory for resolving relative imports
        processed_files: Set of already processed files to avoid cycles
        llm_checked_files: Set of files that have already been checked by LLM
        failure_data: List of test failures to check relevance against
        patterns: Configuration for file pattern matching
        
    Returns:
        Set of Path objects for relevant files that exist in the project
    """
    logger.info(f"Starting LLM file suggestion for {file_path}")
    logger.debug(f"Base directory: {base_dir}")
    logger.debug(f"Number of processed files: {len(processed_files)}")
    logger.debug(f"Number of LLM checked files: {len(llm_checked_files)}")
    
    try:
        # Read the file content
        content = file_path.read_text(encoding='utf-8')
        logger.debug(f"Successfully read file content ({len(content)} characters)")
        
        # Prepare the prompt for the LLM
        prompt = f"""Analyze the following Python file and suggest other relevant files that might need to be modified together.
        Consider:
        1. Related functionality
        2. Common dependencies
        3. Test failures if provided
        4. Code patterns and conventions
        
        File path: {file_path}
        File content:
        ```python
        {content}
        ```
        
        """
        
        if failure_data:
            prompt += f"\nTest failures:\n{json.dumps(failure_data, indent=2)}\n"
            logger.debug(f"Included {len(failure_data)} test failures in prompt")
        
        if patterns:
            prompt += f"\nCode patterns:\n{json.dumps(patterns, indent=2)}\n"
            logger.debug("Included code patterns in prompt")
        
        prompt += """
        Return ONLY a JSON array of file paths that are relevant for fixes, relative to the base directory.
        Example format:
        ["path/to/file1.py", "path/to/file2.py"]
        """
        
        # Initialize Gemini model
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found, skipping LLM file suggestion")
            return set()
            
        logger.info("Initializing Gemini model")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Get response from Gemini
        logger.info("Sending prompt to Gemini model")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Low temperature for more focused results
                max_output_tokens=1024,
                top_p=0.8,
                top_k=40,
            )
        )
        logger.debug("Received response from Gemini model")
        
        # Parse the response
        try:
            suggested_files = json.loads(response.text)
            logger.info(f"Successfully parsed LLM response: {len(suggested_files)} files suggested")
            logger.debug(f"Suggested files: {suggested_files}")
            
            # Convert to absolute paths and filter for existing files
            relevant_files = {
                (base_dir / Path(f)).resolve()
                for f in suggested_files
                if (base_dir / Path(f)).exists()
            }
            
            logger.info(f"Found {len(relevant_files)} existing relevant files")
            logger.debug(f"Relevant files: {[str(f) for f in relevant_files]}")
            return relevant_files
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response as JSON: {response.text}")
            return set()
            
    except Exception as e:
        logger.error(f"Error in LLM file suggestion: {str(e)}", exc_info=True)
        return set() 