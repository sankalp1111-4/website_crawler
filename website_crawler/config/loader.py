"""
Configuration loader for the website crawler.

Loads and validates configuration from JSON files.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

from dotenv import load_dotenv

from .schema import MainConfig

# Load environment variables from .env file if it exists
load_dotenv()

# Default configuration path
DEFAULT_CONFIG_PATH = Path(__file__).parent / "defaults.json"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.
    
    Args:
        base: Base dictionary
        override: Override dictionary
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def _load_env_overrides() -> Dict[str, Any]:
    """
    Load configuration overrides from environment variables.
    
    Environment variables should follow the pattern:
    - CRAWLER_MAX_DEPTH -> crawler.max_depth
    - ENGINE_HEADLESS -> engine.headless
    - STORAGE_CONNECTION_STRING -> storage.connection_string
    etc.
    
    Returns:
        Dictionary with nested structure matching config schema
    """
    overrides: Dict[str, Any] = {}
    
    # Mapping of environment variable prefixes to config sections
    env_mappings = {
        "CRAWLER_": "crawler",
        "ENGINE_": "engine",
        "STORAGE_": "storage",
        "EXTRACTION_": "extraction",
        "STRATEGY_": "strategy",
        "AUTH_": "auth",
        "LOGGING_": "logging",
    }
    
    # Direct mappings for common variables
    direct_mappings = {
        "CLIENT_ID": "client_id",
        "MONGO_URI": "storage.connection_string",
        "MONGO_DATABASE": "storage.database",
        "LOG_LEVEL": "logging.level",
        "HEADLESS": "engine.headless",
        "BROWSER_TYPE": "engine.browser_type",
        "CRAWL_TIMEOUT": "crawler.timeout",
    }
    
    # Process direct mappings
    for env_key, config_path in direct_mappings.items():
        env_value = os.getenv(env_key)
        if env_value is not None:
            keys = config_path.split(".")
            current = overrides
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Convert value to appropriate type
            final_key = keys[-1]
            converted_value = _convert_env_value(env_value)
            current[final_key] = converted_value
    
    # Process prefixed environment variables
    for env_key, env_value in os.environ.items():
        if not env_key.startswith("CRAWLER_") and not any(
            env_key.startswith(prefix) for prefix in env_mappings.keys()
        ):
            continue
        
        # Find matching prefix
        matched_prefix = None
        for prefix, section in env_mappings.items():
            if env_key.startswith(prefix):
                matched_prefix = prefix
                section_name = section
                break
        
        if matched_prefix:
            # Extract the config key (convert SNAKE_CASE to snake_case)
            config_key = env_key[len(matched_prefix):].lower()
            
            # Handle nested keys (e.g., STORAGE_CONNECTION_STRING -> connection_string)
            if section_name not in overrides:
                overrides[section_name] = {}
            
            # Convert value to appropriate type
            converted_value = _convert_env_value(env_value)
            overrides[section_name][config_key] = converted_value
    
    return overrides


def _convert_env_value(value: str) -> Any:
    """
    Convert environment variable string to appropriate Python type.
    
    Args:
        value: Environment variable value as string
        
    Returns:
        Converted value (bool, int, float, str, or None)
    """
    # Handle boolean values
    if value.lower() in ("true", "1", "yes", "on"):
        return True
    if value.lower() in ("false", "0", "no", "off", ""):
        return False
    
    # Handle null/None
    if value.lower() in ("null", "none"):
        return None
    
    # Try to convert to int
    try:
        if "." not in value:
            return int(value)
    except ValueError:
        pass
    
    # Try to convert to float
    try:
        return float(value)
    except ValueError:
        pass
    
    # Return as string
    return value


def load_config(
    config_path: Optional[str] = None,
    client_id: Optional[str] = None,
    use_cache: bool = True
) -> MainConfig:
    """
    Load configuration from JSON file with environment variable overrides.
    
    Args:
        config_path: Path to configuration JSON file. If None, uses defaults.json
        client_id: Optional client identifier for per-client configuration
        use_cache: Whether to use cached configuration (default: True)
        
    Returns:
        Validated MainConfig instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist and is explicitly provided
        ValueError: If configuration validation fails
    """
    # Use cache if enabled
    if use_cache:
        return _load_config_cached(config_path, client_id)
    
    return _load_config_impl(config_path, client_id)


@lru_cache(maxsize=10)
def _load_config_cached(
    config_path: Optional[str],
    client_id: Optional[str]
) -> MainConfig:
    """Cached version of load_config."""
    return _load_config_impl(config_path, client_id)


def _load_config_impl(
    config_path: Optional[str],
    client_id: Optional[str]
) -> MainConfig:
    """Internal implementation of load_config."""
    # Determine config file path
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", str(DEFAULT_CONFIG_PATH))
    
    config_file = Path(config_path)
    
    # Load defaults first
    defaults_file = Path(__file__).parent / "defaults.json"
    if not defaults_file.exists():
        raise FileNotFoundError(f"Default configuration file not found: {defaults_file}")
    
    with open(defaults_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    # Load user config if provided and exists
    if config_file.exists() and config_file != defaults_file:
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # Merge user config over defaults
                config_data = _deep_merge(config_data, user_config)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file {config_file}: {e}")
    elif config_path and not config_file.exists():
        # Only raise error if config_path was explicitly provided
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    # Load per-client configuration if client_id is provided
    if client_id:
        client_config_path = Path(__file__).parent.parent / "config" / "clients" / f"{client_id}.json"
        if client_config_path.exists():
            try:
                with open(client_config_path, "r", encoding="utf-8") as f:
                    client_config = json.load(f)
                    # Merge client config over user config
                    config_data = _deep_merge(config_data, client_config)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in client configuration file {client_config_path}: {e}")
    
    # Override with environment variables
    env_overrides = _load_env_overrides()
    if env_overrides:
        config_data = _deep_merge(config_data, env_overrides)
    
    # Override client_id if provided
    if client_id:
        config_data["client_id"] = client_id
    elif os.getenv("CLIENT_ID"):
        config_data["client_id"] = os.getenv("CLIENT_ID")
    
    # Validate and create MainConfig instance
    try:
        return MainConfig(**config_data)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}") from e


def get_config(
    config_path: Optional[str] = None,
    client_id: Optional[str] = None
) -> MainConfig:
    """
    Get configuration instance (convenience function).
    
    Args:
        config_path: Path to configuration JSON file
        client_id: Optional client identifier
        
    Returns:
        MainConfig instance
    """
    return load_config(config_path=config_path, client_id=client_id, use_cache=True)
