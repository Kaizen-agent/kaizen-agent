"""
Main runner module for Kaizen Agent.
"""
import yaml
import os
import sys
import time
import io
import ast
import json
import datetime
import types
import importlib
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Type, TypeVar, Callable, Sequence, Mapping, Set, FrozenSet, Tuple
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

from .agent_runners import AgentRegistry, AgentRunner, PythonAgentRunner, TypeScriptAgentRunner, DynamicRegionRunner
from .logger import TestLogger
from .code_region import extract_code_regions
from .config import get_config

console = Console()

def create_execution_namespace() -> Dict[str, Any]:
    """
    Create a namespace with commonly used imports and utilities.
    
    Returns:
        Dict[str, Any]: A dictionary containing the execution namespace
    """
    # Get all built-in modules
    builtins = {name: module for name, module in sys.modules.items() 
               if name in sys.builtin_module_names}
    
    # Add commonly used imports
    namespace = {
        # Typing imports
        'Optional': Optional,
        'Dict': Dict,
        'List': List,
        'Any': Any,
        'Union': Union,
        'Type': Type,
        'TypeVar': TypeVar,
        'Callable': Callable,
        'Sequence': Sequence,
        'Mapping': Mapping,
        'Set': Set,
        'FrozenSet': FrozenSet,
        'Tuple': Tuple,
        
        # Standard library imports
        'Path': Path,
        'os': os,
        'sys': sys,
        'time': time,
        'io': io,
        'ast': ast,
        'yaml': yaml,
        'json': json,
        'datetime': datetime,
        'types': types,
        'redirect_stdout': redirect_stdout,
        'StringIO': io.StringIO,
        'importlib': importlib,
        
        # Add typing module itself
        'typing': sys.modules['typing'],
        
        # Add all built-in modules
        **builtins
    }
    
    # Add common third-party imports
    try:
        import openai
        namespace['openai'] = openai
    except ImportError:
        pass
        
    try:
        from dotenv import load_dotenv
        namespace['load_dotenv'] = load_dotenv
    except ImportError:
        pass
    
    return namespace

def execute_code_block(block_code: str, namespace: Dict[str, Any], test_input: Optional[str] = None) -> str:
    """
    Execute a code block and handle function/class execution.
    
    Args:
        block_code (str): The code to execute
        namespace (Dict[str, Any]): The execution namespace
        test_input (Optional[str]): Input to pass to functions/classes
        
    Returns:
        str: The execution output (only return values, ignoring printed output)
    """
    try:
        # Parse the block to determine its type
        block_ast = ast.parse(block_code)
        
        # Execute the block in the namespace (without capturing stdout)
        exec(block_code, namespace)
        
        # Check if it's a function or class
        if len(block_ast.body) == 1:
            node = block_ast.body[0]
            
            if isinstance(node, ast.FunctionDef):
                # It's a function, call it with test_input
                func_name = node.name
                if func_name in namespace:
                    try:
                        result = namespace[func_name](test_input)
                        if result is not None:
                            return str(result)
                    except Exception as e:
                        return f"Error executing function {func_name}: {str(e)}"
                        
            elif isinstance(node, ast.ClassDef):
                # It's a class, try to find and call a method that takes input
                class_name = node.name
                if class_name in namespace:
                    try:
                        # Create an instance of the class
                        instance = namespace[class_name]()
                        
                        # Find a method that takes input
                        for method_name in dir(instance):
                            method = getattr(instance, method_name)
                            if callable(method) and not method_name.startswith('_'):
                                # Check if the method can accept the test_input
                                try:
                                    result = method(test_input)
                                    if result is not None:
                                        return str(result)
                                except (TypeError, ValueError):
                                    # Skip methods that don't accept the input
                                    continue
                                    
                        return f"Error: No suitable method found in class {class_name} that accepts the input"
                    except Exception as e:
                        return f"Error executing class {class_name}: {str(e)}"
        
        # If we get here, either it wasn't a function/class or there was no return value
        return "No return value found"
        
    except SyntaxError as e:
        return f"Error: Invalid Python syntax in block: {str(e)}"
    except Exception as e:
        return f"Error executing code block: {str(e)}"

