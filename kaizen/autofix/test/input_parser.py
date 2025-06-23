"""Input parsing for test runner with support for multiple input types.

This module provides functionality to parse multiple inputs from YAML configuration
with support for different types: string, dict, and object (with dynamic imports).
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
import pickle

logger = logging.getLogger(__name__)

@dataclass
class InputDefinition:
    """Definition of a single input item.
    
    Attributes:
        name: Optional name for the input (for internal use)
        type: Type of input ('string', 'dict', 'object', 'class_object', 'inline_object')
              Note: 'str' is supported as an alias for 'string' for backward compatibility
        value: Direct value for string/dict types
        class_path: Python import path for object types
        args: Arguments for object instantiation
        pickle_path: Path to a pickled object (for class_object)
        import_path: Python import path to a variable/object (for class_object)
        attributes: Dictionary of attributes for inline_object type
    """
    name: Optional[str]
    type: str
    value: Optional[Any] = None
    class_path: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    pickle_path: Optional[str] = None
    import_path: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

class InputParsingError(Exception):
    """Exception raised when input parsing fails."""
    pass

class InputParser:
    """Parser for multiple input definitions from YAML configuration.
    
    Supports the following input types:
    - 'string' (or 'str' as alias): String values
    - 'dict': Dictionary values  
    - 'object': Objects instantiated from class paths
    - 'class_object': Objects loaded from pickle files or imported from modules
    - 'inline_object': Objects with attributes specified directly in YAML
    
    Provides backward compatibility for type aliases (e.g., 'str' -> 'string').
    """
    
    def __init__(self):
        """Initialize the input parser."""
        self.supported_types = {'string', 'dict', 'object', 'class_object', 'inline_object'}
        # Add backward compatibility for 'str' type
        self.type_aliases = {'str': 'string'}
    
    def parse_inputs(self, input_config: Union[List[Dict[str, Any]], Dict[str, Any], Any]) -> List[Any]:
        """Parse input configuration into a list of input objects.
        
        Args:
            input_config: Input configuration from YAML. Can be:
                - List of input definitions
                - Single input definition dict
                - Direct value (for backward compatibility)
                
        Returns:
            List of parsed input objects
            
        Raises:
            InputParsingError: If parsing fails
        """
        logger.debug(f"DEBUG: InputParser.parse_inputs received: {input_config}")
        logger.debug(f"DEBUG: InputParser.parse_inputs type: {type(input_config)}")
        
        try:
            # Handle backward compatibility: single value
            if not isinstance(input_config, (list, dict)):
                logger.debug(f"Single input value detected: {input_config}")
                return [input_config]
            
            # If it's a dict with a 'type' key, treat as input definition (even if type is invalid)
            if isinstance(input_config, dict) and 'type' in input_config:
                # Handle type aliases for backward compatibility
                input_type = input_config['type']
                if input_type in self.type_aliases:
                    logger.debug(f"Converting type alias '{input_type}' to '{self.type_aliases[input_type]}'")
                    input_config = input_config.copy()
                    input_config['type'] = self.type_aliases[input_type]
                
                if input_config['type'] not in self.supported_types:
                    raise InputParsingError(f"Unsupported input type: {input_config['type']}. Supported types: {self.supported_types}")
                logger.debug(f"Single input definition detected: {input_config}")
                return [self._parse_single_input(input_config)]
            
            # Handle backward compatibility: single dict (not an input definition)
            if isinstance(input_config, dict):
                logger.debug(f"Single input dict detected: {input_config}")
                return [input_config]
            
            # Handle list of input definitions
            if isinstance(input_config, list):
                logger.debug(f"Multiple input definitions detected: {len(input_config)} items")
                logger.debug(f"DEBUG: InputParser.parse_inputs processing list with {len(input_config)} items")
                for i, item in enumerate(input_config):
                    logger.debug(f"DEBUG: InputParser.parse_inputs item {i}: {item} (type: {type(item)})")
                return self._parse_input_list(input_config)
            
            # Fallback: treat as direct value
            logger.debug(f"Treating as direct value: {input_config}")
            return [input_config]
            
        except Exception as e:
            raise InputParsingError(f"Failed to parse input configuration: {str(e)}")
    
    def _is_input_definition(self, config: Dict[str, Any]) -> bool:
        """Check if a dict represents an input definition.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if it's an input definition, False otherwise
        """
        return (
            isinstance(config, dict) and
            'type' in config and
            (config['type'] in self.supported_types or config['type'] in self.type_aliases)
        )
    
    def _parse_input_list(self, input_list: List[Dict[str, Any]]) -> List[Any]:
        """Parse a list of input definitions.
        
        Args:
            input_list: List of input definition dictionaries
            
        Returns:
            List of parsed input objects
        """
        parsed_inputs = []
        
        for i, input_def in enumerate(input_list):
            try:
                if not isinstance(input_def, dict):
                    raise InputParsingError(f"Input definition {i} must be a dictionary")
                
                parsed_input = self._parse_single_input(input_def)
                parsed_inputs.append(parsed_input)
                
            except Exception as e:
                raise InputParsingError(f"Failed to parse input definition {i}: {str(e)}")
        
        return parsed_inputs
    
    def _parse_single_input(self, input_def: Dict[str, Any]) -> Any:
        """Parse a single input definition.
        
        Args:
            input_def: Input definition dictionary
            
        Returns:
            Parsed input object
            
        Raises:
            InputParsingError: If parsing fails
        """
        # Validate required fields
        if 'type' not in input_def:
            raise InputParsingError("Input definition must contain 'type' field")
        
        input_type = input_def['type']
        
        # Handle type aliases for backward compatibility
        if input_type in self.type_aliases:
            logger.debug(f"Converting type alias '{input_type}' to '{self.type_aliases[input_type]}'")
            input_type = self.type_aliases[input_type]
            input_def = input_def.copy()
            input_def['type'] = input_type
        
        if input_type not in self.supported_types:
            raise InputParsingError(f"Unsupported input type: {input_type}. Supported types: {self.supported_types}")
        
        # Parse based on type
        if input_type == 'string':
            return self._parse_string_input(input_def)
        elif input_type == 'dict':
            return self._parse_dict_input(input_def)
        elif input_type == 'object':
            return self._parse_object_input(input_def)
        elif input_type == 'class_object':
            return self._parse_class_object_input(input_def)
        elif input_type == 'inline_object':
            return self._parse_inline_object_input(input_def)
        else:
            raise InputParsingError(f"Unknown input type: {input_type}")
    
    def _parse_string_input(self, input_def: Dict[str, Any]) -> str:
        """Parse a string input definition.
        
        Args:
            input_def: Input definition dictionary
            
        Returns:
            String value
            
        Raises:
            InputParsingError: If parsing fails
        """
        if 'value' not in input_def:
            raise InputParsingError("String input must contain 'value' field")
        
        value = input_def['value']
        if not isinstance(value, str):
            raise InputParsingError(f"String input value must be a string, got {type(value).__name__}")
        
        logger.debug(f"Parsed string input: {value}")
        return value
    
    def _parse_dict_input(self, input_def: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a dict input definition.
        
        Args:
            input_def: Input definition dictionary
            
        Returns:
            Dictionary value
            
        Raises:
            InputParsingError: If parsing fails
        """
        if 'value' not in input_def:
            raise InputParsingError("Dict input must contain 'value' field")
        
        value = input_def['value']
        if not isinstance(value, dict):
            raise InputParsingError(f"Dict input value must be a dictionary, got {type(value).__name__}")
        
        logger.debug(f"Parsed dict input: {value}")
        return value
    
    def _parse_object_input(self, input_def: Dict[str, Any]) -> Any:
        """Parse an object input definition with dynamic import.
        
        Args:
            input_def: Input definition dictionary
            
        Returns:
            Instantiated object
            
        Raises:
            InputParsingError: If parsing fails
        """
        if 'class_path' not in input_def:
            raise InputParsingError("Object input must contain 'class_path' field")
        
        class_path = input_def['class_path']
        args = input_def.get('args', {})
        
        if not isinstance(args, dict):
            raise InputParsingError(f"Object input args must be a dictionary, got {type(args).__name__}")
        
        try:
            # Import the class
            cls = self._import_class(class_path)
            
            # Instantiate with args
            instance = cls(**args)
            
            logger.debug(f"Parsed object input: {class_path} with args {args}")
            return instance
            
        except Exception as e:
            raise InputParsingError(f"Failed to instantiate object from {class_path}: {str(e)}")
    
    def _parse_class_object_input(self, input_def: Dict[str, Any]) -> Any:
        """Parse a class object input definition.
        Supports loading from a pickle file or importing a variable from a module.
        """
        if 'pickle_path' in input_def:
            pickle_path = input_def['pickle_path']
            try:
                with open(pickle_path, 'rb') as f:
                    obj = pickle.load(f)
                logger.debug(f"Loaded class object from pickle: {pickle_path}")
                return obj
            except Exception as e:
                raise InputParsingError(f"Failed to load class object from pickle: {pickle_path}: {str(e)}")
        elif 'import_path' in input_def:
            import_path = input_def['import_path']
            try:
                obj = self._import_variable(import_path)
                logger.debug(f"Imported class object from path: {import_path}")
                return obj
            except Exception as e:
                raise InputParsingError(f"Failed to import class object from path: {import_path}: {str(e)}")
        else:
            raise InputParsingError("class_object input must contain either 'pickle_path' or 'import_path' field")
    
    def _parse_inline_object_input(self, input_def: Dict[str, Any]) -> Any:
        """Parse an inline object input definition.
        
        This allows users to specify a class object directly in YAML with its attributes,
        making it easier than loading from files.
        
        Args:
            input_def: Input definition dictionary with 'class_path' and 'attributes'
            
        Returns:
            Instantiated object with the specified attributes
            
        Raises:
            InputParsingError: If parsing fails
        """
        if 'class_path' not in input_def:
            raise InputParsingError("Inline object input must contain 'class_path' field")
        
        if 'attributes' not in input_def:
            raise InputParsingError("Inline object input must contain 'attributes' field")
        
        class_path = input_def['class_path']
        attributes = input_def['attributes']
        
        if not isinstance(attributes, dict):
            raise InputParsingError(f"Inline object attributes must be a dictionary, got {type(attributes).__name__}")
        
        try:
            # Import the class
            cls = self._import_class(class_path)
            
            # Instantiate with attributes
            instance = cls(**attributes)
            
            logger.debug(f"Parsed inline object: {class_path} with attributes {attributes}")
            return instance
            
        except Exception as e:
            raise InputParsingError(f"Failed to instantiate inline object from {class_path}: {str(e)}")
    
    def _import_class(self, class_path: str) -> type:
        """Dynamically import a class from a module path.
        
        Args:
            class_path: Python import path (e.g., 'agents.types.ChemistFeedback')
            
        Returns:
            The imported class
            
        Raises:
            InputParsingError: If import fails
        """
        try:
            # Split the path into module and class name
            if '.' not in class_path:
                raise InputParsingError(f"Invalid class path: {class_path}. Expected format: 'module.submodule.ClassName'")
            
            module_path, class_name = class_path.rsplit('.', 1)
            
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the class
            if not hasattr(module, class_name):
                raise InputParsingError(f"Class '{class_name}' not found in module '{module_path}'")
            
            cls = getattr(module, class_name)
            
            # Verify it's a class
            if not isinstance(cls, type):
                raise InputParsingError(f"'{class_name}' is not a class in module '{module_path}'")
            
            return cls
            
        except ImportError as e:
            raise InputParsingError(f"Failed to import module for class path '{class_path}': {str(e)}")
        except Exception as e:
            raise InputParsingError(f"Failed to import class '{class_path}': {str(e)}")
    
    def _import_variable(self, import_path: str) -> Any:
        """Import a variable/object from a module path (e.g., 'my_module.MY_OBJECT')."""
        try:
            if '.' not in import_path:
                raise InputParsingError(f"Invalid import path: {import_path}. Expected format: 'module.submodule.VAR'")
            module_path, var_name = import_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            if not hasattr(module, var_name):
                raise InputParsingError(f"Variable '{var_name}' not found in module '{module_path}'")
            return getattr(module, var_name)
        except ImportError as e:
            raise InputParsingError(f"Failed to import module for import path '{import_path}': {str(e)}")
        except Exception as e:
            raise InputParsingError(f"Failed to import variable '{import_path}': {str(e)}")

def build_inputs_from_yaml(yaml_input_list: List[Dict[str, Any]]) -> List[Any]:
    """Helper function to build inputs from YAML configuration.
    
    Args:
        yaml_input_list: List of input definitions from YAML
        
    Returns:
        List of parsed input objects
        
    Raises:
        InputParsingError: If parsing fails
    """
    parser = InputParser()
    return parser.parse_inputs(yaml_input_list) 