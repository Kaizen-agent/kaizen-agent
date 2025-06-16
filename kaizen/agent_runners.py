"""
Agent registry and base runner implementation.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional, List, Union, TypeVar, Callable, Sequence, Mapping, Set, FrozenSet, Tuple
from .code_region import extract_code_regions
from .logger import TestLogger
import json
import os
import time
import openai
from .config import Config
import importlib.util
import sys
import types
from pathlib import Path
import io
from contextlib import redirect_stdout
import ast

class AgentRunner(ABC):
    """Base class for all agent runners."""
    
    def __init__(self, config: Dict[str, Any] = None, logger: Optional[TestLogger] = None):
        self.config = config or {}
        self.logger = logger or TestLogger("AgentRunner")
    
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent with the given input data."""
        if self.logger:
            self.logger.logger.debug("Starting agent run")
            self.logger.logger.debug(f"Input data: {input_data}")
        
        # Skip region extraction for dynamic runners
        if isinstance(self, DynamicRegionRunner):
            return self.process_code(input_data)
        
        # Extract code regions if specified
        code = input_data.get('code', '')
        language = input_data.get('language', 'python')
        
        if self.logger:
            self.logger.logger.debug(f"Extracting code regions with language: {language}")
        regions = extract_code_regions(code, language, self.logger)
        if not regions:
            error_msg = f"Could not extract code regions with language: {language}"
            if self.logger:
                self.logger.logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
        
        # Update input data with processed regions
        input_data['regions'] = regions
        
        # Call the specific implementation
        return self.process_code(input_data)
    
    @abstractmethod
    def process_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the code and return results. To be implemented by specific agents."""
        pass

class AgentRegistry:
    """Registry for managing different types of agent runners."""
    
    def __init__(self):
        self._runners: Dict[str, Type[AgentRunner]] = {}

    def register(self, agent_type: str, runner_class: Type[AgentRunner]):
        """Register a new agent runner type."""
        self._runners[agent_type] = runner_class

    def get_runner(self, agent_type: str) -> Optional[AgentRunner]:
        """Get an instance of the runner for the given agent type."""
        runner_class = self._runners.get(agent_type)
        if runner_class:
            return runner_class()
        return None

# Example Python agent runner
class PythonAgentRunner(AgentRunner):
    """Runner for Python-based agents."""
    
    def process_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Python code and return analysis results."""
        regions = input_data.get('regions', {})
        context = input_data.get('context', {})
        
        if self.logger:
            self.logger.logger.debug("Processing Python code")
            self.logger.logger.debug(f"Regions: {list(regions.keys())}")
            self.logger.logger.debug(f"Context: {context}")
        
        # Process each region
        results = {}
        for region_name, region_code in regions.items():
            self.logger.logger.debug(f"Processing region: {region_name}")
            result = self.process_code(region_code, context)
            results[region_name] = result
        
        return {
            "status": "success",
            "results": results
        }
    
    def process_code(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process Python code and return analysis results."""
        # Here you would implement the actual code analysis
        # For now, we'll return a simple analysis
        return {
            "type": "python_analysis",
            "code_length": len(code),
            "has_functions": "def " in code,
            "has_classes": "class " in code
        }

# Example TypeScript agent runner
class TypeScriptAgentRunner(AgentRunner):
    """Runner for TypeScript-based agents."""
    
    def process_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process TypeScript code and return analysis results."""
        regions = input_data.get('regions', {})
        context = input_data.get('context', {})
        
        if self.logger:
            self.logger.logger.debug("Processing TypeScript code")
            self.logger.logger.debug(f"Regions: {list(regions.keys())}")
            self.logger.logger.debug(f"Context: {context}")
        
        # Process each region
        results = {}
        for region_name, region_code in regions.items():
            self.logger.logger.debug(f"Processing region: {region_name}")
            result = self.process_code(region_code, context)
            results[region_name] = result
        
        return {
            "status": "success",
            "results": results
        }
    
    def process_code(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process TypeScript code and return analysis results."""
        # Here you would implement the actual code analysis
        # For now, we'll return a simple analysis
        return {
            "type": "typescript_analysis",
            "code_length": len(code),
            "has_functions": "function " in code,
            "has_classes": "class " in code,
            "has_interfaces": "interface " in code
        }

# Register default runners
registry = AgentRegistry()
registry.register("python", PythonAgentRunner)
registry.register("typescript", TypeScriptAgentRunner)

class LLMSearchAgent:
    """Agent that uses OpenAI for code search capabilities."""
    
    def __init__(self, logger: Optional[TestLogger] = None):
        self.config = Config()
        self.api_key = self.config.get_api_key("openai")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please add it to your .env file.")
        
        self.logger = logger or TestLogger("AgentRunner")
        self._setup_provider()
    
    def _setup_provider(self):
        """Set up the OpenAI client."""
        openai.api_key = self.api_key
    
    def search(self, query: str, language: str) -> Dict[str, Any]:
        """Search for code examples using OpenAI."""
        start_time = time.time()
        self.logger.logger.info("=== LLMSearchAgent: Starting search ===")
        self.logger.logger.debug(f"Searching for: {query} in {language}")
        
        try:
            # Create the prompt for code search
            prompt = self._create_search_prompt(query, language)
            
            # Get response from OpenAI
            response = self._get_llm_response(prompt)
            
            # Parse and structure the results
            results = self._parse_search_results(response)
            
            end_time = time.time()
            self.logger.logger.info(f"=== LLMSearchAgent: Search completed in {end_time - start_time:.2f}s ===")
            
            return {
                "status": "success",
                "results": results,
                "metadata": {
                    "execution_time": end_time - start_time,
                    "query": query,
                    "language": language,
                    "results_count": len(results),
                    "provider": "openai"
                }
            }
            
        except Exception as e:
            end_time = time.time()
            self.logger.logger.error(f"Error in LLMSearchAgent: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "metadata": {
                    "execution_time": end_time - start_time,
                    "query": query,
                    "language": language,
                    "provider": "openai"
                }
            }
    
    def _create_search_prompt(self, query: str, language: str) -> str:
        """Create a prompt for code search."""
        return f"""You are an expert code search assistant. Search for code examples that match the following query:

Query: {query}
Language: {language}

Please provide code examples that:
1. Match the query intent
2. Follow best practices for {language}
3. Include clear explanations
4. Are well-documented

Format your response as a JSON array of objects with the following structure:
[
    {{
        "code": "the code example",
        "description": "explanation of what the code does",
        "best_practices": ["list of best practices demonstrated"],
        "complexity": "time/space complexity if applicable"
    }}
]"""
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get response from OpenAI."""
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert code search assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content
    
    def _parse_search_results(self, response: str) -> List[Dict[str, Any]]:
        """Parse the OpenAI response into structured results."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.logger.error("Failed to parse OpenAI response as JSON")
            return []

class LLMAnalysisAgent:
    """Agent that uses OpenAI for code analysis."""
    
    def __init__(self, logger: Optional[TestLogger] = None):
        self.config = Config()
        self.api_key = self.config.get_api_key("openai")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please add it to your .env file.")
        
        self.logger = logger or TestLogger("AgentRunner")
        self._setup_provider()
    
    def _setup_provider(self):
        """Set up the OpenAI client."""
        openai.api_key = self.api_key
    
    def analyze(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code using OpenAI."""
        start_time = time.time()
        self.logger.logger.info("=== LLMAnalysisAgent: Starting analysis ===")
        self.logger.logger.debug(f"Analyzing code in {language}")
        
        try:
            # Create the prompt for code analysis
            prompt = self._create_analysis_prompt(code, language)
            
            # Get response from OpenAI
            response = self._get_llm_response(prompt)
            
            # Parse and structure the analysis
            analysis = self._parse_analysis_results(response)
            
            end_time = time.time()
            self.logger.logger.info(f"=== LLMAnalysisAgent: Analysis completed in {end_time - start_time:.2f}s ===")
            
            return {
                "status": "success",
                "analysis": analysis,
                "metadata": {
                    "execution_time": end_time - start_time,
                    "language": language,
                    "provider": "openai",
                    "analysis_type": "llm"
                }
            }
            
        except Exception as e:
            end_time = time.time()
            self.logger.logger.error(f"Error in LLMAnalysisAgent: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "metadata": {
                    "execution_time": end_time - start_time,
                    "language": language,
                    "provider": "openai"
                }
            }
    
    def _create_analysis_prompt(self, code: str, language: str) -> str:
        """Create a prompt for code analysis."""
        return f"""You are an expert code analyzer. Analyze the following code:

Language: {language}
Code:
```{language}
{code}
```

Please provide a detailed analysis including:
1. Code structure (functions, classes, etc.)
2. Code quality assessment
3. Potential issues or improvements
4. Best practices followed or missing
5. Performance considerations
6. Security considerations

Format your response as a JSON object with the following structure:
{{
    "structure": {{
        "has_functions": boolean,
        "has_classes": boolean,
        "function_count": number,
        "class_count": number,
        "code_length": number
    }},
    "quality": {{
        "score": number (0-100),
        "strengths": ["list of strengths"],
        "weaknesses": ["list of weaknesses"]
    }},
    "issues": ["list of potential issues"],
    "improvements": ["list of suggested improvements"],
    "best_practices": {{
        "followed": ["list of followed best practices"],
        "missing": ["list of missing best practices"]
    }},
    "performance": {{
        "complexity": "time/space complexity analysis",
        "bottlenecks": ["list of potential bottlenecks"]
    }},
    "security": {{
        "vulnerabilities": ["list of potential security issues"],
        "recommendations": ["list of security recommendations"]
    }}
}}"""
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get response from OpenAI."""
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert code analyzer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content
    
    def _parse_analysis_results(self, response: str) -> Dict[str, Any]:
        """Parse the OpenAI response into structured analysis results."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.logger.error("Failed to parse OpenAI response as JSON")
            return {
                "error": "Failed to parse analysis results",
                "raw_response": response
            }

class DynamicRegionRunner(AgentRunner):
    """Runner for dynamically executing code regions."""
    
    def __init__(self, logger: Optional[TestLogger] = None):
        super().__init__(logger=logger)
    
    def process_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process code regions and execute them."""
        try:
            file_path = input_data.get('file_path')
            if not file_path:
                return {
                    "status": "error",
                    "error": "No file path provided"
                }

            # Read the code from the file
            with open(file_path, 'r') as f:
                code = f.read()

            # Create a new namespace for execution with proper module attributes
            namespace = {
                '__name__': '__main__',
                '__file__': file_path,
                '__package__': None,
                '__builtins__': __builtins__
            }

            # Add the file's directory to Python path
            file_dir = os.path.dirname(os.path.abspath(file_path))
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)

            try:
                # Parse imports using AST
                tree = ast.parse(code)
                import_lines = []
                
                # Extract all import statements
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        import_lines.append(ast.unparse(node))
                
                if import_lines:
                    import_block = '\n'.join(import_lines)
                    exec(import_block, namespace)

                # Force reload of the module if it exists
                module_name = Path(file_path).stem
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                
                # Extract the specified region
                region = input_data.get('region')
                if region:
                    start_marker = f'# kaizen:start:{region}'
                    end_marker = f'# kaizen:end:{region}'
                else:
                    start_marker = '# kaizen:start'
                    end_marker = '# kaizen:end'
                
                start_idx = code.find(start_marker)
                if start_idx == -1:
                    return {
                        "status": "error",
                        "error": f"Start marker '{start_marker}' not found"
                    }
                
                end_idx = code.find(end_marker, start_idx)
                if end_idx == -1:
                    return {
                        "status": "error",
                        "error": f"End marker '{end_marker}' not found"
                    }
                
                # Extract the code block
                block_code = code[start_idx + len(start_marker):end_idx].strip()
                
                # Execute either the full file or just the block based on whether a region was specified
                if not region:
                    # If no specific region was requested, execute the full file
                    exec(code, namespace)
                else:
                    # If a specific region was requested, only execute that block
                    exec(block_code, namespace)
                
                # If a method is specified, call it with the input
                method = input_data.get('method')
                test_input = input_data.get('input')
                
                if method and test_input is not None:
                    # Find the class in the namespace
                    class_name = None
                    for name, obj in namespace.items():
                        if isinstance(obj, type) and hasattr(obj, method):
                            class_name = name
                            break
                    
                    if class_name:
                        # Instantiate the class
                        instance = namespace[class_name]()
                        # Call the method
                        result = getattr(instance, method)(test_input)
                        return {
                            "status": "success",
                            "output": str(result)
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"Class with method '{method}' not found in namespace"
                        }
                
                return {
                    "status": "success",
                    "output": "Region executed successfully"
                }
                
            finally:
                # Clean up: remove the added path
                if file_dir in sys.path:
                    sys.path.remove(file_dir)
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            } 