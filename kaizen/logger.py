"""
Logging utility for Kaizen Agent.
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.logging import RichHandler

console = Console()

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: The name of the logger
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(f"kaizen.{name}")
    logger.setLevel(logging.DEBUG)
    
    # Add rich handler for console output if no handlers exist
    if not logger.handlers:
        console_handler = RichHandler(console=console)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
        # Add file handler for detailed logs
        output_dir = Path("logs")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = output_dir / f"{name}_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    
    return logger

class TestLogger:
    def __init__(self, test_name: str, output_dir: str = "test-results"):
        self.test_name = test_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Set up logging
        self.logger = get_logger(test_name)
        
        # Initialize test results
        self.results = {
            "test_name": test_name,
            "start_time": datetime.now().isoformat(),
            "steps": []
        }
    
    def log_step_start(self, step_index: int, input_data: Dict[str, Any]):
        """Log the start of a test step."""
        self.logger.info(f"Starting step {step_index}")
        self.logger.debug(f"Step {step_index} input: {json.dumps(input_data, indent=2)}")
        
        self.results["steps"].append({
            "step_index": step_index,
            "start_time": datetime.now().isoformat(),
            "input": input_data,
            "status": "running"
        })
    
    def log_step_result(self, step_index: int, output: Any, passed: bool, error: Optional[str] = None):
        """Log the result of a test step."""
        status = "passed" if passed else "failed"
        self.logger.info(f"Step {step_index} {status}")
        self.logger.debug(f"Step {step_index} output: {json.dumps(output, indent=2)}")
        
        if error:
            self.logger.error(f"Step {step_index} error: {error}")
        
        # Update the step result
        for step in self.results["steps"]:
            if step["step_index"] == step_index:
                step.update({
                    "end_time": datetime.now().isoformat(),
                    "output": output,
                    "status": status,
                    "error": error
                })
                break
    
    def get_last_step_details(self) -> Optional[str]:
        """Get the details of the last executed step.
        
        Returns:
            Optional[str]: The error message if the last step failed, None otherwise
        """
        if not self.results["steps"]:
            return None
            
        last_step = self.results["steps"][-1]
        if last_step["status"] == "failed":
            return last_step.get("error", "Test failed")
        return None
    
    def save_results(self):
        """Save test results to a JSON file."""
        self.results["end_time"] = datetime.now().isoformat()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.output_dir / f"{self.test_name}_{timestamp}_results.json"
        
        with open(result_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        self.logger.info(f"Test results saved to {result_file}")
        return result_file 