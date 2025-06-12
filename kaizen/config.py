"""
Configuration module for Kaizen Agent.
"""
import os
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

class Config:
    """Configuration manager for Kaizen Agent."""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file or '.env'
        self._load_env()
    
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