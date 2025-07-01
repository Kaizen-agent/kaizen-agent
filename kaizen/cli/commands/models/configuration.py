"""Test configuration model."""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional, List, Dict, Any

from kaizen.cli.commands.errors import ConfigurationError
from ..types import PRStrategy, DEFAULT_MAX_RETRIES, Language, DEFAULT_LANGUAGE

from .metadata import TestMetadata
from .evaluation import TestEvaluation
from .settings import TestSettings
from .step import TestStep

@dataclass
class AgentEntryPoint:
    """Configuration for agent entry point without markers.
    
    Attributes:
        module: Module path (e.g., 'path.to.module')
        class_name: Class name to instantiate (optional)
        method: Method name to call (optional)
        fallback_to_function: Whether to fallback to function if class/method not found
    """
    module: str
    class_name: Optional[str] = None
    method: Optional[str] = None
    fallback_to_function: bool = True

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
        regions: List of regions to test (legacy marker-based)
        agent: Agent entry point configuration (new marker-free approach)
        steps: List of test steps
        settings: Test settings
        auto_fix: Enable auto-fix
        create_pr: Enable PR creation
        max_retries: Retry limit
        base_branch: PR base branch
        pr_strategy: PR creation strategy
        dependencies: List of required dependencies
        referenced_files: List of referenced files to import
        files_to_fix: List of files that should be fixed
        language: Test language
    """
    # Required fields
    name: str
    file_path: Path
    config_path: Path
    
    # Optional fields
    agent_type: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[TestMetadata] = None
    evaluation: Optional[TestEvaluation] = None
    regions: List[str] = field(default_factory=list)
    agent: Optional[AgentEntryPoint] = None
    steps: List[TestStep] = field(default_factory=list)
    settings: Optional[TestSettings] = None
    auto_fix: bool = False
    create_pr: bool = False
    max_retries: int = DEFAULT_MAX_RETRIES
    base_branch: str = "main"
    pr_strategy: PRStrategy = PRStrategy.ALL_PASSING
    dependencies: List[str] = field(default_factory=list)
    referenced_files: List[str] = field(default_factory=list)
    files_to_fix: List[str] = field(default_factory=list)
    language: Language = DEFAULT_LANGUAGE

    def with_cli_overrides(
        self,
        auto_fix: bool = False,
        create_pr: bool = False,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_branch: str = 'main',
        pr_strategy: str = 'ALL_PASSING',
        language: Optional[str] = None
    ) -> 'TestConfiguration':
        """Create a new configuration with CLI overrides applied.
        
        This method efficiently creates a new configuration instance with
        CLI-specific settings overridden, avoiding the need to manually
        copy all fields.
        
        Args:
            auto_fix: Whether to enable auto-fix
            create_pr: Whether to create pull requests
            max_retries: Maximum number of retry attempts
            base_branch: Base branch for pull requests
            pr_strategy: Strategy for when to create PRs
            language: Language override (if provided)
            
        Returns:
            New TestConfiguration instance with overrides applied
        """
        # Prepare override values
        overrides = {
            'auto_fix': auto_fix,
            'create_pr': create_pr,
            'max_retries': max_retries,
            'base_branch': base_branch,
            'pr_strategy': PRStrategy.from_str(pr_strategy)
        }
        
        # Handle language override if provided
        if language is not None and str(language).strip() != '':
            overrides['language'] = Language.from_str(language)
        
        # Use dataclass replace for efficient field updates
        return replace(self, **overrides)

    @classmethod
    def from_dict(
        cls, 
        data: Dict[str, Any], 
        config_path: Path,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> 'TestConfiguration':
        """Create a TestConfiguration instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration data
            config_path: Path to the configuration file
            cli_overrides: Optional CLI parameter overrides
            
        Returns:
            TestConfiguration instance
            
        Raises:
            ConfigurationError: If configuration is invalid
            FileNotFoundError: If test file does not exist
        """
        # Apply CLI overrides to data if provided
        if cli_overrides:
            data = {**data, **cli_overrides}
        
        # Parse PR strategy
        pr_strategy = data.get('pr_strategy', 'ALL_PASSING')
        if isinstance(pr_strategy, str):
            try:
                pr_strategy = PRStrategy.from_str(pr_strategy)
            except ValueError as e:
                raise ConfigurationError(str(e))
        
        # Parse language
        language = DEFAULT_LANGUAGE
        if 'language' in data:
            lang_val = data['language']
            print(f"DEBUG: Processing language value: {lang_val} (type: {type(lang_val)})")
            if isinstance(lang_val, Language):
                language = lang_val
                print(f"DEBUG: Using Language enum directly: {language}")
            elif isinstance(lang_val, str):
                try:
                    language = Language.from_str(lang_val)
                    print(f"DEBUG: Converted string to Language: {language}")
                except ValueError as e:
                    raise ConfigurationError(str(e))
            else:
                raise ConfigurationError(f"Invalid type for language: {type(lang_val)}")
        else:
            print(f"DEBUG: No language in data, using default: {language}")
        
        # Parse agent entry point if present
        agent_entry_point = None
        if 'agent' in data:
            agent_data = data['agent']
            if isinstance(agent_data, dict):
                agent_entry_point = AgentEntryPoint(
                    module=agent_data['module'],
                    class_name=agent_data.get('class'),
                    method=agent_data.get('method'),
                    fallback_to_function=agent_data.get('fallback_to_function', True)
                )
        
        return cls(
            name=data['name'],
            file_path=Path(data['file_path']),
            config_path=config_path,
            agent_type=data.get('agent_type'),
            description=data.get('description'),
            metadata=TestMetadata.from_dict(data.get('metadata', {})) if 'metadata' in data else None,
            evaluation=TestEvaluation.from_dict(data.get('evaluation', {})) if 'evaluation' in data else None,
            regions=data.get('regions', []),
            agent=agent_entry_point,
            steps=[TestStep.from_dict(step) for step in data.get('steps', [])],
            settings=TestSettings.from_dict(data.get('settings', {})) if 'settings' in data else None,
            auto_fix=data.get('auto_fix', False),
            create_pr=data.get('create_pr', False),
            max_retries=data.get('max_retries', DEFAULT_MAX_RETRIES),
            base_branch=data.get('base_branch', 'main'),
            pr_strategy=pr_strategy,
            dependencies=data.get('dependencies', []),
            referenced_files=data.get('referenced_files', []),
            files_to_fix=data.get('files_to_fix', []),
            language=language
        ) 