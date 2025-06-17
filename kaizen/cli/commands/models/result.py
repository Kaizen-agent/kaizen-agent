"""Test result model."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .configuration import TestConfiguration

@dataclass(frozen=True)
class TestResult:
    """Test execution result.
    
    Attributes:
        name: Test name
        file_path: Test file location
        config_path: Config file location
        start_time: Test start time
        end_time: Test end time
        status: Overall test status
        results: Detailed test results
        error: Error message if failed
        steps: Test step results
    """
    # Required fields
    name: str
    file_path: Path
    config_path: Path
    start_time: datetime
    end_time: datetime
    status: str
    results: Dict[str, any]
    
    # Optional fields
    error: Optional[str] = None
    steps: List[Dict[str, any]] = field(default_factory=list)
    
    @classmethod
    def from_config(cls, config: TestConfiguration) -> 'TestResult':
        """Create a test result from configuration.
        
        Args:
            config: Test configuration
            
        Returns:
            New test result instance
        """
        now = datetime.now()
        return cls(
            name=config.name,
            file_path=config.file_path,
            config_path=config.config_path,
            start_time=now,
            end_time=now,
            status='pending',
            results={}
        ) 