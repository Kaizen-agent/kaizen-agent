from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Base class for all test agents."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the agent with configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        
    @abstractmethod
    def run_test(self, code: str, region: str) -> Dict[str, Any]:
        """
        Run tests for the specified code region.
        
        Args:
            code (str): The code to test
            region (str): The region name to test
            
        Returns:
            Dict[str, Any]: Test results
        """
        pass 