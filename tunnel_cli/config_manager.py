"""
Configuration manager for storing credentials and settings
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".tunnel-cli"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._config = self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save(self):
        """Save configuration to file"""
        with open(self.config_file, "w") as f:
            json.dump(self._config, f, indent=2)
        # Set restrictive permissions
        os.chmod(self.config_file, 0o600)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value
        self.save()
    
    def delete(self, key: str):
        """Delete configuration value"""
        if key in self._config:
            del self._config[key]
            self.save()
    
    def clear(self):
        """Clear all configuration"""
        self._config = {}
        if self.config_file.exists():
            os.remove(self.config_file)
    
    @property
    def api_key(self) -> Optional[str]:
        return self.get("api_key")
    
    @api_key.setter
    def api_key(self, value: str):
        self.set("api_key", value)
    
    @property
    def api_url(self) -> str:
        return self.get("api_url", "https://tunnel.ovream.com/api/v1")
    
    @api_url.setter
    def api_url(self, value: str):
        self.set("api_url", value)
    
    @property
    def username(self) -> Optional[str]:
        return self.get("username")
    
    @username.setter
    def username(self, value: str):
        self.set("username", value)