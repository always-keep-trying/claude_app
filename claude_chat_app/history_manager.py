"""
history_manager.py
Manages chat history (per-session JSON files) and persistent token/cost usage tracking.
History lives in ~/.claude_chat_app/history/
Usage data lives in ~/.claude_chat_app/usage.json
"""

import copy
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Pricing per 1 million tokens (USD) — update as Anthropic changes pricing
# Source: Anthropic official pricing, February 2026
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-6":           {"input":  5.00, "output": 25.00},
    "claude-sonnet-4-6":         {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input":  1.00, "output":  5.00},
}

_FALLBACK_PRICING = {"input": 3.00, "output": 15.00}


class HistoryManager:
    """Manages chat sessions on disk and tracks cumulative API usage."""

    def __init__(self, app_dir: Path):
        self.history_dir = app_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.usage_path = app_dir / "usage.json"
        self.usage = self._load_usage()

        # State for the currently active chat
        self.current_chat_id: Optional[str] = None
        self.current_messages: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------

    def _load_usage(self) -> Dict:
        if self.usage_path.exists():
            try:
                with open(self.usage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0.0,
            "by_model": {},
        }

    def _save_usage(self):
        with open(self.usage_path, "w", encoding="utf-8") as f:
            json.dump(self.usage, f, indent=2)

    def record_usage(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Add token counts to the running totals and return the cost for this call."""
        pricing = MODEL_PRICING.get(model, _FALLBACK_PRICING)
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        self.usage["input_tokens"]  += input_tokens
        self.usage["output_tokens"] += output_tokens
        self.usage["total_cost"]    += cost

        if model not in self.usage["by_model"]:
            self.usage["by_model"][model] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        self.usage["by_model"][model]["input_tokens"]  += input_tokens
        self.usage["by_model"][model]["output_tokens"] += output_tokens
        self.usage["by_model"][model]["cost"]          += cost

        self._save_usage()
        return cost

    def get_total_usage(self) -> Dict:
        """Return a deep copy so callers cannot accidentally mutate internal state."""
        return copy.deepcopy(self.usage)

    # ------------------------------------------------------------------
    # Chat session management
    # ------------------------------------------------------------------

    def new_chat(self) -> str:
        """Start a blank new chat; returns the new chat ID."""
        self.current_chat_id = str(uuid.uuid4())
        self.current_messages = []
        return self.current_chat_id

    def add_message(
        self,
        role: str,
        content: str,
        stop_reason: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> Dict:
        """Append a message to the current chat and persist it."""
        msg: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "stop_reason": stop_reason,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        self.current_messages.append(msg)
        self._save_current_chat()
        return msg

    def _save_current_chat(self):
        if not self.current_chat_id:
            return
        chat_data = {
            "id": self.current_chat_id,
            "created": (
                self.current_messages[0]["timestamp"]
                if self.current_messages
                else datetime.now().isoformat()
            ),
            "messages": self.current_messages,
        }
        path = self.history_dir / f"{self.current_chat_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, indent=2)

    def list_chats(self) -> List[Dict]:
        """Return metadata for all saved chats, newest first."""
        chats = []
        for p in sorted(
            self.history_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        ):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            # Use first user message as the display title
            title = "Empty chat"
            for msg in data.get("messages", []):
                if msg["role"] == "user":
                    raw = msg["content"]
                    title = raw[:48] + ("…" if len(raw) > 48 else "")
                    break

            chats.append(
                {
                    "id": data["id"],
                    "title": title,
                    "created": data.get("created", ""),
                    "message_count": len(data.get("messages", [])),
                }
            )
        return chats

    def load_chat(self, chat_id: str) -> List[Dict]:
        """Load a past chat into memory and return its messages."""
        path = self.history_dir / f"{chat_id}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.current_chat_id = chat_id
                self.current_messages = data.get("messages", [])
                return self.current_messages
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def delete_chat(self, chat_id: str):
        """Remove a chat file from disk."""
        path = self.history_dir / f"{chat_id}.json"
        if path.exists():
            path.unlink()
        if self.current_chat_id == chat_id:
            self.current_chat_id = None
            self.current_messages = []
