"""Example test file that demonstrates dependency management."""

import requests
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def test_function(input_data: str) -> Dict[str, Any]:
    """Test function that uses dependencies.
    
    Args:
        input_data: Input data for testing
        
    Returns:
        Dictionary containing test results
    """
    try:
        # Use pandas for data processing
        df = pd.DataFrame({'data': [input_data]})
        
        # Use numpy for calculations
        result = np.mean([1, 2, 3, 4, 5])
        
        # Use requests for API call (simulated)
        response = {"status": "success", "data": input_data}
        
        return {
            "status": "success",
            "result": result,
            "data": df.to_dict(),
            "response": response
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

def test_error_handling(invalid_input: str) -> Dict[str, Any]:
    """Test function that demonstrates error handling.
    
    Args:
        invalid_input: Invalid input to trigger errors
        
    Returns:
        Dictionary containing error information
    """
    try:
        # This will raise a ValueError for invalid input
        if not invalid_input or invalid_input == "invalid":
            raise ValueError("Invalid input provided")
        
        return {"status": "success", "result": "valid input"}
        
    except ValueError as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": "ValueError"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

class TestClass:
    """Test class that demonstrates class-based testing."""
    
    def __init__(self, name: str):
        """Initialize the test class.
        
        Args:
            name: Name for the test instance
        """
        self.name = name
        self.data = []
    
    def add_data(self, item: Any) -> None:
        """Add data to the test instance.
        
        Args:
            item: Item to add to the data list
        """
        self.data.append(item)
    
    def get_data(self) -> list:
        """Get all data from the test instance.
        
        Returns:
            List of all data items
        """
        return self.data
    
    def process_data(self) -> Dict[str, Any]:
        """Process the data using dependencies.
        
        Returns:
            Dictionary containing processed data
        """
        try:
            if not self.data:
                return {"status": "error", "error": "No data to process"}
            
            # Use pandas to process data
            df = pd.DataFrame(self.data, columns=['value'])
            summary = df.describe()
            
            # Use numpy for calculations
            mean_value = np.mean(self.data)
            std_value = np.std(self.data)
            
            return {
                "status": "success",
                "name": self.name,
                "data_count": len(self.data),
                "mean": mean_value,
                "std": std_value,
                "summary": summary.to_dict()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }

# Example usage
if __name__ == "__main__":
    # Test the functions
    print("Testing test_function:")
    result1 = test_function("test data")
    print(result1)
    
    print("\nTesting error handling:")
    result2 = test_error_handling("invalid")
    print(result2)
    
    print("\nTesting TestClass:")
    test_instance = TestClass("test_instance")
    test_instance.add_data(1)
    test_instance.add_data(2)
    test_instance.add_data(3)
    result3 = test_instance.process_data()
    print(result3) 