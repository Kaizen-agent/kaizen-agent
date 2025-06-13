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

console = Console()

def create_execution_namespace() -> Dict[str, Any]:
    """
    Create a namespace with commonly used imports and utilities.
    
    Returns:
        Dict[str, Any]: A dictionary containing the execution namespace
    """
    # Get all built-in modules
    builtins = {name: module for name, module in sys.modules.items() 
               if name in sys.stdlib_module_names}
    
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
        str: The execution output
    """
    output = io.StringIO()
    
    try:
        # Parse the block to determine its type
        block_ast = ast.parse(block_code)
        
        with redirect_stdout(output):
            # Execute the block in the namespace
            exec(block_code, namespace)
            
            # Check if it's a function or class
            if len(block_ast.body) == 1:
                node = block_ast.body[0]
                
                if isinstance(node, ast.FunctionDef):
                    # It's a function, call it with test_input
                    func_name = node.name
                    if func_name in namespace:
                        result = namespace[func_name](test_input)
                        if result is not None:
                            print(result)
                            
                elif isinstance(node, ast.ClassDef):
                    # It's a class, instantiate and call reply if present
                    class_name = node.name
                    if class_name in namespace:
                        instance = namespace[class_name]()
                        if hasattr(instance, 'reply'):
                            result = instance.reply(test_input)
                            if result is not None:
                                print(result)
                                
        return output.getvalue().strip()
        
    except SyntaxError as e:
        return f"Error: Invalid Python syntax in block: {str(e)}"
    except Exception as e:
        return f"Error executing code block: {str(e)}"

def run_test_block(file_path: str, test_input: Optional[str] = None, region: Optional[str] = None) -> str:
    """
    Execute a code block between kaizen markers in a Python file.
    
    Args:
        file_path (str): Path to the Python file
        test_input (Optional[str]): Input to pass to the function/class if applicable
        region (Optional[str]): Name of the region to extract (e.g., 'email_agent')
        
    Returns:
        str: Output from the code block execution or error message
    """
    try:
        # Read the full file
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Create execution namespace with all necessary imports
        namespace = create_execution_namespace()
        
        # Add imports from the file to the namespace
        try:
            # Execute imports first
            import_lines = []
            for line in content.split('\n'):
                if line.startswith('import ') or line.startswith('from '):
                    import_lines.append(line)
                elif line.strip() and not line.startswith('#'):
                    break
            
            if import_lines:
                exec('\n'.join(import_lines), namespace)
            
            # Now execute the full file
            exec(content, namespace)
        except Exception as e:
            return f"Error setting up imports: {str(e)}"
        
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
            return f"Error: Start marker '{start_marker}' not found"
            
        end_idx = content.find(end_marker, start_idx)
        if end_idx == -1:
            return f"Error: End marker '{end_marker}' not found"
            
        # Extract the block code
        block_code = content[start_idx + len(start_marker):end_idx].strip()
        
        # Execute the block
        return execute_code_block(block_code, namespace, test_input)
        
    except Exception as e:
        return f"Error executing code block: {str(e)}"

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
        # Load environment variables
        load_dotenv()
        
        # Merge with test config if provided
        if self.test_config:
            self.config = {**self.test_config}
        else:
            self.config = {}

    def _validate_api_keys(self):
        """Validate that required API keys are present."""
        # OpenAI API key is always required
        if not os.getenv('OPENAI_API_KEY'):
            console.print("[red]Error: Missing required API key: OPENAI_API_KEY[/red]")
            console.print("Please add it to your .env file or environment variables")
            sys.exit(1)

        # Anthropic API key is optional - only warn if not present
        if not os.getenv('ANTHROPIC_API_KEY'):
            console.print("[yellow]Note: ANTHROPIC_API_KEY not found - Anthropic-based tests will use OpenAI instead[/yellow]")

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

                # Run the agent
                result = runner.run(input_data)
                
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
        results = {}
        
        # Get the agent type from config
        agent_type = self.test_config.get('agent_type', 'dynamic_region')
        
        # Create logger
        logger = TestLogger(self.test_config.get('name', 'Unnamed Test'))
        
        # Run each test step
        for step in self.test_config.get('steps', []):
            step_index = step.get('step_index')
            step_name = step.get('name', f'Step {step_index}')
            
            logger.log_step_start(step_index, step.get('input', {}))
            
            # Run the step
            passed = self.run_step(step, agent_type, logger)
            
            # Log the result
            logger.log_step_result(
                step_index,
                {'status': 'passed' if passed else 'failed'},
                passed
            )
            
            # Store results by region
            region = step.get('input', {}).get('region', 'default')
            if region not in results:
                results[region] = {'test_cases': []}
            
            results[region]['test_cases'].append({
                'name': step_name,
                'status': 'passed' if passed else 'failed'
            })
        
        # Save test results
        logger.save_results()
        
        return results 