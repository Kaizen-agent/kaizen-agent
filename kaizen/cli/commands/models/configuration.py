"""Test configuration model."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

from .metadata import TestMetadata
from .evaluation import TestEvaluation
from .step import TestStep
from ..types import PRStrategy

@dataclass(frozen=True)
class TestConfiguration:
    """Test configuration with all required and optional settings.
    
    Attributes:
        name: Test identifier
        file_path: Test file location
        config_path: Config file location
        auto_fix: Enable auto-fix
        create_pr: Enable PR creation
        max_retries: Retry limit
        base_branch: PR base branch
        pr_strategy: PR creation strategy
        description: Test description
        agent_type: Agent type
        regions: Test regions
        steps: Test steps
        metadata: Test metadata
        evaluation: Test evaluation
    """
    # Required fields
    name: str
    file_path: Path
    config_path: Path
    auto_fix: bool
    create_pr: bool
    max_retries: int
    base_branch: str
    pr_strategy: PRStrategy
    
    # Optional fields
    description: Optional[str] = None
    agent_type: Optional[str] = None
    regions: List[str] = field(default_factory=list)
    steps: List[TestStep] = field(default_factory=list)
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[TestEvaluation] = None 