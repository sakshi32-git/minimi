"""
agent.py – The core Agent class.

Ties together memory, search, and LLM into a clean interface that the
CLI (or any future UI) can call with a single method: ``agent.ask(question)``.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from memory import ConversationMemory
from llm import chat_completion

logger = logging.getLogger(__name__)


class SearchAgent:
    """
    A conversational agent with one tool — web search — and persistent memory.

    Usage
    -----
    >>> agent = SearchAgent()
    >>> reply = agent.ask("What's the latest on the Mars mission?")
    >>> print(reply)
    """

    def __init__(
        self,
        session_id: str | None = None,
        on_search: Callable[[str, list[dict]], None] | None = None,
    ):
        self.memory = ConversationMemory(session_id)
        self.on_search = on_search

    def ask(self, question: str) -> str:
        """Send a user message and get the assistant's reply."""
        # 1. Record the user turn
        self.memory.add("user", question)

        # 2. Build the context window
        messages = self.memory.get_context_messages()

        # 3. Call the LLM (may trigger tool calls internally)
        reply, tool_msgs = chat_completion(messages, on_search=self.on_search)

        # 4. Store intermediate tool messages in memory
        for tm in tool_msgs:
            self.memory.add(
                role=tm["role"],
                content=tm.get("content"),
                tool_call_id=tm.get("tool_call_id"),
                tool_calls=tm.get("tool_calls"),
            )

        # 5. Store the final assistant reply
        self.memory.add("assistant", reply)

        return reply

    @property
    def session_id(self) -> str:
        return self.memory.session_id

    def session_info(self) -> dict[str, Any]:
        return self.memory.get_session_summary()

