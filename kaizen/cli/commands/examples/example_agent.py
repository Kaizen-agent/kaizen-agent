"""
Example agent demonstrating the new entry point system without markers.

This agent can be tested using the agent_entry_point_example.yaml configuration
without requiring any special markers in the code.
"""

from typing import Dict, Any, List, Optional
import json


class ExampleAgent:
    """Example agent that processes various types of input data."""
    
    def __init__(self):
        """Initialize the agent."""
        self.processed_result = None
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0
        }
    
    def process_input(self, input_data: Any) -> Dict[str, Any]:
        """Process input data and return results.
        
        Args:
            input_data: Input data to process (string, dict, or list)
            
        Returns:
            Dictionary containing processing results
        """
        try:
            self.processing_stats['total_processed'] += 1
            
            # Handle different input types
            if isinstance(input_data, str):
                result = self._process_string_input(input_data)
            elif isinstance(input_data, dict):
                result = self._process_dict_input(input_data)
            elif isinstance(input_data, list):
                result = self._process_list_input(input_data)
            else:
                result = self._process_unknown_input(input_data)
            
            # Store the processed result for evaluation
            self.processed_result = result
            self.processing_stats['successful'] += 1
            
            return {
                'status': 'success',
                'result': result,
                'stats': self.processing_stats
            }
            
        except Exception as e:
            self.processing_stats['failed'] += 1
            return {
                'status': 'error',
                'error': str(e),
                'stats': self.processing_stats
            }
    
    def _process_string_input(self, text: str) -> str:
        """Process string input."""
        return f"Processed string: {text.upper()}"
    
    def _process_dict_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dictionary input."""
        if 'items' in data and 'operation' in data:
            items = data['items']
            operation = data['operation']
            
            if operation == 'sum':
                result = sum(items) if isinstance(items, list) else 0
            elif operation == 'count':
                result = len(items) if isinstance(items, list) else 0
            else:
                result = f"Unknown operation: {operation}"
            
            return {
                'operation': operation,
                'items': items,
                'result': result
            }
        else:
            return {
                'message': 'Dictionary processed',
                'data': data
            }
    
    def _process_list_input(self, items: List[Any]) -> Dict[str, Any]:
        """Process list input."""
        return {
            'count': len(items),
            'sum': sum(items) if all(isinstance(x, (int, float)) for x in items) else None,
            'items': items
        }
    
    def _process_unknown_input(self, data: Any) -> str:
        """Process unknown input type."""
        return f"Unknown input type: {type(data).__name__}"


# Example function that can also be used as an entry point
def process_data_function(input_data: Any) -> Dict[str, Any]:
    """Alternative function-based entry point.
    
    This demonstrates how you can use a function instead of a class method.
    """
    agent = ExampleAgent()
    return agent.process_input(input_data)


# Example of a callable class that can be used directly
class CallableAgent:
    """Example of a callable agent class."""
    
    def __init__(self):
        self.processed_count = 0
    
    def __call__(self, input_data: Any) -> Dict[str, Any]:
        """Make the class callable."""
        self.processed_count += 1
        return {
            'status': 'success',
            'result': f"Processed {self.processed_count} items",
            'input': str(input_data)
        } 