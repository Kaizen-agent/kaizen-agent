"""
Model configuration module for Kaizen Agent.
This module handles configuration for different LLM models and their API keys.
"""
from typing import Dict, Optional, Literal, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import os
from .config import get_config

# Common provider types, but allowing for future additions
ProviderType = Literal["google", "kaizen"]

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    model_type: str  # Allow any model name
    api_key: str
    provider: ProviderType

    def is_valid(self) -> Tuple[bool, str]:
        """Check if the configuration is valid."""
        if not self.api_key:
            return False, "API key is required"
        if not self.model_type:
            return False, "Model type is required"
        if not self.provider:
            return False, "Provider is required"
        return True, ""

class ModelConfigurationManager:
    """Manages model configurations for different components."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(os.path.expanduser("~"), ".kaizen", "model_config.json")
        self._config: Dict[str, ModelConfig] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    for component, data in config_data.items():
                        self._config[component] = ModelConfig(
                            model_type=data["model_type"],
                            api_key=data["api_key"],
                            provider=data["provider"]
                        )
            except Exception as e:
                print(f"Error loading model configuration: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
        
        # Override CLI settings with environment variables if they exist
        self._override_cli_settings()
    
    def _override_cli_settings(self) -> None:
        """Override CLI settings with environment variables if they exist."""
        cli_model = os.getenv("KAIZEN_CLI_MODEL")
        cli_api_key = os.getenv("KAIZEN_CLI_API_KEY")
        cli_provider = os.getenv("KAIZEN_CLI_PROVIDER")
        
        # Get current CLI config or create default
        current_cli_config = self._config.get("cli", ModelConfig(
            model_type="gemini-2.5-flash-preview-05-20",  # Default to Gemini 2.5 Flash Preview
            api_key="",
            provider="google"  # Default to Google provider
        ))
        
        # Only update if at least one environment variable is set
        if any([cli_model, cli_api_key, cli_provider]):
            # Validate provider if set
            if cli_provider and cli_provider not in ["google", "kaizen"]:
                print(f"Warning: Invalid provider '{cli_provider}'. Using default provider.")
                cli_provider = current_cli_config.provider
            
            # Create new config with environment variables or fallback to current values
            new_config = ModelConfig(
                model_type=cli_model or current_cli_config.model_type,
                api_key=cli_api_key or current_cli_config.api_key,
                provider=cli_provider or current_cli_config.provider
            )
            
            # Validate the new configuration
            is_valid, message = new_config.is_valid()
            if is_valid:
                self._config["cli"] = new_config
            else:
                print(f"Warning: Invalid CLI configuration: {message}. Using default configuration.")
    
    def _create_default_config(self) -> None:
        """Create default configuration."""
        self._config = {
            "test_agent": ModelConfig(
                model_type="gemini-2.5-flash-preview-05-20",  # Default to Gemini 2.5 Flash Preview
                api_key="",
                provider="google"  # Default to Google provider
            ),
            "kaizen_llm": ModelConfig(
                model_type="kaizen-llm",
                api_key="",
                provider="kaizen"
            ),
            "cli": ModelConfig(
                model_type="gemini-2.5-flash-preview-05-20",  # Default to Gemini 2.5 Flash Preview
                api_key="",
                provider="google"  # Default to Google provider
            )
        }
        self.save_config()
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        config_data = {
            component: {
                "model_type": config.model_type,
                "api_key": config.api_key,
                "provider": config.provider
            }
            for component, config in self._config.items()
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def get_model_config(self, component: str) -> Optional[ModelConfig]:
        """Get model configuration for a specific component."""
        config = self._config.get(component)
        if config:
            is_valid, message = config.is_valid()
            if not is_valid:
                print(f"Warning: Invalid configuration for {component}: {message}")
        return config
    
    def set_model_config(self, component: str, model_type: str, api_key: str, provider: ProviderType) -> None:
        """Set model configuration for a specific component."""
        new_config = ModelConfig(
            model_type=model_type,
            api_key=api_key,
            provider=provider
        )
        
        is_valid, message = new_config.is_valid()
        if is_valid:
            self._config[component] = new_config
            self.save_config()
        else:
            raise ValueError(f"Invalid configuration: {message}")
    
    def get_all_configs(self) -> Dict[str, ModelConfig]:
        """Get all model configurations."""
        return self._config.copy()

# Global instance
model_config_manager = ModelConfigurationManager()

def get_model_config(component: str) -> Optional[ModelConfig]:
    """Get model configuration for a specific component."""
    return model_config_manager.get_model_config(component)

def set_model_config(component: str, model_type: str, api_key: str, provider: ProviderType) -> None:
    """Set model configuration for a specific component."""
    model_config_manager.set_model_config(component, model_type, api_key, provider)

def get_all_model_configs() -> Dict[str, ModelConfig]:
    """Get all model configurations."""
    return model_config_manager.get_all_configs() 