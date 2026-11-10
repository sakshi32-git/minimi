"""
memory.py – Timestamped conversation memory with persistence.

Features:
  • Each message is stored with an ISO-8601 timestamp.
  • History is persisted to a JSON file per session.
  • Token-aware context window: trims old turns to stay under budget.
  • Supports listing past sessions and resuming them.
"""

from __future__ import annotations

import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger(__name__)


# ── Lightweight token estimator (avoids tiktoken import cost) ─
def _estimate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token for English."""
    return max(1, len(text) // 4)


try:
    import tiktoken

    _enc = tiktoken.encoding_for_model("gpt-4o-mini")

    def _count_tokens(text: str) -> int:
        return len(_enc.encode(text))

except Exception:
    _count_tokens = _estimate_tokens


class Message:
    """A single chat message with metadata."""

    __slots__ = ("role", "content", "timestamp", "tool_call_id",
                 "tool_calls", "name")

    def __init__(
        self,
        role: str,
        content: str | None,
        timestamp: str | None = None,
        tool_call_id: str | None = None,
        tool_calls: list[dict] | None = None,
        name: str | None = None,
    ):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.tool_call_id = tool_call_id
        self.tool_calls = tool_calls
        self.name = name

    # ── Serialisation ─────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.name:
            d["name"] = self.name
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Message":
        return cls(
            role=d["role"],
            content=d.get("content"),
            timestamp=d.get("timestamp"),
            tool_call_id=d.get("tool_call_id"),
            tool_calls=d.get("tool_calls"),
            name=d.get("name"),
        )

    def to_api(self) -> dict[str, Any]:
        """Convert to the format expected by OpenAI's chat API."""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.name:
            msg["name"] = self.name
        return msg


class ConversationMemory:
    """Manages a single conversation session with full history."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        self.messages: list[Message] = []
        self._file = config.MEMORY_DIR / f"{self.session_id}.json"

        # Resume if file exists
        if self._file.exists():
            self._load()
            logger.info("Resumed session %s (%d messages)", self.session_id, len(self.messages))

    # ── Public API ────────────────────────────────────────────
    def add(
        self,
        role: str,
        content: str | None,
        tool_call_id: str | None = None,
        tool_calls: list[dict] | None = None,
        name: str | None = None,
    ) -> Message:
        msg = Message(role, content, tool_call_id=tool_call_id,
                      tool_calls=tool_calls, name=name)
        self.messages.append(msg)
        self._save()
        return msg

    def get_context_messages(self) -> list[dict[str, Any]]:
        """
        Return the most recent messages that fit within the token budget.
        Always includes the system prompt as the first message.
        """
        system_msg = {"role": "system", "content": config.SYSTEM_PROMPT}
        budget = config.MAX_CONTEXT_TOKENS
        budget -= _count_tokens(config.SYSTEM_PROMPT)

        # Walk backwards to find the window
        selected: list[dict[str, Any]] = []
        tokens_used = 0

        for msg in reversed(self.messages):
            text = msg.content or ""
            t = _count_tokens(text)
            if tokens_used + t > budget:
                break
            selected.append(msg.to_api())
            tokens_used += t

        selected.reverse()

        # Enforce max-turns cap
        if len(selected) > config.MAX_CONTEXT_TURNS:
            selected = selected[-config.MAX_CONTEXT_TURNS:]

        return [system_msg] + selected

    def get_session_summary(self) -> dict[str, Any]:
        """Quick metadata about this session."""
        user_msgs = [m for m in self.messages if m.role == "user"]
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "user_message_count": len(user_msgs),
            "started": self.messages[0].timestamp if self.messages else None,
            "last_activity": self.messages[-1].timestamp if self.messages else None,
            "first_query": user_msgs[0].content[:80] if user_msgs else None,
        }

    # ── Persistence ───────────────────────────────────────────
    def _save(self) -> None:
        data = {
            "session_id": self.session_id,
            "messages": [m.to_dict() for m in self.messages],
        }
        self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        data = json.loads(self._file.read_text(encoding="utf-8"))
        self.messages = [Message.from_dict(d) for d in data["messages"]]

    # ── Class helpers ─────────────────────────────────────────
    @staticmethod
    def list_sessions() -> list[dict[str, Any]]:
        """List all saved sessions with metadata."""
        sessions = []
        for f in sorted(config.MEMORY_DIR.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                mem = ConversationMemory.__new__(ConversationMemory)
                mem.session_id = data["session_id"]
                mem.messages = [Message.from_dict(d) for d in data["messages"]]
                mem._file = f
                sessions.append(mem.get_session_summary())
            except Exception:
                continue
        return sessions

