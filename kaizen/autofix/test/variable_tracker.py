"""Variable tracking for flexible output evaluation.

This module provides functionality to track variable assignments and values
during code execution, enabling evaluation of specific variables in addition
to return values.
"""

import sys
import logging
import json
from typing import Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class VariableSnapshot:
    """Snapshot of a variable's value at a specific point in execution."""
    name: str
    value: Any
    type: str
    timestamp: float
    line_number: Optional[int] = None

@dataclass
class ExecutionContext:
    """Context for tracking variables during execution."""
    variables: Dict[str, VariableSnapshot] = field(default_factory=dict)
    return_value: Optional[Any] = None
    tracked_names: Set[str] = field(default_factory=set)
    is_tracking: bool = False

class VariableTracker:
    """Tracks variable assignments and values during code execution."""
    
    def __init__(self):
        """Initialize the variable tracker."""
        self.context = ExecutionContext()
        self.original_trace = None
        self._setup_trace_function()
    
    def _setup_trace_function(self):
        """Set up the trace function for monitoring variable assignments."""
        def trace_function(frame, event, arg):
            if not self.context.is_tracking:
                return None
                
            if event == 'line':
                # Track variable assignments on each line
                self._track_line_variables(frame)
            elif event == 'return':
                # Track return values
                self._track_return_value(arg)
                
            return trace_function
        
        self.trace_function = trace_function
    
    def _track_line_variables(self, frame):
        """Track variables on the current line."""
        try:
            # Get local variables from the frame
            local_vars = frame.f_locals
            
            for var_name, value in local_vars.items():
                # Only track variables we're interested in
                if var_name in self.context.tracked_names:
                    self._record_variable(var_name, value, frame.f_lineno)
                    
        except Exception as e:
            logger.debug(f"Error tracking line variables: {str(e)}")
    
    def _track_return_value(self, return_value):
        """Track the return value of a function."""
        try:
            self.context.return_value = return_value
        except Exception as e:
            logger.debug(f"Error tracking return value: {str(e)}")
    
    def _record_variable(self, name: str, value: Any, line_number: Optional[int] = None):
        """Record a variable's value."""
        try:
            import time
            snapshot = VariableSnapshot(
                name=name,
                value=value,
                type=type(value).__name__,
                timestamp=time.time(),
                line_number=line_number
            )
            self.context.variables[name] = snapshot
            logger.debug(f"Tracked variable '{name}': {value} (type: {type(value).__name__})")
        except Exception as e:
            logger.debug(f"Error recording variable '{name}': {str(e)}")
    
    def start_tracking(self, variable_names: Set[str]):
        """Start tracking specific variables.
        
        Args:
            variable_names: Set of variable names to track
        """
        self.context.tracked_names = variable_names
        self.context.is_tracking = True
        self.context.variables.clear()
        self.context.return_value = None
        
        # Install trace function
        self.original_trace = sys.gettrace()
        sys.settrace(self.trace_function)
        
        logger.debug(f"Started tracking variables: {variable_names}")
    
    def stop_tracking(self):
        """Stop tracking variables."""
        self.context.is_tracking = False
        
        # Restore original trace function
        if self.original_trace is not None:
            sys.settrace(self.original_trace)
            self.original_trace = None
        
        logger.debug("Stopped tracking variables")
    
    def get_variable_value(self, name: str) -> Optional[Any]:
        """Get the value of a tracked variable.
        
        Args:
            name: Name of the variable
            
        Returns:
            The variable's value or None if not found
        """
        if name in self.context.variables:
            return self.context.variables[name].value
        return None
    
    def get_return_value(self) -> Optional[Any]:
        """Get the return value from the tracked execution.
        
        Returns:
            The return value or None if not available
        """
        return self.context.return_value
    
    def get_all_tracked_values(self) -> Dict[str, Any]:
        """Get all tracked variable values and return value.
        
        Returns:
            Dictionary containing all tracked values
        """
        result = {}
        
        # Add variable values
        for name, snapshot in self.context.variables.items():
            result[name] = snapshot.value
        
        # Add return value
        if self.context.return_value is not None:
            result['return'] = self.context.return_value
        
        return result
    
    def clear(self):
        """Clear all tracked data."""
        self.context.variables.clear()
        self.context.return_value = None
        self.context.tracked_names.clear()
        self.context.is_tracking = False

@contextmanager
def track_variables(variable_names: Set[str]):
    """Context manager for tracking variables during execution.
    
    Args:
        variable_names: Set of variable names to track
        
    Yields:
        VariableTracker instance
    """
    tracker = VariableTracker()
    try:
        tracker.start_tracking(variable_names)
        yield tracker
    finally:
        tracker.stop_tracking()

def safe_serialize_value(value: Any) -> str:
    """Safely serialize a value to string for LLM evaluation.
    
    Args:
        value: The value to serialize
        
    Returns:
        String representation of the value
    """
    try:
        if value is None:
            return "None"
        elif isinstance(value, (str, int, float, bool)):
            return str(value)
        elif isinstance(value, (list, tuple)):
            return json.dumps(value, default=str, indent=2)
        elif isinstance(value, dict):
            return json.dumps(value, default=str, indent=2)
        else:
            # For dataclass objects, convert to dict first
            if hasattr(value, '__dataclass_fields__'):
                try:
                    from dataclasses import asdict
                    return json.dumps(asdict(value), default=str, indent=2)
                except Exception as e:
                    logger.warning(f"Error converting dataclass to dict: {str(e)}")
                    return str(value)
            # For other complex objects, try to get a meaningful representation
            try:
                return str(value)
            except:
                return f"<{type(value).__name__} object>"
    except Exception as e:
        logger.warning(f"Error serializing value: {str(e)}")
        return f"<Error serializing {type(value).__name__}: {str(e)}>" 