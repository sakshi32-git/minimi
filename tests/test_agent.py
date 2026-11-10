"""
tests/test_agent.py – Unit tests for core components.

Run:  python -m pytest tests/ -v
"""

import json
import sys
import os
import types
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from memory import ConversationMemory, Message, _estimate_tokens
from search_tool import web_search, execute_tool_call, TOOL_SCHEMA


# ═══════════════════════ Memory Tests ═════════════════════════

class TestMessage:
    def test_roundtrip(self):
        msg = Message("user", "hello world")
        d = msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.role == "user"
        assert restored.content == "hello world"
        assert restored.timestamp == msg.timestamp

    def test_to_api_minimal(self):
        msg = Message("assistant", "hi")
        api = msg.to_api()
        assert api == {"role": "assistant", "content": "hi"}

    def test_to_api_with_tool_call_id(self):
        msg = Message("tool", "result", tool_call_id="tc_123")
        api = msg.to_api()
        assert api["tool_call_id"] == "tc_123"

    def test_timestamp_auto_set(self):
        msg = Message("user", "test")
        assert msg.timestamp is not None
        assert "T" in msg.timestamp  # ISO format


class TestConversationMemory:
    def setup_method(self):
        """Use a temp dir for each test."""
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        config.MEMORY_DIR = Path(self._tmpdir)

    def test_add_and_retrieve(self):
        mem = ConversationMemory()
        mem.add("user", "What is Python?")
        mem.add("assistant", "A programming language.")
        assert len(mem.messages) == 2
        assert mem.messages[0].role == "user"

    def test_persistence(self):
        mem = ConversationMemory()
        sid = mem.session_id
        mem.add("user", "test question")
        mem.add("assistant", "test answer")

        # Reload from disk
        mem2 = ConversationMemory(session_id=sid)
        assert len(mem2.messages) == 2
        assert mem2.messages[0].content == "test question"

    def test_context_window_respects_token_limit(self):
        config.MAX_CONTEXT_TOKENS = 100  # very small budget
        mem = ConversationMemory()
        for i in range(50):
            mem.add("user", f"Message number {i} with some extra padding text here")
        ctx = mem.get_context_messages()
        # Should be trimmed: system + some recent messages, not all 50
        assert len(ctx) < 52  # 50 msgs + system + buffer
        assert ctx[0]["role"] == "system"

    def test_session_summary(self):
        mem = ConversationMemory()
        mem.add("user", "First question ever")
        mem.add("assistant", "Answer")
        info = mem.get_session_summary()
        assert info["message_count"] == 2
        assert info["user_message_count"] == 1
        assert "First question" in info["first_query"]

    def test_list_sessions(self):
        mem1 = ConversationMemory()
        mem1.add("user", "session one")
        mem2 = ConversationMemory()
        mem2.add("user", "session two")
        sessions = ConversationMemory.list_sessions()
        assert len(sessions) >= 2


class TestTokenEstimator:
    def test_estimate_tokens(self):
        assert _estimate_tokens("hello") >= 1
        assert _estimate_tokens("a" * 400) == 100


# ═══════════════════════ Search Tool Tests ════════════════════

class TestToolSchema:
    def test_schema_structure(self):
        assert TOOL_SCHEMA["type"] == "function"
        func = TOOL_SCHEMA["function"]
        assert func["name"] == "web_search"
        assert "query" in func["parameters"]["properties"]
        assert "query" in func["parameters"]["required"]


class TestExecuteToolCall:
    def test_unknown_tool_raises(self):
        try:
            execute_tool_call("unknown_tool", '{"x": 1}')
            assert False, "Should have raised"
        except ValueError as e:
            assert "Unknown tool" in str(e)

    @patch("search_tool.DDGS")
    def test_web_search_returns_list(self, mock_ddgs):
        mock_instance = MagicMock()
        mock_instance.__enter__ = lambda s: s
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.text.return_value = [
            {"title": "Test", "href": "https://example.com", "body": "A snippet"},
        ]
        mock_ddgs.return_value = mock_instance

        results = web_search("test query")
        assert len(results) == 1
        assert results[0]["title"] == "Test"
        assert results[0]["url"] == "https://example.com"

    @patch("search_tool.DDGS")
    def test_web_search_handles_failure(self, mock_ddgs):
        mock_ddgs.side_effect = Exception("Network down")
        results = web_search("test")
        assert len(results) == 1
        assert "error" in results[0]["title"].lower()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

