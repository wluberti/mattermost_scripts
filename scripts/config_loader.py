import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv

# Load .env file from the root of the repo (assuming script is run from scripts/)
# Adjust path to find .env one level up
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config if config else {}
    except FileNotFoundError:
        # Fallback to looking in the same directory as the script if not found via relative path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.join(script_dir, config_path)
        try:
             with open(abs_path, "r") as f:
                config = yaml.safe_load(f)
             return config if config else {}
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing configuration file: {e}")

def get_env_var(name: str, default: str = None, required: bool = False) -> str:
    """Retrieves an environment variable."""
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value
