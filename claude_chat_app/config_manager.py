"""
config_manager.py
Manages local configuration for the Claude Chat App.
Config is stored in ~/.claude_chat_app/config.json
"""

import json
from pathlib import Path
from typing import Any, Dict

# Available models with their API identifiers
AVAILABLE_MODELS = [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "model": "claude-sonnet-4-6",
    "max_tokens": 8096,
    "temperature": 1.0,
    "system_prompt": "",
}


class ConfigManager:
    """Manages persistent app configuration stored as a local JSON file."""

    def __init__(self, app_dir: Path):
        self.config_path = app_dir / "config.json"
        self.config = self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        """Load config from disk, merging any missing keys with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Forward-fill any new default keys
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
            except (json.JSONDecodeError, OSError):
                pass
        return DEFAULT_CONFIG.copy()

    def _save(self):
        """Persist current config to disk."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self._save()

    def update(self, data: Dict[str, Any]):
        self.config.update(data)
        self._save()

    def all(self) -> Dict[str, Any]:
        return dict(self.config)
