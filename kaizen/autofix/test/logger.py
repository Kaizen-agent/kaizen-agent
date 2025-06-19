import logging
from typing import Dict, Any

class TestLogger:
    """A logger class for test execution that wraps Python's built-in logging."""
    
    def __init__(self, test_name: str):
        """
        Initialize the test logger.
        
        Args:
            test_name: Name of the test being executed
        """
        self.logger = logging.getLogger(f"kaizen.test.{test_name}")
        self.test_name = test_name
        
        # Configure logging if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def info(self, message: str, extra: Dict[str, Any] = None) -> None:
        """Log an info message."""
        self.logger.info(message, extra=extra)
    
    def error(self, message: str, extra: Dict[str, Any] = None) -> None:
        """Log an error message."""
        self.logger.error(message, extra=extra)
    
    def warning(self, message: str, extra: Dict[str, Any] = None) -> None:
        """Log a warning message."""
        self.logger.warning(message, extra=extra)
    
    def debug(self, message: str, extra: Dict[str, Any] = None) -> None:
        """Log a debug message."""
        self.logger.debug(message, extra=extra) 