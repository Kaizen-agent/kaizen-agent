"""Test configuration model."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

from .metadata import TestMetadata
from .evaluation import TestEvaluation
from .settings import TestSettings
from .step import TestStep
from ..types import PRStrategy

@dataclass(frozen=True)
class TestConfiguration:
    """Test configuration with all required and optional settings.
    
    Attributes:
        name: Test identifier
        file_path: Test file location
        config_path: Config file location
        agent_type: Type of agent to use
        description: Test description
        metadata: Test metadata
        evaluation: Test evaluation criteria
        regions: List of regions to test
        steps: List of test steps
        settings: Test settings
        auto_fix: Enable auto-fix
        create_pr: Enable PR creation
        max_retries: Retry limit
        base_branch: PR base branch
        pr_strategy: PR creation strategy
    """
    # Required fields
    name: str
    file_path: Path
    config_path: Path
    agent_type: str
    
    # Optional fields
    description: Optional[str] = None
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[TestEvaluation] = None
    regions: List[str] = field(default_factory=list)
    steps: List[TestStep] = field(default_factory=list)
    settings: Optional[TestSettings] = None
    auto_fix: bool = False
    create_pr: bool = False
    max_retries: int = 3
    base_branch: str = "main"
    pr_strategy: PRStrategy = PRStrategy.CREATE_NEW

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: Path) -> 'TestConfiguration':
        """Create a TestConfiguration instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration data
            config_path: Path to the configuration file
            
        Returns:
            TestConfiguration instance
        """
        return cls(
            name=data['name'],
            file_path=Path(data['file_path']),
            config_path=config_path,
            agent_type=data.get('agent_type', 'default'),
            description=data.get('description'),
            metadata=TestMetadata.from_dict(data.get('metadata', {})) if 'metadata' in data else None,
            evaluation=TestEvaluation.from_dict(data.get('evaluation', {})) if 'evaluation' in data else None,
            regions=data.get('regions', []),
            steps=[TestStep.from_dict(step) for step in data.get('steps', [])],
            settings=TestSettings.from_dict(data.get('settings', {})) if 'settings' in data else None,
            auto_fix=data.get('auto_fix', False),
            create_pr=data.get('create_pr', False),
            max_retries=data.get('max_retries', 3),
            base_branch=data.get('base_branch', 'main'),
            pr_strategy=PRStrategy.from_str(data.get('pr_strategy', 'CREATE_NEW'))
        ) 