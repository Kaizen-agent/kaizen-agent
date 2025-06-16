import os
import uuid
from typing import List, Dict, Tuple, Optional, Set, Pattern
import subprocess
from pathlib import Path
import google.generativeai as genai
from github import Github
from github.GithubException import GithubException
from datetime import datetime
import json
import yaml
import sys
from rich.console import Console
import ast
import importlib
import random
from dataclasses import dataclass
import re
import time

from .logger import get_logger
from .config import get_config
from .runner import TestRunner
from .logger import TestLogger

logger = get_logger(__name__)
console = Console()

@dataclass
class FilePatterns:
    """Configuration for file pattern matching."""
    prompt_patterns: List[str] = None
    utils_patterns: List[str] = None
    config_patterns: List[str] = None
    agent_patterns: List[str] = None
    common_words: Set[str] = None
    
    def __post_init__(self):
        """Initialize default patterns if not provided."""
        self.prompt_patterns = self.prompt_patterns or ['prompt', 'instruction', 'guideline', 'template']
        self.utils_patterns = self.utils_patterns or ['utils', 'utility', 'helper', 'common']
        self.config_patterns = self.config_patterns or ['config', 'setting', 'parameter', 'option']
        self.agent_patterns = self.agent_patterns or ['agent', 'assistant', 'bot', 'model']
        self.common_words = self.common_words or {
            'test', 'error', 'failed', 'failure', 'assert', 'check', 'verify', 'validate',
            'should', 'must', 'need', 'have', 'with', 'from', 'that', 'this', 'when'
        }

@dataclass
class PromptDetectionConfig:
    """Configuration for prompt detection."""
    # Scoring weights for different types of patterns
    system_message_weight: float = 0.8
    user_message_weight: float = 0.8
    assistant_message_weight: float = 0.8
    general_prompt_weight: float = 0.6
    chat_array_weight: float = 0.7
    
    # Context scoring weights
    prompt_content_weight: float = 1.0
    input_output_weight: float = 0.5
    structured_pattern_weight: float = 0.8
    nested_pattern_weight: float = 0.9
    multiline_weight: float = 0.3
    formatting_weight: float = 0.2
    numbered_list_weight: float = 0.2
    
    # False positive reduction weights
    test_file_weight: float = 0.5
    config_file_weight: float = 0.5
    utility_file_weight: float = 0.5
    
    # Thresholds
    min_prompt_score: float = 0.6
    min_context_score: float = 0.3
    
    # Cache settings
    cache_size: int = 1000
    cache_ttl: int = 3600  # 1 hour in seconds

