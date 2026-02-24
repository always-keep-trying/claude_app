"""
config_manager.py
Manages local configuration for the Claude Chat App.

Non-sensitive settings are stored in ~/.claude_chat_app/config.json
The API key is stored in the OS keychain via the `keyring` library,
keeping it out of plain-text files on disk.

Falls back to JSON storage if keyring is unavailable (e.g. headless Linux).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False
    logging.warning("keyring not available — API key will be stored in config.json")

_KEYRING_SERVICE  = "claude_chat_app"
_KEYRING_USERNAME = "anthropic_api_key"

# Available models with their API identifiers
AVAILABLE_MODELS = [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
]

# api_key is intentionally excluded — stored in OS keychain, not JSON
DEFAULT_CONFIG: Dict[str, Any] = {
    "model":         "claude-sonnet-4-6",
    "max_tokens":    8096,
    "temperature":   1.0,
    "system_prompt": "",
}


class ConfigManager:
    """
    Manages persistent app configuration.

    Non-sensitive values are persisted as JSON.
    The API key is stored in the OS keychain when keyring is available,
    falling back to JSON if not.
    """

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
                # Migrate legacy plaintext api_key to keychain on first run
                if "api_key" in data and _KEYRING_AVAILABLE:
                    legacy_key = data.pop("api_key", "")
                    if legacy_key:
                        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, legacy_key)
                        self._save_data(data)
                return data
            except (json.JSONDecodeError, OSError):
                pass
        return DEFAULT_CONFIG.copy()

    def _save_data(self, data: Dict[str, Any]):
        """Persist a dict to JSON, always excluding api_key."""
        safe = {k: v for k, v in data.items() if k != "api_key"}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(safe, f, indent=2)

    def _save(self):
        self._save_data(self.config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        if key == "api_key":
            if _KEYRING_AVAILABLE:
                try:
                    return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME) or default
                except Exception:
                    pass
            # Fallback: read from in-memory config (legacy / no keyring)
            return self.config.get("api_key", default)
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        if key == "api_key":
            if _KEYRING_AVAILABLE:
                try:
                    keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, value)
                    return
                except Exception:
                    pass
            self.config["api_key"] = value
        else:
            self.config[key] = value
        self._save()

    def update(self, data: Dict[str, Any]):
        """Update multiple keys. API key is routed to keychain if available."""
        if "api_key" in data:
            self.set("api_key", data["api_key"])
        non_key = {k: v for k, v in data.items() if k != "api_key"}
        if non_key:
            self.config.update(non_key)
            self._save()

    def all(self) -> Dict[str, Any]:
        """Return a copy of all config including the api_key."""
        result = dict(self.config)
        result["api_key"] = self.get("api_key", "")
        return result