def run_test_block(file_path: str, test_input: Optional[str] = None, region: Optional[str] = None, config_file: Optional[str] = None) -> str:
    """
    Execute a code block between kaizen markers in a Python file.
    
    Args:
        file_path (str): Path to the Python file
        test_input (Optional[str]): Input to pass to the function/class if applicable
        region (Optional[str]): Name of the region to extract (e.g., 'email_agent')
        config_file (Optional[str]): Path to the config file for resolving relative paths
        
    Returns:
        str: Output from the code block execution or error message
    """
    try:
        console.print(f"[blue]Debug: run_test_block called with file_path={file_path}, config_file={config_file}[/blue]")
        
        # Convert test file path to actual code file path
        if file_path.endswith('.yaml'):
            # If it's a test file, look for the corresponding Python file
            # Remove the test file extension and directory structure
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            # Remove common test prefixes/suffixes
            base_name = base_name.replace('test_', '').replace('_test', '')
            # Look for the corresponding Python file in the same directory
            code_file = os.path.join(os.path.dirname(file_path), f"{base_name}.py")
            console.print(f"[blue]Debug: Resolved YAML test file to code file: {code_file}[/blue]")
            if not os.path.exists(code_file):
                return f"Error: Could not find code file at {code_file}"
        else:
            # If the file path is absolute, use it directly
            if os.path.isabs(file_path):
                code_file = file_path
                console.print(f"[blue]Debug: Using absolute path: {code_file}[/blue]")
            # If config_file is provided, resolve the file_path relative to it
            elif config_file:
                config_dir = os.path.dirname(os.path.abspath(config_file))
                code_file = os.path.normpath(os.path.join(config_dir, file_path))
                console.print(f"[blue]Debug: Resolved relative path using config_dir={config_dir}[/blue]")
                console.print(f"[blue]Debug: Final resolved code_file={code_file}[/blue]")
            else:
                code_file = file_path
                console.print(f"[blue]Debug: Using relative path: {code_file}[/blue]")

        # Check if file exists
        if not os.path.exists(code_file):
            return f"Error: File not found at {code_file} (resolved from {file_path})"

        # Add the file's directory and parent directories to Python path
        file_dir = os.path.dirname(os.path.abspath(code_file))
        parent_dir = os.path.dirname(file_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            console.print(f"[blue]Debug: Added {parent_dir} to Python path[/blue]")

        # Read the full file
        with open(code_file, 'r') as f:
            content = f.read()
            
        # Extract the block between markers
        if region:
            # Use named region markers
            start_marker = f'# kaizen:start:{region}'
            end_marker = f'# kaizen:end:{region}'
        else:
            # Use simple markers
            start_marker = '# kaizen:start'
            end_marker = '# kaizen:end'
        
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return f"Error: Start marker '{start_marker}' not found in file {code_file}"
            
        end_idx = content.find(end_marker, start_idx)
        if end_idx == -1:
            return f"Error: End marker '{end_marker}' not found in file {code_file}"
            
        # Extract the block code
        block_code = content[start_idx + len(start_marker):end_idx].strip()
        
        # Create a temporary module to execute the code
        module_name = os.path.splitext(os.path.basename(code_file))[0]
        package_name = os.path.basename(os.path.dirname(code_file))
        
        # Create a new module
        spec = importlib.util.spec_from_file_location(f"{package_name}.{module_name}", code_file)
        if spec is None:
            return f"Error: Could not create module spec for {code_file}"
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        
        # Set up the module's namespace
        module.__file__ = code_file
        module.__package__ = package_name
        
        # Execute the module's code
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            return f"Error executing module: {str(e)}"
            
        # Now execute the specific block
        try:
            # Create a new namespace for the block execution
            block_namespace = {
                '__name__': f'{package_name}.{module_name}',
                '__file__': code_file,
                '__package__': package_name,
                '__builtins__': __builtins__,
                # Copy all names from the module
                **{name: getattr(module, name) for name in dir(module) if not name.startswith('_')}
            }
            
            # Execute the block in the new namespace
            exec(block_code, block_namespace)
            
            # If there's a test input, try to call the main function/class
            if test_input:
                # Look for a class with a run method
                for name, obj in block_namespace.items():
                    if isinstance(obj, type) and hasattr(obj, 'run'):
                        # If it's a static method, call it directly
                        if isinstance(obj.run, staticmethod):
                            return str(obj.run(test_input))
                        # Otherwise create an instance and call run
                        else:
                            instance = obj()
                            return str(instance.run(test_input))
                            
                # If no class with run method found, look for a main function
                if 'main' in block_namespace:
                    main_func = block_namespace['main']
                    if callable(main_func):
                        return str(main_func(test_input))
                        
            return "Code block executed successfully"
            
        except Exception as e:
            return f"Error executing code block: {str(e)}"
            
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        # Clean up: remove the added path
        if parent_dir in sys.path:
            sys.path.remove(parent_dir)
            console.print(f"[blue]Debug: Removed {parent_dir} from Python path[/blue]")

class TestRunner:
    def __init__(self, test_config: Optional[Dict] = None):
        """
        Initialize the TestRunner.
        
        Args:
            test_config: Optional test configuration dictionary
        """
        self.test_config = test_config or {}
        self._load_config()
        self._validate_api_keys()
        self.agent_registry = AgentRegistry()
        # Register default runners
        self.agent_registry.register("python", PythonAgentRunner)
        self.agent_registry.register("typescript", TypeScriptAgentRunner)
        self.agent_registry.register("dynamic_region", DynamicRegionRunner)

    def _load_config(self):
        """Load configuration from environment variables and test config."""
        print("Debug: TestRunner: Starting configuration loading...")
        
        # Load environment variables using the Config class
        self.config = get_config()
        print("Debug: TestRunner: Config instance created")
        
        # Merge with test config if provided
        if self.test_config:
            print(f"Debug: TestRunner: Merging test config: {self.test_config}")
            self.config.update(self.test_config)
        
        print("Debug: TestRunner: Configuration loading completed")

    def _validate_api_keys(self):
        """Validate that required API keys are present."""
        print("Debug: TestRunner: Starting API key validation...")
        
        # Google API key is required by default
        google_key = os.getenv('GOOGLE_API_KEY')
        print(f"Debug: TestRunner: GOOGLE_API_KEY present: {google_key is not None}")
        
        if not google_key:
            console.print("[red]Error: Missing required API key: GOOGLE_API_KEY[/red]")
            console.print("Please add it to your .env file or environment variables")
            sys.exit(1)
            
        # Configure Google API
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            # Test the configuration with a simple model
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            print("Debug: TestRunner: Successfully configured Google API")
        except Exception as e:
            console.print(f"[red]Error configuring Google API: {str(e)}[/red]")
            sys.exit(1)

        # OpenAI API key is optional - only warn if not present
        openai_key = os.getenv('OPENAI_API_KEY')
        print(f"Debug: TestRunner: OPENAI_API_KEY present: {openai_key is not None}")
        if not openai_key:
            console.print("[yellow]Note: OPENAI_API_KEY not found - OpenAI-based tests will use Google Gemini instead[/yellow]")

        # Anthropic API key is optional - only warn if not present
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        print(f"Debug: TestRunner: ANTHROPIC_API_KEY present: {anthropic_key is not None}")
        if not anthropic_key:
            console.print("[yellow]Note: ANTHROPIC_API_KEY not found - Anthropic-based tests will use Google Gemini instead[/yellow]")

    def load_test_file(self, file_path: str) -> Dict:
        """Load and parse a YAML test file."""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            console.print(f"[red]Error: Invalid YAML syntax in {file_path}[/red]")
            console.print(f"Line {e.problem_mark.line + 1}: {e.problem}")
            sys.exit(1)
        except FileNotFoundError:
            console.print(f"[red]Error: Test file not found: {file_path}[/red]")
            sys.exit(1)

    def validate_test_data(self, test_data: Dict) -> bool:
        """Validate test data structure."""
        # Accept both 'name' and 'test_name' as valid fields
        if 'name' not in test_data and 'test_name' not in test_data:
            console.print("[red]Error: Missing required field: 'name' or 'test_name'[/red]")
            return False
        
        # Use either name or test_name
        test_data['name'] = test_data.get('name') or test_data.get('test_name')
        
        required_fields = ['agent_type', 'steps']
        missing_fields = [field for field in required_fields if field not in test_data]
        
        if missing_fields:
            console.print(f"[red]Error: Missing required fields: {', '.join(missing_fields)}[/red]")
            return False
        
        for step in test_data['steps']:
            if 'input' not in step:
                console.print(f"[red]Error: Missing 'input' field in step[/red]")
                return False
        
        return True

    def run_step(self, step: Dict, global_agent_type: str, logger: TestLogger) -> bool:
        """Run a single test step and return whether it passed."""
        step_index = step.get('step_index', 0)
        agent_type = step.get('agent_type', global_agent_type)
        input_data = step.get('input', {})
        expected_contains = step.get('expected_output_contains', [])
        expected_exact = step.get('expected_output_exact')
        expected_exit_code = step.get('expected_exit_code', 0)

        # Log step start
        logger.log_step_start(step_index, input_data)

        try:
            # Handle code block execution
            if 'file_path' in input_data:
                # Get the appropriate agent runner
                runner = self.agent_registry.get_runner(agent_type)
                if not runner:
                    error_msg = f"No runner found for agent type: {agent_type}"
                    logger.log_step_result(step_index, None, False, error_msg)
                    return False

                # Create a copy of input_data with the resolved file path
                resolved_input = input_data.copy()
                if 'file_path' in resolved_input:
                    # Use the file_path from test_config which is already resolved
                    resolved_input['file_path'] = self.test_config.get('file_path')
                    console.print(f"[blue]Debug: Using resolved file path: {resolved_input['file_path']}[/blue]")

                # Run the agent with resolved input
                result = runner.run(resolved_input)
                
                if result.get('status') == 'error':
                    error_msg = result.get('error', 'Unknown error')
                    logger.log_step_result(step_index, None, False, error_msg)
                    return False
                
                output = result.get('output', '')
                
                # Validate output
                if expected_contains:
                    for expected in expected_contains:
                        if expected not in output:
                            error_msg = f"Expected output not found: {expected}"
                            logger.log_step_result(step_index, output, False, error_msg)
                            return False

                if expected_exact:
                    if output != expected_exact:
                        error_msg = "Output does not match expected exact output"
                        logger.log_step_result(step_index, output, False, error_msg)
                        return False

                logger.log_step_result(step_index, output, True)
                return True

            # Handle CLI-specific tests
            if 'command' in input_data:
                return self._run_cli_test(input_data, expected_exit_code, logger)

            # Handle configuration tests
            if 'env_file' in input_data or 'config_file' in input_data:
                return self._run_config_test(input_data, expected_exit_code, logger)

            error_msg = "No valid input data found in step"
            logger.log_step_result(step_index, None, False, error_msg)
            return False

        except Exception as e:
            error_msg = f"Error in step execution: {str(e)}"
            logger.log_step_result(step_index, None, False, error_msg)
            return False

    def _run_cli_test(self, input_data: Dict, expected_exit_code: int, logger: TestLogger) -> bool:
        """Run a CLI-specific test."""
        import subprocess
        command = input_data['command']
        
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=input_data.get('timeout', 30)
            )
            
            if result.returncode != expected_exit_code:
                logger.logger.error(f"Expected exit code {expected_exit_code}, got {result.returncode}")
                return False
            
            output = result.stdout + result.stderr
            expected_contains = input_data.get('expected_output_contains', [])
            
            for expected in expected_contains:
                if expected not in output:
                    logger.logger.error(f"Expected output not found: {expected}")
                    return False
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.logger.error("Command execution timed out")
            return False
        except Exception as e:
            logger.logger.error(f"Error executing command: {str(e)}")
            return False

    def _run_config_test(self, input_data: Dict, expected_exit_code: int, logger: TestLogger) -> bool:
        """Run a configuration-specific test."""
        try:
            if 'env_file' in input_data:
                env_path = Path(input_data['env_file'])
                if not env_path.exists() and expected_exit_code == 1:
                    return True
                
                load_dotenv(env_path)
                self._validate_api_keys()
            
            if 'config_file' in input_data:
                config_path = Path(input_data['config_file'])
                if not config_path.exists() and expected_exit_code == 1:
                    return True
                
                with open(config_path) as f:
                    yaml.safe_load(f)
            
            return True
            
        except Exception as e:
            if expected_exit_code == 1:
                return True
            logger.logger.error(f"Error in configuration test: {str(e)}")
            return False

    def run_tests(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Run all tests specified in the configuration.
        
        Args:
            file_path: Path to the file to test
            
        Returns:
            Dict[str, Any]: Test results for each region
        """
        file_path = Path(file_path)
        results = {
            'overall_status': {
                'test_cases': [],
                'status': 'failed'
            }
        }
        all_steps_passed = True
        
        # Get the agent type from config
        agent_type = self.test_config.get('agent_type', 'dynamic_region')
        
        # Store the resolved file path in the test configuration
        self.test_config['file_path'] = str(file_path)
        
        # Create logger
        logger = TestLogger(self.test_config.get('name', 'Unnamed Test'))
        
        try:
            # Log configuration details
            console.print(f"[blue]Debug: Test configuration: {self.test_config}[/blue]")
            console.print(f"[blue]Debug: Test file path: {file_path}[/blue]")
            console.print(f"[blue]Debug: Config file path: {self.test_config.get('config_file')}[/blue]")
            
            # Log file contents for debugging only if debug mode is enabled
            debug_mode = os.getenv('KAIZEN_DEBUG', '').lower() in ('true', '1', 'yes')
            if debug_mode:
                with open(file_path, 'r') as f:
                    file_contents = f.read()
                    console.print(f"[blue]Debug: File contents:\n{file_contents}[/blue]")
            
            # Initialize LLM evaluator if evaluation criteria are specified
            evaluator = None
            if 'evaluation' in self.test_config:
                from .evaluator import LLMEvaluator
                evaluator = LLMEvaluator(
                    provider=self.test_config['evaluation'].get('llm_provider', 'google'),
                    logger=logger
                )
            
            # Add the file's directory and parent directories to Python path
            file_dir = os.path.dirname(os.path.abspath(file_path))
            parent_dir = os.path.dirname(file_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
                console.print(f"[blue]Debug: Added {parent_dir} to Python path[/blue]")
            
            try:
                # Run each test step
                for step in self.test_config.get('steps', []):
                    step_index = step.get('step_index')
                    step_name = step.get('name', f'Step {step_index}')
                    
                    logger.log_step_start(step_index, step.get('input', {}))
                    
                    # Run the step and capture output
                    output = None
                    if 'region' in step.get('input', {}):
                        console.print(f"[blue]Debug: Running test block for step {step_index}[/blue]")
                        console.print(f"[blue]Debug: Step input: {step.get('input', {})}[/blue]")
                        
                        # Use the step's file_path if provided, otherwise use the main test file path
                        step_file_path = step.get('input', {}).get('file_path')
                        if step_file_path:
                            # Resolve the step's file path relative to the config file
                            if self.test_config.get('config_file'):
                                config_dir = os.path.dirname(os.path.abspath(self.test_config['config_file']))
                                step_file_path = os.path.normpath(os.path.join(config_dir, step_file_path))
                            console.print(f"[blue]Debug: Using step's file path: {step_file_path}[/blue]")
                        else:
                            step_file_path = str(file_path)
                            console.print(f"[blue]Debug: Using main test file path: {step_file_path}[/blue]")
                        
                        try:
                            # Read the file content
                            console.print(f"[blue]Debug: Reading file content from {step_file_path}[/blue]")
                            with open(step_file_path, 'r') as f:
                                content = f.read()
                            
                            # Extract the code between kaizen markers first
                            region = step.get('input', {}).get('region')
                            if region:
                                start_marker = f'# kaizen:start:{region}'
                                end_marker = f'# kaizen:end:{region}'
                            else:
                                start_marker = '# kaizen:start'
                                end_marker = '# kaizen:end'
                            
                            console.print(f"[blue]Debug: Looking for markers: start='{start_marker}', end='{end_marker}'[/blue]")
                            
                            start_idx = content.find(start_marker)
                            if start_idx == -1:
                                console.print(f"[red]Error: Start marker '{start_marker}' not found in file[/red]")
                                console.print(f"[blue]Debug: File content:\n{content}[/blue]")
                                raise ImportError(f"Start marker '{start_marker}' not found in {step_file_path}")
                            
                            end_idx = content.find(end_marker, start_idx)
                            if end_idx == -1:
                                console.print(f"[red]Error: End marker '{end_marker}' not found in file[/red]")
                                console.print(f"[blue]Debug: File content from start marker:\n{content[start_idx:]}[/blue]")
                                raise ImportError(f"End marker '{end_marker}' not found in {step_file_path}")
                            
                            # Extract the code between markers
                            code_block = content[start_idx + len(start_marker):end_idx].strip()
                            console.print(f"[blue]Debug: Extracted code block:\n{code_block}[/blue]")
                            
                            # Create a new module for execution
                            module_name = os.path.splitext(os.path.basename(step_file_path))[0]
                            package_name = os.path.basename(os.path.dirname(step_file_path))
                            parent_package = os.path.basename(os.path.dirname(os.path.dirname(step_file_path)))
                            console.print(f"[blue]Debug: Creating module {module_name} in package {package_name} (parent: {parent_package})[/blue]")
                            
                            # Add parent directory to Python path if not already there
                            parent_dir = os.path.dirname(os.path.dirname(step_file_path))
                            if parent_dir not in sys.path:
                                sys.path.insert(0, parent_dir)
                                console.print(f"[blue]Debug: Added parent directory {parent_dir} to Python path[/blue]")
                            
                            # Create module spec and module
                            spec = importlib.util.spec_from_file_location(f"{parent_package}.{package_name}.{module_name}", step_file_path)
                            if spec is None:
                                raise ImportError(f"Could not create module spec for {step_file_path}")
                            
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[spec.name] = module
                            
                            # Set up the module's namespace with proper package structure
                            module.__file__ = step_file_path
                            module.__package__ = f"{parent_package}.{package_name}"
                            module.__name__ = f"{parent_package}.{package_name}.{module_name}"
                            
                            # Create parent package modules if they don't exist
                            if parent_package not in sys.modules:
                                parent_spec = importlib.util.find_spec(parent_package)
                                if parent_spec:
                                    parent_module = importlib.util.module_from_spec(parent_spec)
                                    sys.modules[parent_package] = parent_module
                                    console.print(f"[blue]Debug: Created parent package module {parent_package}[/blue]")
                            
                            if f"{parent_package}.{package_name}" not in sys.modules:
                                package_spec = importlib.util.find_spec(f"{parent_package}.{package_name}")
                                if package_spec:
                                    package_module = importlib.util.module_from_spec(package_spec)
                                    sys.modules[f"{parent_package}.{package_name}"] = package_module
                                    console.print(f"[blue]Debug: Created package module {parent_package}.{package_name}[/blue]")
                            
                            # Now handle the imports
                            import_lines = []
                            for line in content.split('\n'):
                                if line.strip().startswith('from ') or line.strip().startswith('import '):
                                    # Convert relative imports to absolute imports
                                    if line.strip().startswith('from .'):
                                        # Replace relative import with absolute import
                                        line = line.replace('from .', f'from {parent_package}.{package_name}.')
                                    import_lines.append(line)
                                elif line.strip() and not line.strip().startswith('#'):
                                    break
                            
                            if import_lines:
                                import_code = '\n'.join(import_lines)
                                console.print(f"[blue]Debug: Executing imports:\n{import_code}[/blue]")
                                
                                # First, execute the code block to define the class
                                console.print("[blue]Debug: Executing code block first to define the class[/blue]")
                                exec(code_block, module.__dict__)
                                console.print(f"[blue]Debug: Module namespace after code block execution: {[k for k in module.__dict__.keys() if not k.startswith('_')]}[/blue]")
                                
                                # Then execute the imports
                                console.print("[blue]Debug: Now executing imports[/blue]")
                                try:
                                    # Import the required modules
                                    console.print(f"[blue]Debug: Importing prompt module[/blue]")
                                    prompt_module = importlib.import_module(f"{parent_package}.{package_name}.prompt")
                                    console.print(f"[blue]Debug: Importing utils module[/blue]")
                                    utils_module = importlib.import_module(f"{parent_package}.{package_name}.utils")
                                    
                                    # Add them to the module namespace
                                    console.print(f"[blue]Debug: Adding functions to module namespace[/blue]")
                                    module.__dict__['get_prompt'] = getattr(prompt_module, 'get_prompt')
                                    module.__dict__['call_gemini_llm'] = getattr(utils_module, 'call_gemini_llm')
                                    
                                    console.print(f"[blue]Debug: Successfully imported modules[/blue]")
                                except ImportError as e:
                                    console.print(f"[red]Error importing modules: {str(e)}[/red]")
                                    # Only log relevant modules in sys.modules
                                    relevant_modules = [k for k in sys.modules.keys() if k.startswith(parent_package)]
                                    console.print(f"[blue]Debug: Relevant modules in sys.modules: {relevant_modules}[/blue]")
                                    console.print(f"[blue]Debug: sys.path: {sys.path}[/blue]")
                                    # Fall back to executing the import code
                                    console.print("[blue]Debug: Falling back to executing import code[/blue]")
                                    exec(import_code, module.__dict__)
                                
                                console.print(f"[blue]Debug: Module namespace after imports: {[k for k in module.__dict__.keys() if not k.startswith('_')]}[/blue]")
                            
                            # Get the class from the module
                            console.print("[blue]Debug: Looking for class with run method in module namespace[/blue]")
                            console.print(f"[blue]Debug: Available names in module: {list(module.__dict__.keys())}[/blue]")
                            
                            class_name = None
                            for name, obj in module.__dict__.items():
                                if isinstance(obj, type) and hasattr(obj, 'run'):
                                    class_name = name
                                    console.print(f"[blue]Debug: Found class {name} with run method[/blue]")
                                    break
                                    
                            if class_name is None:
                                console.print("[red]Error: No class with run method found in module namespace[/red]")
                                raise ImportError(f"Could not find class with run method in the extracted code block")
                                
                            # Get the class and call its run method
                            console.print(f"[blue]Debug: Getting class {class_name} from module[/blue]")
                            cls = getattr(module, class_name)
                            
                            input_text = step.get('input', {}).get('input', '')
                            console.print(f"[blue]Debug: Calling run method with input: {input_text}[/blue]")
                            
                            if isinstance(cls.run, staticmethod):
                                output = str(cls.run(input_text))
                            else:
                                instance = cls()
                                output = str(instance.run(input_text))
                            
                            console.print(f"[blue]Debug: Run method output: {output}[/blue]")
                            
                            # Store the module in sys.modules to prevent it from being garbage collected
                            module_name = f"{parent_package}.{package_name}.{os.path.splitext(os.path.basename(step_file_path))[0]}"
                            sys.modules[module_name] = module
                            console.print(f"[blue]Debug: Stored module {module_name} in sys.modules[/blue]")
                            
                        except Exception as e:
                            console.print(f"[red]Error during execution: {str(e)}[/red]")
                            console.print(f"[blue]Debug: Exception type: {type(e).__name__}[/blue]")
                            import traceback
                            console.print(f"[blue]Debug: Traceback:\n{traceback.format_exc()}[/blue]")
                            raise
                        finally:
                            # Don't remove the paths, just log them
                            console.print(f"[blue]Debug: Current sys.path: {sys.path}[/blue]")
                            console.print(f"[blue]Debug: Current sys.modules keys: {list(sys.modules.keys())}[/blue]")
                        
                        console.print(f"[blue]Debug: Test block output: {output}[/blue]")
                    
                    # Use run_step to properly validate all test criteria
                    passed = self.run_step(step, agent_type, logger)
                    
                    # Store results by region
                    region = step.get('input', {}).get('region', 'default')
                    if region not in results:
                        results[region] = {
                            'test_cases': [],
                            'status': 'passed'  # Initialize status for each region
                        }
                    
                    # If we have an output and evaluator, evaluate it immediately
                    evaluation_result = None
                    if output and evaluator and 'evaluation' in self.test_config:
                        try:
                            # Create a temporary results structure for evaluation
                            temp_results = {
                                region: {
                                    'test_cases': [{
                                        'name': step_name,
                                        'input': step.get('input', {}),
                                        'output': output,
                                        'details': logger.get_last_step_details()
                                    }]
                                }
                            }
                            
                            # Run evaluation
                            evaluation_result = evaluator.evaluate(
                                results=temp_results,
                                criteria=self.test_config['evaluation'].get('criteria', [])
                            )
                            
                            # Update passed status based on evaluation
                            if isinstance(evaluation_result, dict):
                                if evaluation_result.get('status') == 'failed':
                                    passed = False
                                    all_steps_passed = False
                                    results[region]['status'] = 'failed'  # Update region status
                            elif isinstance(evaluation_result, str):
                                # If evaluation_result is a string, treat it as an error
                                passed = False
                                all_steps_passed = False
                                results[region]['status'] = 'failed'  # Update region status
                                evaluation_result = {
                                    'status': 'error',
                                    'error': evaluation_result
                                }
                                
                        except Exception as e:
                            logger.logger.error(f"Error during output evaluation: {str(e)}")
                            evaluation_result = {
                                'status': 'error',
                                'error': str(e)
                            }
                            results[region]['status'] = 'failed'  # Update region status
                    
                    # Add test case result
                    test_case = {
                        'name': step_name,
                        'input': step.get('input', {}),
                        'status': 'passed' if passed else 'failed',
                        'output': output,
                        'details': logger.get_last_step_details()
                    }
                    
                    # Add evaluation result if available
                    if evaluation_result:
                        test_case['evaluation'] = evaluation_result
                    
                    results[region]['test_cases'].append(test_case)
                    
                    # Update region status if test case failed
                    if not passed:
                        results[region]['status'] = 'failed'
                
                # Update overall status
                results['overall_status']['status'] = 'passed' if all_steps_passed else 'failed'
                
                if not all_steps_passed:
                    logger.logger.error("Test failed due to failed steps or evaluations")
                else:
                    logger.logger.info("All tests passed")
                
                # Save test results
                logger.save_results()
                
                return results
                
            except Exception as e:
                error_msg = f"Error running tests: {str(e)}"
                logger.logger.error(error_msg)
                results['overall_status']['status'] = 'failed'
                results['overall_status']['error'] = error_msg
                return results
            finally:
                # Clean up: remove the added path
                if parent_dir in sys.path:
                    sys.path.remove(parent_dir)
                    console.print(f"[blue]Debug: Removed {parent_dir} from Python path[/blue]")
            
        except Exception as e:
            error_msg = f"Error running tests: {str(e)}"
            logger.logger.error(error_msg)
            results['overall_status']['status'] = 'failed'
            results['overall_status']['error'] = error_msg
            return results 
            return results 