class PromptDetector:
    """A class for detecting prompts in code files."""
    
    def __init__(self, config: Optional[PromptDetectionConfig] = None):
        """
        Initialize the prompt detector.
        
        Args:
            config: Optional configuration for prompt detection
        """
        self.config = config or PromptDetectionConfig()
        self._cache = {}
        self._cache_timestamps = {}
        
    def _get_cache_key(self, file_path: str, content: str) -> str:
        """Generate a cache key for the file content."""
        return f"{file_path}:{hash(content)}"
        
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if the cached result is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[cache_key] < self.config.cache_ttl
        
    def _update_cache(self, cache_key: str, result: Tuple[bool, Optional[str]]):
        """Update the cache with a new result."""
        # Remove oldest entry if cache is full
        if len(self._cache) >= self.config.cache_size:
            oldest_key = min(self._cache_timestamps.items(), key=lambda x: x[1])[0]
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
            
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
        
    def detect_prompt(self, file_path: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if a file contains prompts by analyzing its content.
        
        Args:
            file_path: Path to the file to analyze
            content: The content of the file
            
        Returns:
            Tuple[bool, Optional[str]]: (contains_prompt, error_message)
            
        Examples:
            >>> detector = PromptDetector()
            >>> detector.detect_prompt("prompt.py", 'system_message = "You are a helpful assistant"')
            (True, None)
            >>> detector.detect_prompt("utils.py", 'def helper(): pass')
            (False, None)
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(file_path, content)
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
                
            if not content.strip():
                return False, "File is empty"
                
            # Initialize scoring
            prompt_score = 0.0
            context_score = 0.0
            
            # Check for prompt patterns with context
            content_lower = content.lower()
            
            # System message patterns
            system_patterns = [
                (r'system_message\s*=\s*[\'"](.*?)[\'"]', self.config.system_message_weight),
                (r'system_prompt\s*=\s*[\'"](.*?)[\'"]', self.config.system_message_weight),
                (r'role\s*:\s*[\'"]system[\'"]', self.config.system_message_weight * 0.9)
            ]
            
            # User message patterns
            user_patterns = [
                (r'user_message\s*=\s*[\'"](.*?)[\'"]', self.config.user_message_weight),
                (r'user_prompt\s*=\s*[\'"](.*?)[\'"]', self.config.user_message_weight),
                (r'role\s*:\s*[\'"]user[\'"]', self.config.user_message_weight * 0.9)
            ]
            
            # Assistant message patterns
            assistant_patterns = [
                (r'assistant_message\s*=\s*[\'"](.*?)[\'"]', self.config.assistant_message_weight),
                (r'assistant_prompt\s*=\s*[\'"](.*?)[\'"]', self.config.assistant_message_weight),
                (r'role\s*:\s*[\'"]assistant[\'"]', self.config.assistant_message_weight * 0.9)
            ]
            
            # General prompt patterns
            general_patterns = [
                (r'prompt\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight),
                (r'instruction\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight),
                (r'guideline\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight),
                (r'template\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight)
            ]
            
            # Chat/message array patterns
            chat_patterns = [
                (r'messages\s*=\s*\[', self.config.chat_array_weight),
                (r'chat\s*=\s*\[', self.config.chat_array_weight),
                (r'conversation\s*=\s*\[', self.config.chat_array_weight)
            ]
            
            # Combine all patterns
            all_patterns = (
                system_patterns + 
                user_patterns + 
                assistant_patterns + 
                general_patterns + 
                chat_patterns
            )
            
            # Check patterns and calculate scores
            for pattern, weight in all_patterns:
                matches = re.finditer(pattern, content_lower)
                for match in matches:
                    # Get context around the match
                    start = max(0, match.start() - 50)
                    end = min(len(content_lower), match.end() + 50)
                    context = content_lower[start:end]
                    
                    # Calculate context score
                    if any(keyword in context for keyword in ['you are', 'your task', 'please', 'should', 'must', 'need to']):
                        context_score += self.config.prompt_content_weight
                    elif any(keyword in context for keyword in ['input', 'output', 'format', 'response', 'result']):
                        context_score += self.config.input_output_weight
                    
                    # Check for structured patterns
                    if re.search(r'\{.*?role.*?content.*?\}', context):
                        context_score += self.config.structured_pattern_weight
                    elif re.search(r'\[.*?\{.*?role.*?content.*?\}.*?\]', context):
                        context_score += self.config.nested_pattern_weight
                    
                    # Check for formatting
                    if '\n' in match.group(0):
                        context_score += self.config.multiline_weight
                    if re.search(r'[#*\-]\s+[A-Z]', context):
                        context_score += self.config.formatting_weight
                    if re.search(r'\d+\.\s+[A-Z]', context):
                        context_score += self.config.numbered_list_weight
                    
                    # Add to prompt score
                    prompt_score += weight
            
            # Check for false positives
            if prompt_score >= self.config.min_prompt_score:
                # Check if the file is likely a test file
                if any(keyword in content_lower for keyword in ['test_', 'test_', 'unittest', 'pytest']):
                    prompt_score *= self.config.test_file_weight
                # Check if the file is likely a configuration file
                if any(keyword in content_lower for keyword in ['config', 'settings', 'options']):
                    prompt_score *= self.config.config_file_weight
                # Check if the file is likely a utility file
                if any(keyword in content_lower for keyword in ['utils', 'helpers', 'common']):
                    prompt_score *= self.config.utility_file_weight
            
            # Final decision
            result = (
                prompt_score >= self.config.min_prompt_score and 
                context_score >= self.config.min_context_score,
                None
            )
            
            # Update cache
            self._update_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting prompts in {file_path}: {str(e)}")
            return False, str(e)

def _compile_patterns(patterns: List[str]) -> List[Pattern]:
    """Compile regex patterns for efficient matching."""
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

def _extract_failure_keywords(failure_data: List[Dict], common_words: Set[str]) -> Set[str]:
    """Extract relevant keywords from test failures."""
    keywords = set()
    for failure in failure_data:
        test_name = failure.get('test_name', '').lower()
        error_msg = failure.get('error_message', '').lower()
        keywords.update(test_name.split())
        keywords.update(error_msg.split())
    
    return {k for k in keywords if len(k) > 2 and k not in common_words}

def _check_file_name_patterns(file_name: str, patterns: FilePatterns) -> Optional[str]:
    """Check if file name matches any critical patterns."""
    file_name_lower = file_name.lower()
    
    pattern_groups = {
        'prompt': patterns.prompt_patterns,
        'utils': patterns.utils_patterns,
        'config': patterns.config_patterns,
        'agent': patterns.agent_patterns
    }
    
    for pattern_type, pattern_list in pattern_groups.items():
        if any(pattern in file_name_lower for pattern in pattern_list):
            return pattern_type
    return None

def _check_file_content(content: str, patterns: FilePatterns, failure_keywords: Set[str]) -> Optional[str]:
    """Check if file content matches any critical patterns or failure keywords."""
    content_lower = content.lower()
    
    # Check failure keywords first
    if any(keyword in content_lower for keyword in failure_keywords):
        return 'failure_keyword'
    
    # Check critical patterns
    pattern_groups = {
        'prompt': patterns.prompt_patterns,
        'utils': patterns.utils_patterns,
        'config': patterns.config_patterns,
        'agent': patterns.agent_patterns
    }
    
    for pattern_type, pattern_list in pattern_groups.items():
        if any(pattern in content_lower for pattern in pattern_list):
            return pattern_type
    return None

def _analyze_with_llm(content: str, failure_data: List[Dict], model) -> bool:
    """Use LLM to analyze if a file is relevant for fixes."""
    try:
        prompt = f"""You are a senior software engineer specializing in AI agent development. Your task is to analyze if a Python file might be relevant for fixing test failures, even if it's not directly imported.

File Content:
{content}

Test Failures:
{chr(10).join(f'- {failure["test_name"]}: {failure["error_message"]}' for failure in failure_data)}

Please analyze if this file might be relevant for fixing any of the test failures. Consider:
1. Does it contain prompts or configurations that might need improvement?
2. Does it have functions that might be related to the failing tests?
3. Does it contain code that might be indirectly related to the failures?
4. Does it have any AI agent-specific code that might need enhancement?
5. Is it a utility or helper file that might be used by the failing tests?
6. Does it contain any shared functionality that might affect the tests?

Return only "YES" if the file is relevant, or "NO" if it's not relevant. Be conservative - if there's any chance the file might be relevant, return "YES"."""
        
        response = model.generate_content(prompt)
        return response.text.strip().upper() == "YES"
    except Exception as e:
        logger.warning(f"LLM analysis failed: {str(e)}")
        return False

def _collect_referenced_files(file_path: str, processed_files: set = None, base_dir: str = None, 
                            failure_data: List[Dict] = None, llm_checked_files: set = None,
                            patterns: FilePatterns = None) -> set:
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
    if patterns is None:
        patterns = FilePatterns()
    
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
        
        # Check file relevance if we have failure data
        if failure_data and file_path not in llm_checked_files:
            should_check_with_llm = False
            match_type = None
            
            # Check file name first
            file_name = os.path.basename(file_path)
            match_type = _check_file_name_patterns(file_name, patterns)
            if match_type:
                should_check_with_llm = True
                logger.info(f"File name matches {match_type} pattern: {file_path}")
            
            # If no match in file name, check content
            if not should_check_with_llm:
                failure_keywords = _extract_failure_keywords(failure_data, patterns.common_words)
                match_type = _check_file_content(content, patterns, failure_keywords)
                if match_type:
                    should_check_with_llm = True
                    logger.info(f"File content matches {match_type} pattern: {file_path}")
            
            # Use LLM for final verification
            if should_check_with_llm:
                try:
                    config = get_config()
                    genai.configure(api_key=config.get_api_key("google"))
                    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
                    
                    if _analyze_with_llm(content, failure_data, model):
                        logger.info(f"LLM determined file is relevant for fixes: {file_path}")
                        imported_files.update(dir_python_files)
                    
                    llm_checked_files.add(file_path)
                    
                except Exception as e:
                    logger.warning(f"Error checking file relevance with LLM: {str(e)}")
        
        # Process all collected files
        for imported_file in imported_files:
            if imported_file not in processed_files:
                _collect_referenced_files(imported_file, processed_files, base_dir, 
                                       failure_data, llm_checked_files, patterns)
    
    except Exception as e:
        logger.warning(f"Error processing imports in {file_path}: {str(e)}")
    
    return processed_files

def _map_modules(file_paths: set) -> Dict[str, str]:
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

def _match_failure(failure: Dict, module_to_file: Dict[str, str], referenced_files: set) -> set:
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

def _analyze_failure_dependencies(failure_data: List[Dict], referenced_files: set) -> Dict[str, List[Dict]]:
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
    module_to_file = _map_modules(referenced_files)
    
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
        affected_files = _match_failure(failure, module_to_file, referenced_files)
        
        # Add the failure to all affected files
        for file_path in affected_files:
            file_failures[file_path].append({
                **failure,
                'error_context': error_context
            })
            logger.info(f"Added failure to {os.path.basename(file_path)} with context: {error_context}")
    
    # Log summary of file failures
    for file_path, failures in file_failures.items():
        if failures:
            logger.info(f"File {os.path.basename(file_path)} has {len(failures)} failures:")
            for failure in failures:
                logger.info(f"  - Test: {failure.get('test_name')}")
                logger.info(f"    Error: {failure.get('error_message')}")
                logger.info(f"    Region: {failure.get('region')}")
    
    return file_failures

def _reload_modules(file_paths: set) -> None:
    """
    Reload all affected modules to ensure changes are properly reflected.
    This function handles circular dependencies and ensures proper reload order.
    
    Args:
        file_paths: Set of file paths to reload
    """
    # First, invalidate all import caches
    importlib.invalidate_caches()
    
    # Build dependency graph
    dependency_graph = {}
    for file_path in file_paths:
        try:
            abs_path = os.path.abspath(file_path)
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the file to find imports
            tree = ast.parse(content)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.update(name.name.split('.')[0] for name in node.names)
                    else:
                        imports.add(node.module.split('.')[0])
            
            # Get module name
            file_dir = os.path.dirname(abs_path)
            root_dir = file_dir
            while os.path.exists(os.path.join(root_dir, '__init__.py')):
                parent = os.path.dirname(root_dir)
                if parent == root_dir:  # Reached filesystem root
                    break
                root_dir = parent
            
            rel_path = os.path.relpath(abs_path, root_dir)
            module_name = os.path.splitext(rel_path)[0].replace(os.sep, '.')
            
            dependency_graph[module_name] = imports
            
        except Exception as e:
            logger.warning(f"Error analyzing dependencies for {file_path}: {str(e)}")
    
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

def _apply_code_changes(fixed_codes: Dict[str, str], original_codes: Dict[str, str]) -> None:
    """
    Apply code changes and ensure they are properly reflected in the running system.
    
    Args:
        fixed_codes: Dictionary mapping file paths to fixed code
        original_codes: Dictionary mapping file paths to original code
    """
    try:
        # First, write all changes to disk
        for file_path, code in fixed_codes.items():
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                logger.info(f"Written changes to {file_path}")
            except Exception as e:
                logger.error(f"Failed to write changes to {file_path}: {str(e)}")
                # Restore original code
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_codes[file_path])
                raise
        
        # Reload all affected modules
        _reload_modules(set(fixed_codes.keys()))
        
        # Verify changes were applied
        for file_path, code in fixed_codes.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_code = f.read()
                if current_code != code:
                    logger.error(f"Changes not properly applied to {file_path}")
                    # Restore original code
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(original_codes[file_path])
                    raise ValueError(f"Changes not properly applied to {file_path}")
            except Exception as e:
                logger.error(f"Failed to verify changes in {file_path}: {str(e)}")
                raise
        
        logger.info("All code changes successfully applied and verified")
        
    except Exception as e:
        logger.error(f"Failed to apply code changes: {str(e)}")
        # Restore all original code
        for file_path, code in original_codes.items():
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
            except Exception as restore_error:
                logger.error(f"Failed to restore original code in {file_path}: {str(restore_error)}")
        raise

def _validate_and_improve_code(fixed_code: str, original_code: str) -> str:
    """
    Validate and improve the fixed code to ensure it maintains the original structure
    while incorporating the necessary fixes. This function specifically handles AI agent code
    with a focus on prompt engineering and output quality.
    
    Args:
        fixed_code: The code generated by the LLM
        original_code: The original code to compare against
        
    Returns:
        str: The validated and improved code
        
    Raises:
        ValueError: If the fixed code is invalid or missing critical components
    """
    try:
        # Basic validation
        if not fixed_code or fixed_code.isspace():
            raise ValueError("Generated code is empty or whitespace only")
            
        # First pass: Try to fix common syntax issues
        fixed_code = _fix_common_syntax_issues(fixed_code)
            
        # Parse both codes to validate syntax
        try:
            fixed_tree = ast.parse(fixed_code)
            original_tree = ast.parse(original_code)
        except SyntaxError as e:
            # Second pass: Try more aggressive syntax fixing
            fixed_code = _fix_aggressive_syntax_issues(fixed_code)
            try:
                fixed_tree = ast.parse(fixed_code)
                original_tree = ast.parse(original_code)
            except SyntaxError as e:
                logger.error(f"Syntax error in code: {str(e)}")
                raise ValueError(f"Invalid syntax in code: {str(e)}")
        
        # Extract imports from both codes
        fixed_imports = []
        original_imports = []
        
        for node in ast.walk(fixed_tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                fixed_imports.append(ast.unparse(node))
                
        for node in ast.walk(original_tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                original_imports.append(ast.unparse(node))
        
        # Ensure all original imports are preserved
        missing_imports = [imp for imp in original_imports if imp not in fixed_imports]
        if missing_imports:
            # Add missing imports at the top of the file
            fixed_code = '\n'.join(missing_imports) + '\n\n' + fixed_code
        
        # Extract class and function definitions from original code
        original_defs = {}
        for node in ast.walk(original_tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                original_defs[node.name] = node
        
        # Verify all original definitions are present in fixed code
        fixed_defs = {}
        for node in ast.walk(fixed_tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                fixed_defs[node.name] = node
        
        missing_defs = [name for name in original_defs if name not in fixed_defs]
        if missing_defs:
            # If any definitions are missing, keep the original code for those
            for name in missing_defs:
                original_def = original_defs[name]
                fixed_code += '\n\n' + ast.unparse(original_def)
        
        # AI Agent-specific improvements
        try:
            # Check for prompt-related code
            prompt_nodes = []
            for node in ast.walk(fixed_tree):
                if isinstance(node, ast.Str) and any(keyword in node.s.lower() 
                    for keyword in ['prompt', 'instruction', 'guideline', 'template']):
                    prompt_nodes.append(node)
            
            # Improve prompts if found
            if prompt_nodes:
                for node in prompt_nodes:
                    # Add output format requirements if not present
                    if 'format' not in node.s.lower() and 'output' not in node.s.lower():
                        improved_prompt = node.s + "\n\nPlease format your response as follows:\n1. Clear and concise\n2. Well-structured\n3. Include all necessary details"
                        fixed_code = fixed_code.replace(node.s, improved_prompt)
            
            # Check for error handling
            error_handling_nodes = []
            for node in ast.walk(fixed_tree):
                if isinstance(node, ast.Try):
                    error_handling_nodes.append(node)
            
            # Add error handling if missing
            if not error_handling_nodes:
                # Find main processing functions
                for node in ast.walk(fixed_tree):
                    if isinstance(node, ast.FunctionDef) and 'process' in node.name.lower():
                        # Add basic error handling
                        error_handling = """
    try:
        # Your processing code here
        pass
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise ValueError(f"Failed to process input: {str(e)}")
"""
                        # Insert error handling at the start of the function
                        fixed_code = fixed_code.replace(ast.unparse(node), 
                            ast.unparse(node).replace('pass', error_handling))
            
            # Check for input validation
            validation_nodes = []
            for node in ast.walk(fixed_tree):
                if isinstance(node, ast.If) and any(keyword in ast.unparse(node).lower() 
                    for keyword in ['validate', 'check', 'verify']):
                    validation_nodes.append(node)
            
            # Add input validation if missing
            if not validation_nodes:
                for node in ast.walk(fixed_tree):
                    if isinstance(node, ast.FunctionDef) and 'process' in node.name.lower():
                        # Add basic input validation
                        validation = """
    if not input_data:
        raise ValueError("Input data cannot be empty")
    if not isinstance(input_data, (str, dict)):
        raise TypeError("Input data must be a string or dictionary")
"""
                        # Insert validation at the start of the function
                        fixed_code = fixed_code.replace(ast.unparse(node), 
                            ast.unparse(node).replace('pass', validation))
            
            # Check for logging
            logging_nodes = []
            for node in ast.walk(fixed_tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'logger':
                    logging_nodes.append(node)
            
            # Add logging if missing
            if not logging_nodes:
                for node in ast.walk(fixed_tree):
                    if isinstance(node, ast.FunctionDef) and 'process' in node.name.lower():
                        # Add basic logging
                        logging = """
    logger.info(f"Processing input: {input_data}")
    try:
        # Your processing code here
        pass
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise
    finally:
        logger.info("Processing completed")
"""
                        # Insert logging
                        fixed_code = fixed_code.replace(ast.unparse(node), 
                            ast.unparse(node).replace('pass', logging))
        
        except Exception as e:
            logger.warning(f"Failed to apply AI agent improvements: {str(e)}")
            # Continue with the basic validation
        
        # Final validation
        try:
            ast.parse(fixed_code)  # This will raise SyntaxError if invalid
        except SyntaxError as e:
            logger.error(f"Invalid syntax in final code: {str(e)}")
            # Last resort: try to fix the specific syntax error
            fixed_code = _fix_specific_syntax_error(fixed_code, str(e))
            try:
                ast.parse(fixed_code)
            except SyntaxError as e:
                raise ValueError(f"Invalid syntax in final code: {str(e)}")
        
        return fixed_code
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in code validation: {str(e)}")
        raise ValueError(f"Failed to validate code: {str(e)}")

def _fix_common_syntax_issues(code: str) -> str:
    """
    Fix common syntax issues in the code.
    
    This function handles basic syntax issues like:
    - Unclosed strings
    - Missing colons after control structures
    - Missing parentheses in function calls
    - Basic indentation issues
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: The fixed code
        
    Examples:
        >>> _fix_common_syntax_issues('def hello world')
        'def hello world: '
        >>> _fix_common_syntax_issues('print "hello')
        'print "hello"'
    """
    # Fix unclosed strings with more robust pattern
    code = re.sub(
        r'([\'"])((?:[^\'"]|\\[\'"])*?)(?:\n|$)', 
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
    
    for line in lines:
        stripped = line.strip()
        
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
    
    return '\n'.join(fixed_lines)

def _fix_aggressive_syntax_issues(code: str) -> str:
    """
    Apply more aggressive syntax fixes when common fixes fail.
    
    This function handles more complex syntax issues like:
    - Non-printable characters
    - Complex string issues
    - Missing parentheses and brackets
    - Complex indentation issues
    
    Args:
        code (str): The code to fix
        
    Returns:
        str: The fixed code
        
    Examples:
        >>> _fix_aggressive_syntax_issues('print "hello\x00world"')
        'print "helloworld"'
        >>> _fix_aggressive_syntax_issues('def hello[world')
        'def hello[world]'
    """
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
    
    return '\n'.join(fixed_lines)

def _fix_specific_syntax_error(code: str, error_msg: str) -> str:
    """
    Fix specific syntax errors based on the error message.
    
    This function handles specific syntax errors like:
    - Unclosed string literals
    - Missing parentheses
    - Invalid indentation
    - Other common syntax errors
    
    Args:
        code (str): The code to fix
        error_msg (str): The syntax error message
        
    Returns:
        str: The fixed code
        
    Examples:
        >>> _fix_specific_syntax_error('print "hello', 'EOL while scanning string literal')
        'print "hello"'
        >>> _fix_specific_syntax_error('def hello(', 'unexpected EOF while parsing')
        'def hello():'
    """
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
    
    return code

def _detect_prompt_file(file_path: str, max_file_size: int = 1024 * 1024) -> Tuple[bool, Optional[str]]:
    """
    Detect if a file contains prompts by analyzing its content.
    
    Args:
        file_path: Path to the file to analyze
        max_file_size: Maximum file size to process (default: 1MB)
        
    Returns:
        Tuple[bool, Optional[str]]: (contains_prompt, error_message)
        
    Examples:
        >>> _detect_prompt_file("prompt.py")
        (True, None)
        >>> _detect_prompt_file("utils.py")
        (False, None)
    """
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > max_file_size:
            return False, f"File too large ({file_size} bytes)"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Use the PromptDetector class
        detector = PromptDetector()
        return detector.detect_prompt(file_path, content)
        
    except Exception as e:
        logger.error(f"Error detecting prompts in {file_path}: {str(e)}")
        return False, str(e)

def _get_prompt_template(file_path: str, test_config: Dict, files_to_fix: Dict[str, List[Dict]], 
                        file_dependencies: Dict[str, List[str]], context_files: Dict[str, str],
                        original_codes: Dict[str, str]) -> str:
    """
    Get the appropriate prompt template based on file content.
    
    Args:
        file_path: Path to the file being processed
        test_config: Test configuration dictionary
        files_to_fix: Dictionary mapping file paths to their failures
        file_dependencies: Dictionary mapping file paths to their dependencies
        context_files: Dictionary mapping file paths to their content
        original_codes: Dictionary mapping file paths to their original code
        
    Returns:
        str: The prompt template to use
    """
    contains_prompt, error = _detect_prompt_file(file_path)
    
    if error:
        logger.warning(f"Prompt detection error for {file_path}: {error}")
        # Default to code-focused template if detection fails
        contains_prompt = False
        
    logger.info(f"File {file_path} {'contains' if contains_prompt else 'does not contain'} prompts")
    
    # Common prompt elements
    common_elements = f"""
Test Configuration Context:
{json.dumps(test_config, indent=2)}

IMPORTANT: You are currently fixing this file: {file_path}
Failures in this file:
{chr(10).join(f'- {failure["test_name"]}: {failure["error_message"]}' for failure in files_to_fix[file_path])}

File Dependencies:
{chr(10).join(f'- {path} imports: {", ".join(deps)}' for path, deps in file_dependencies.items())}

All files in the codebase (for context):
{chr(10).join(f'=== {path} ==={chr(10)}{code}{chr(10)}' for path, code in context_files.items())}

The file you need to fix is: {file_path}
Original code for this file:
{original_codes[file_path]}
"""
    
    if contains_prompt:
        return f"""You are a senior AI agent engineer specializing in prompt engineering and AI agent development. Your task is to improve the prompts in this file while maintaining compatibility with the rest of the codebase.

{common_elements}

PRIMARY FOCUS: IMPROVE THE PROMPTS
1. Analyze each prompt in the file
2. Enhance prompt structure and clarity
3. Add necessary context and examples
4. Improve error handling and validation
5. Ensure prompts are robust and maintainable

Prompt Engineering Requirements:
1. Structure and Organization:
   - Use clear section headers and bullet points
   - Group related instructions together
   - Use consistent formatting and indentation
   - Include a clear introduction and conclusion
   - Add examples for complex instructions

2. Clarity and Precision:
   - Use clear, concise language
   - Avoid ambiguous terms
   - Define technical terms
   - Use active voice
   - Break down complex instructions into steps

3. Context and Background:
   - Provide necessary background information
   - Explain the purpose of each section
   - Include relevant domain knowledge
   - Specify the target audience
   - Add context for why certain requirements exist

4. Output Requirements:
   - Specify exact output format
   - Include example outputs
   - Define success criteria
   - List required elements
   - Specify length constraints
   - Add validation rules

5. Error Handling:
   - Define error scenarios
   - Specify error messages
   - Include recovery steps
   - Add fallback options
   - Define retry strategies

6. Safety and Quality:
   - Add content filtering rules
   - Include fact-checking requirements
   - Specify ethical guidelines
   - Add quality assurance steps
   - Include validation checks

7. AI-Specific Improvements:
   - Add model-specific instructions
   - Include temperature settings
   - Specify token limits
   - Add context window management
   - Include model behavior controls

8. Response Enhancement:
   - Add post-processing rules
   - Include formatting requirements
   - Specify style guidelines
   - Add quality checks
   - Include enhancement steps

Code Requirements (Secondary Focus):
1. Maintain existing code structure
2. Keep all imports and dependencies
3. Preserve function signatures
4. Maintain type hints
5. Keep error handling consistent
6. Ensure compatibility with other files

Return only the fixed code for {file_path}, without any file markers or additional text."""
    else:
        return f"""You are a senior AI agent engineer specializing in AI agent development. Your task is to improve this code file while maintaining compatibility with the rest of the codebase.

{common_elements}

PRIMARY FOCUS: IMPROVE THE CODE
1. Fix all test failures
2. Enhance code structure and organization
3. Improve error handling and validation
4. Optimize performance
5. Ensure code is maintainable and testable

Code Improvement Requirements:
1. Structure and Organization:
   - Follow clean code principles
   - Use clear and consistent naming
   - Organize code logically
   - Add proper documentation
   - Follow design patterns

2. Error Handling:
   - Add comprehensive error handling
   - Include proper error messages
   - Add recovery mechanisms
   - Handle edge cases
   - Add proper logging

3. Performance:
   - Optimize resource usage
   - Add caching where appropriate
   - Handle large inputs efficiently
   - Implement proper cleanup
   - Add performance monitoring

4. Testing:
   - Make code testable
   - Add proper mocking points
   - Include validation logic
   - Handle edge cases
   - Add proper assertions

5. Security:
   - Add input validation
   - Implement proper sanitization
   - Handle sensitive data
   - Add access controls
   - Follow security best practices

6. AI Agent Best Practices:
   - Implement proper initialization
   - Handle API rate limits
   - Add retry mechanisms
   - Validate model outputs
   - Handle model errors

7. Code Quality:
   - Add type hints
   - Include docstrings
   - Follow PEP 8
   - Add proper comments
   - Use consistent style

8. Maintainability:
   - Keep functions focused
   - Reduce complexity
   - Add proper logging
   - Include error tracking
   - Add monitoring

Return only the fixed code for {file_path}, without any file markers or additional text."""

def run_autofix_and_pr(failure_data: List[Dict], file_path: str, test_config_path: str, max_retries: int = 1, create_pr: bool = True, base_branch: str = 'main') -> List[Dict]:
    """
    Automatically fixes code based on test failures and optionally creates a PR.
    
    Args:
        failure_data: List of dictionaries containing test failure information
        file_path: Path to the source code file to be fixed
        test_config_path: Path to the test configuration file
        max_retries: Maximum number of retry attempts for fixing tests (default: 1)
        create_pr: Whether to create a pull request with the fixes (default: True)
        base_branch: The base branch to create the PR against (default: 'main')
        
    Returns:
        List of dictionaries containing information about each fix attempt
        
    Raises:
        ValueError: If required environment variables are not set
        subprocess.CalledProcessError: If git commands fail
        GithubException: If GitHub API operations fail
        FileNotFoundError: If required files cannot be found
    """
    try:
        # Start with a clear section marker
        logger.info("=" * 50)
        logger.info("Starting run_autofix_and_pr")
        
        # Validate input paths
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")
        if not os.path.exists(test_config_path):
            raise FileNotFoundError(f"Test configuration file not found: {test_config_path}")
        
        # Log basic information with sanitized data
        logger.info("Processing request", extra={
            'file_path': file_path,
            'test_config_path': test_config_path,
            'max_retries': max_retries,
            'create_pr': create_pr,
            'base_branch': base_branch,
            'failure_count': len(failure_data)
        })
        
        # Store the original file path to avoid shadowing
        main_file_path = os.path.abspath(file_path)
        logger.debug("Resolved main file path", extra={
            'original_path': file_path,
            'absolute_path': main_file_path
        })
        
        # Store the original branch
        original_branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        logger.info("Retrieved original branch", extra={'branch': original_branch})
        
        # Initialize branch_name with a default value
        branch_name = f"autofix-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        config = get_config()
        logger.info("Starting auto-fix process", extra={
            'file_path': main_file_path,
            'failure_count': len(failure_data)
        })
        
        # Create a set of failing test names for quick lookup
        failing_test_names = {failure["test_name"] for failure in failure_data}
        logger.debug("Failing test names", extra={'test_names': list(failing_test_names)})
        
        # Load test configuration
        try:
            with open(test_config_path, 'r') as f:
                test_config = yaml.safe_load(f)
                logger.info("Loaded test configuration", extra={
                    'config_path': test_config_path,
                    'config_name': test_config.get('name', 'Unnamed'),
                    'test_count': sum(len(result.get('test_cases', [])) 
                                    for result in test_config.get('regions', {}).values())
                })
                
                # Validate and resolve file paths in test configuration
                if 'file_path' in test_config:
                    config_dir = os.path.dirname(os.path.abspath(test_config_path))
                    test_file_path = os.path.normpath(os.path.join(config_dir, test_config['file_path']))
                    if not os.path.exists(test_file_path):
                        raise FileNotFoundError(f"Test file not found: {test_file_path}")
                    test_config['file_path'] = test_file_path
                    logger.info("Resolved test file path in configuration", extra={
                        'original_path': test_config['file_path'],
                        'resolved_path': test_file_path
                    })
                
                # Validate and resolve file paths in test steps
                for step in test_config.get('steps', []):
                    if 'input' in step and 'file_path' in step['input']:
                        step_dir = os.path.dirname(os.path.abspath(test_config_path))
                        step_file_path = os.path.normpath(os.path.join(step_dir, step['input']['file_path']))
                        if not os.path.exists(step_file_path):
                            raise FileNotFoundError(f"Step file not found: {step_file_path}")
                        step['input']['file_path'] = step_file_path
                        logger.debug("Resolved step file path", extra={
                            'step': step.get('name', 'Unknown'),
                            'original_path': step['input']['file_path'],
                            'resolved_path': step_file_path
                        })
                
        except Exception as e:
            logger.error("Failed to load test configuration", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'config_path': test_config_path
            })
            raise
        
        # Collect all referenced files
        try:
            referenced_files = _collect_referenced_files(main_file_path, failure_data=failure_data)
            logger.info("Collected referenced files", extra={
                'file_count': len(referenced_files),
                'files': list(referenced_files)
            })
            
            # Validate all referenced files exist
            missing_files = [f for f in referenced_files if not os.path.exists(f)]
            if missing_files:
                raise FileNotFoundError(f"Referenced files not found: {missing_files}")
            
            # Log details about each referenced file
            for ref_file in referenced_files:
                try:
                    with open(ref_file, 'r') as f:
                        content = f.read()
                        logger.debug("File content details", extra={
                            'file': ref_file,
                            'content_length': len(content),
                            'content_preview': content[:100] if len(content) > 100 else content
                        })
                except Exception as e:
                    logger.error("Failed to read file", extra={
                        'file': ref_file,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    raise
        except Exception as e:
            logger.error("Failed to collect referenced files", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'file_path': main_file_path
            })
            raise
        
        # Analyze which files need to be fixed based on failures
        try:
            file_failures = _analyze_failure_dependencies(failure_data, referenced_files)
            logger.info("Analyzed failure dependencies", extra={
                'file_count': len(file_failures),
                'files_with_failures': [f for f, fails in file_failures.items() if fails]
            })
            
            # Log detailed failure analysis for each file
            for file_path, failures in file_failures.items():
                if failures:
                    logger.debug("File failure details", extra={
                        'file': file_path,
                        'failure_count': len(failures),
                        'failures': [{
                            'test_name': f.get('test_name'),
                            'error_message': f.get('error_message'),
                            'region': f.get('region')
                        } for f in failures]
                    })
        except Exception as e:
            logger.error("Failed to analyze failure dependencies", extra={
                'error': str(e)
            })
            raise
        
        # Load original code for all files
        original_codes = {}
        for ref_file in referenced_files:
            try:
                with open(ref_file, 'r') as f:
                    original_codes[ref_file] = f.read()
                logger.debug("Loaded original code", extra={
                    'file': ref_file,
                    'content_length': len(original_codes[ref_file])
                })
            except Exception as e:
                logger.error("Failed to load original code", extra={
                    'file': ref_file,
                    'error': str(e)
                })
                raise
        
        # Generate PR info with test configuration
        try:
            branch_name, pr_title, pr_body = _generate_pr_info(failure_data, [], {}, test_config, original_codes[main_file_path])
            logger.info("Generated PR info", extra={
                'branch_name': branch_name,
                'pr_title': pr_title,
                'pr_body_length': len(pr_body)
            })
        except Exception as e:
            logger.warning("Failed to generate PR info", extra={
                'error': str(e)
            })
            # Use default values if PR info generation fails
            timestamp = datetime.now().strftime('%Y%m%d')
            branch_name = f"fix-tests-{timestamp}"
            pr_title = "Fix: Resolved test failures"
            pr_body = f"# Test Fix Summary\n\nFixing test failures in {file_path}"
        
        # Track which previously failing tests are now passing
        fixed_tests = []
        best_fixed_tests = []
        best_fixed_codes = {}
        
        # Track all test attempts
        all_test_attempts = []
        
        for attempt in range(max_retries):
            logger.info("Starting auto-fix attempt", extra={
                'attempt': attempt + 1,
                'max_retries': max_retries
            })
            
            # Get the fixed code from Gemini for each file that needs fixing
            genai.configure(api_key=config.get_api_key("google"))
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            
            fixed_codes = {}
            # Collect all files that need fixing
            files_to_fix = {path: failures for path, failures in file_failures.items() if failures}
            
            if files_to_fix:
                logger.info("Requesting code fixes", extra={
                    'file_count': len(files_to_fix),
                    'files': list(files_to_fix.keys())
                })
                
                # Analyze dependencies between files
                file_dependencies = {}
                for path in files_to_fix.keys():
                    try:
                        with open(path, 'r') as f:
                            content = f.read()
                            tree = ast.parse(content)
                            imports = []
                            for node in ast.walk(tree):
                                if isinstance(node, (ast.Import, ast.ImportFrom)):
                                    if isinstance(node, ast.Import):
                                        imports.extend(name.name.split('.')[0] for name in node.names)
                                    else:
                                        imports.append(node.module.split('.')[0])
                            file_dependencies[path] = imports
                            logger.debug("File dependencies", extra={
                                'file': path,
                                'imports': imports
                            })
                    except Exception as e:
                        logger.warning("Failed to analyze dependencies", extra={
                            'file': path,
                            'error': str(e)
                        })
                        file_dependencies[path] = []
                
                # Sort files by dependencies (files with no dependencies first)
                sorted_files = []
                remaining_files = set(files_to_fix.keys())
                
                while remaining_files:
                    # Find files with no remaining dependencies
                    independent_files = {
                        f for f in remaining_files 
                        if not any(dep in remaining_files for dep in file_dependencies.get(f, []))
                    }
                    
                    if not independent_files:
                        # If no independent files found but we still have remaining files,
                        # there might be a circular dependency. Just take the first file.
                        independent_files = {next(iter(remaining_files))}
                    
                    sorted_files.extend(independent_files)
                    remaining_files -= independent_files

                # Fix files one by one, using previously fixed files as context
                for current_file in sorted_files:
                    logger.info(f"Fixing file: {current_file}")
                    
                    # Prepare context from all files
                    context_files = {}
                    # Add previously fixed files
                    for fixed_file in fixed_codes:
                        context_files[fixed_file] = fixed_codes[fixed_file]
                    
                    # Add original code for unfixed files
                    for unfixed_file in files_to_fix:
                        if unfixed_file not in fixed_codes:
                            context_files[unfixed_file] = original_codes[unfixed_file]
                    
                    # Get appropriate prompt template
                    prompt = _get_prompt_template(
                        current_file,
                        test_config,
                        files_to_fix,
                        file_dependencies,
                        context_files,
                        original_codes
                    )
                    
                    logger.debug("Generated prompt for file", extra={
                        'file': current_file,
                        'prompt_length': len(prompt)
                    })
                    
                    # Get fix for current file
                    retry_count = 0
                    max_retries = 3
                    
                    while retry_count < max_retries:
                        try:
                            response = model.generate_content(prompt)
                            fixed_code = response.text.strip()
                            
                            # Validate and improve the generated code
                            fixed_code = _validate_and_improve_code(fixed_code, original_codes[current_file])
                            
                            # Additional validation
                            if not fixed_code or fixed_code.isspace():
                                raise ValueError("Generated code is empty or whitespace only")
                                
                            if fixed_code == original_codes[current_file]:
                                logger.warning("Generated code is identical to original", extra={
                                    'file': current_file
                                })
                                retry_count += 1
                                continue
                            
                            fixed_codes[current_file] = fixed_code
                            logger.info("Successfully fixed code", extra={
                                'file': current_file,
                                'content_length': len(fixed_code)
                            })
                            break
                            
                        except Exception as e:
                            logger.error("Failed to process file", extra={
                                'file': current_file,
                                'error': str(e),
                                'error_type': type(e).__name__
                            })
                            retry_count += 1
                            if retry_count >= max_retries:
                                # If all retries failed, keep original code
                                fixed_codes[current_file] = original_codes[current_file]
                                logger.warning("Using original code after failed fixes", extra={
                                    'file': current_file
                                })
                            continue
            
            # Write all fixed code to disk before running tests
            logger.info("Writing fixed code to disk", extra={
                'file_count': len(fixed_codes)
            })
            
            # Apply code changes with proper verification
            _apply_code_changes(fixed_codes, original_codes)
            
            # Run tests again to verify fixes
            logger.info("Running tests to verify fixes")
            
            test_runner = TestRunner(test_config)
            test_logger = TestLogger(f"Auto-fix Test Run (Attempt {attempt + 1})")
            
            # Extract file path from the root of the configuration
            test_file_path = test_config.get('file_path')
            logger.info("Retrieved test file path", extra={
                'test_file_path': test_file_path
            })
            
            if not test_file_path:
                error_msg = "No file_path found in test configuration"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Resolve the test file path relative to the YAML config file's directory
            config_dir = os.path.dirname(os.path.abspath(test_config_path))
            resolved_test_file_path = os.path.normpath(os.path.join(config_dir, test_file_path))
            logger.info("Resolved test file path", extra={
                'resolved_path': resolved_test_file_path,
                'config_dir': config_dir
            })
            
            logger.info("Running tests", extra={
                'file_path': resolved_test_file_path
            })
            try:
                test_results = test_runner.run_tests(Path(resolved_test_file_path))
                logger.info("Test execution completed", extra={
                    'result_type': type(test_results).__name__
                })
            except Exception as e:
                logger.error("Test execution failed", extra={
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                raise
            
            # Validate test results
            if test_results is None:
                error_msg = "Test runner returned None results"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not isinstance(test_results, dict):
                error_msg = f"Invalid test results type: {type(test_results)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Store this attempt's results
            all_test_attempts.append({
                'attempt': attempt + 1,
                'code': fixed_codes,
                'results': test_results
            })
            
            # Check if test results indicate an error
            if isinstance(test_results, dict) and test_results.get('overall_status') == 'error':
                error_msg = test_results.get('error', 'Unknown error')
                logger.error("Test execution failed", extra={
                    'error': error_msg
                })
                raise RuntimeError(f"Test execution failed: {error_msg}")
            
            # Track which previously failing tests are now passing
            fixed_tests = []
            logger.info("Processing test results", extra={
                'region_count': len(test_results)
            })
            for region, result in test_results.items():
                if isinstance(result, str) or region in ('_status', 'overall_status'):
                    logger.debug("Skipping special region", extra={
                        'region': region
                    })
                    continue
                    
                if not isinstance(result, dict):
                    logger.warning("Invalid result format", extra={
                        'region': region,
                        'result_type': type(result).__name__
                    })
                    continue
                    
                test_cases = result.get('test_cases', [])
                logger.debug("Processing test cases", extra={
                    'region': region,
                    'test_case_count': len(test_cases)
                })
                
                if not isinstance(test_cases, list):
                    logger.warning("Invalid test cases format", extra={
                        'region': region,
                        'test_cases_type': type(test_cases).__name__
                    })
                    continue
                    
                for test_case in test_cases:
                    if not isinstance(test_case, dict):
                        logger.warning("Invalid test case format", extra={
                            'region': region,
                            'test_case_type': type(test_case).__name__
                        })
                        continue
                        
                    test_name = test_case.get('name')
                    test_status = test_case.get('status')
                    
                    if test_name in failing_test_names and test_status == 'passed':
                        logger.info("Found fixed test", extra={
                            'test_name': test_name,
                            'region': region
                        })
                        fixed_tests.append({
                            'region': region,
                            'test_name': test_name
                        })
            
            logger.info("Test processing completed", extra={
                'fixed_test_count': len(fixed_tests)
            })
            
            # Update best attempt if this one fixed more tests
            if len(fixed_tests) > len(best_fixed_tests):
                best_fixed_tests = fixed_tests
                best_fixed_codes = fixed_codes
                logger.info("Updated best attempt", extra={
                    'fixed_test_count': len(fixed_tests)
                })
            
            # If we fixed all tests, we can stop early
            if len(fixed_tests) == len(failing_test_names):
                logger.info("All tests fixed", extra={
                    'fixed_test_count': len(fixed_tests)
                })
                break
            
            # If this is not the last attempt, continue to next iteration
            if attempt < max_retries - 1:
                logger.info("Continuing to next attempt", extra={
                    'current_attempt': attempt + 1,
                    'max_retries': max_retries,
                    'fixed_test_count': len(fixed_tests)
                })
                continue
        
        # Use the best attempt's results
        fixed_tests = best_fixed_tests
        fixed_codes = best_fixed_codes
        
        if not fixed_tests:
            logger.info("No tests were fixed, reverting changes")
            subprocess.run(["git", "checkout", original_branch], check=True)
            # Only try to delete the branch if we created it
            try:
                # Check if branch exists
                result = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], 
                                      capture_output=True, check=False)
                if result.returncode == 0:
                    subprocess.run(["git", "branch", "-D", branch_name], check=True)
            except subprocess.CalledProcessError:
                # Ignore errors if branch doesn't exist
                pass
            return all_test_attempts
        
        logger.info("Tests fixed successfully", extra={
            'fixed_test_count': len(fixed_tests)
        })
        
        # Update PR info with fixed tests
        branch_name, pr_title, pr_body = _generate_pr_info(failure_data, fixed_tests, test_results, test_config, original_codes[main_file_path])
        logger.info("Updated PR info", extra={
            'branch_name': branch_name,
            'pr_title': pr_title
        })
        
        # Create a new branch
        logger.info("Creating new branch", extra={
            'branch_name': branch_name
        })
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        except subprocess.CalledProcessError:
            # If branch already exists, add a unique suffix
            logger.info("Branch already exists, adding unique suffix", extra={
                'branch_name': branch_name
            })
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=4))
            unique_branch_name = f"{branch_name}-{timestamp}-{random_suffix}"
            logger.info("Trying with new branch name", extra={
                'new_branch_name': unique_branch_name
            })
            subprocess.run(["git", "checkout", "-b", unique_branch_name], check=True)
            branch_name = unique_branch_name
        
        # Write the best fixed code back to disk before committing
        logger.info("Writing fixed code to disk", extra={
            'file_count': len(fixed_codes)
        })
        for current_file_path, code in fixed_codes.items():
            with open(current_file_path, 'w') as f:
                f.write(code)
            logger.debug("Updated file", extra={
                'file': current_file_path,
                'content_length': len(code)
            })
        
        # Commit changes with a proper commit message
        subprocess.run(["git", "add", *fixed_codes.keys()], check=True)
        commit_message = f"Fix: {pr_title}\n\n{pr_body}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        logger.info("Committed changes", extra={
            'commit_message': commit_message[:100] + "..." if len(commit_message) > 100 else commit_message
        })
        
        # Push branch
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
        logger.info("Pushed branch", extra={
            'branch_name': branch_name
        })
        
        # Create PR using GitHub API
        if create_pr:
            logger.info("Starting PR creation process")
            github_token = os.environ.get("GITHUB_TOKEN")
            if not github_token:
                raise ValueError("GITHUB_TOKEN environment variable not set. Please set it with your GitHub personal access token.")
            
            g = Github(github_token)
            
            # Get repository information from git config
            try:
                repo_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
                if repo_url.endswith('.git'):
                    repo_url = repo_url[:-4]
                repo_name = repo_url.split('/')[-1]
                repo_owner = repo_url.split('/')[-2]
                repo = g.get_repo(f"{repo_owner}/{repo_name}")
                logger.info("Connected to repository", extra={
                    'repo': f"{repo_owner}/{repo_name}"
                })
            except subprocess.CalledProcessError:
                raise ValueError("Could not determine repository information. Please ensure you're in a git repository with a remote origin.")
            except GithubException as e:
                raise ValueError(f"Error accessing GitHub repository: {str(e)}")
            
            # Create PR
            logger.info("Preparing to create PR")
            try:
                enhanced_pr_body = _enhance_pr_body(failure_data, fixed_tests, test_results, test_config, all_test_attempts)
                logger.info("Enhanced PR body", extra={
                    'body_length': len(enhanced_pr_body)
                })
            except Exception as e:
                logger.error("Failed to enhance PR body", extra={
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                raise
            
            try:
                # Ensure PR title is not empty
                if not pr_title or not pr_title.strip():
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    pr_title = f"Fix: Resolved test failures ({timestamp})"
                    logger.warning("Empty PR title detected", extra={
                        'new_title': pr_title
                    })
                
                pr = repo.create_pull(
                    title=pr_title,
                    body=enhanced_pr_body,
                    head=branch_name,
                    base=base_branch
                )
                logger.info("Created Pull Request", extra={
                    'pr_url': pr.html_url
                })
                print(f"Pull Request created: {pr.html_url}")
            except Exception as e:
                logger.error("Failed to create PR", extra={
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                raise
        
        # Return to the original branch
        logger.info("Returning to original branch", extra={
            'branch': original_branch
        })
        subprocess.run(["git", "checkout", original_branch], check=True)
        
        return all_test_attempts
        
    except subprocess.CalledProcessError as e:
        logger.error("Git command failed", extra={
            'error': str(e),
            'command': e.cmd,
            'returncode': e.returncode
        })
        # Try to return to original branch even if there was an error
        try:
            subprocess.run(["git", "checkout", original_branch], check=True)
        except:
            pass
        raise
    except GithubException as e:
        logger.error("GitHub API error", extra={
            'error': str(e),
            'status': e.status,
            'data': e.data
        })
        # Try to return to original branch even if there was an error
        try:
            subprocess.run(["git", "checkout", original_branch], check=True)
        except:
            pass
        raise
    except Exception as e:
        logger.error("Unexpected error", extra={
            'error': str(e),
            'error_type': type(e).__name__,
            'error_args': e.args
        })
        # Try to return to original branch even if there was an error
        try:
            subprocess.run(["git", "checkout", original_branch], check=True)
        except:
            pass
        raise 