"""
Configuration module for Kaizen Agent.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Any
from dotenv import load_dotenv
import time

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
        print(f"Debug: Starting environment variable loading...")
        print(f"Debug: Looking for env file: {self.env_file}")
        
        # Clear any existing environment variables
        if 'GOOGLE_API_KEY' in os.environ:
            del os.environ['GOOGLE_API_KEY']
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        # First try to load from the explicitly set env file path
        if self.env_file and os.path.exists(self.env_file):
            print(f"Debug: Loading from explicit path: {self.env_file}")
            print(f"Debug: File last modified: {time.ctime(os.path.getmtime(self.env_file))}")
            load_dotenv(self.env_file, override=True)
            return

        # Try to find .env file in current directory and parent directories
        current_dir = Path.cwd()
        env_path = None
        
        # Look for .env file in current directory and parent directories
        while current_dir != current_dir.parent:
            potential_path = current_dir / self.env_file
            print(f"Debug: Checking path: {potential_path}")
            if potential_path.exists():
                env_path = potential_path
                print(f"Debug: Found env file at: {env_path}")
                print(f"Debug: File last modified: {time.ctime(env_path.stat().st_mtime)}")
                break
            current_dir = current_dir.parent
        
        if env_path:
            print(f"Debug: Loading from found path: {env_path}")
            load_dotenv(env_path, override=True)
        else:
            # If no .env file found, try to load from current directory
            print("Debug: No env file found in directories, trying current directory")
            load_dotenv(override=True)
            
            # If still no environment variables loaded, try to load from user's home directory
            home_env = Path.home() / '.kaizen' / '.env'
            print(f"Debug: Checking home directory: {home_env}")
            if home_env.exists():
                print(f"Debug: Loading from home directory: {home_env}")
                print(f"Debug: File last modified: {time.ctime(home_env.stat().st_mtime)}")
                load_dotenv(home_env, override=True)
        
        # Debug: Check if GOOGLE_API_KEY is loaded
        google_key = os.getenv('GOOGLE_API_KEY')
        if google_key:
            print(f"Debug: GOOGLE_API_KEY is loaded (length: {len(google_key)})")
        else:
            print("Debug: GOOGLE_API_KEY is NOT loaded")
    
    def set_env_file(self, env_file: str) -> None:
        """
        Set the environment file path and reload environment variables.
        
        Args:
            env_file: Path to the .env file
        """
        self.env_file = env_file
        self._load_env()
    
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
            "anthropic": self.get_api_key("anthropic"),
            "google": self.get_api_key("google")
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