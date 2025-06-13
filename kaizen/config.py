"""
Configuration module for Kaizen Agent.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Any
from dotenv import load_dotenv

class Config:
    """Configuration manager for Kaizen Agent."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, env_file: Optional[str] = None):
        if not hasattr(self, 'initialized'):
            self.env_file = env_file or '.env'
            self._config = {}
            self._load_env()
            self.initialized = True
    
    def _load_env(self):
        """Load environment variables from .env file."""
        # Try to find .env file in current directory and parent directories
        current_dir = Path.cwd()
        env_path = None
        
        # Look for .env file in current directory and parent directories
        while current_dir != current_dir.parent:
            potential_path = current_dir / self.env_file
            if potential_path.exists():
                env_path = potential_path
                break
            current_dir = current_dir.parent
        
        if env_path:
            load_dotenv(env_path)
        else:
            # If no .env file found, try to load from current directory
            load_dotenv()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key to get
            default: Default value if key is not found
            
        Returns:
            The configuration value or default
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key to set
            value: The value to set
        """
        self._config[key] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration with a dictionary of values.
        
        Args:
            config_dict: Dictionary of configuration values
        """
        self._config.update(config_dict)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for the specified provider."""
        env_var = f"{provider.upper()}_API_KEY"
        return os.getenv(env_var)
    
    def get_all_api_keys(self) -> Dict[str, str]:
        """Get all configured API keys."""
        return {
            "openai": self.get_api_key("openai"),
            "anthropic": self.get_api_key("anthropic")
        }
    
    def validate_api_keys(self, required_providers: list[str]) -> Dict[str, bool]:
        """Validate that required API keys are present."""
        validation = {}
        for provider in required_providers:
            key = self.get_api_key(provider)
            validation[provider] = key is not None
        return validation

def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get the singleton Config instance.
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Config: The singleton configuration instance
    """
    return Config(env_file) 