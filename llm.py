"""
llm.py – LLM abstraction layer.

Wraps OpenAI (primary) and Google Gemini (optional fallback).
Handles tool-call loops: the agent keeps calling tools until the LLM
produces a final text response.
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any

from openai import OpenAI

import config
from search_tool import TOOL_SCHEMA, execute_tool_call

logger = logging.getLogger(__name__)


def _build_client() -> OpenAI:
    """Construct the OpenAI client (works with any compatible endpoint)."""
    return OpenAI(api_key=config.OPENAI_API_KEY)


def chat_completion(
    messages: list[dict[str, Any]],
    on_search: Any | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Run a full agent turn (may involve multiple tool calls).

    Parameters
    ----------
    messages : list
        The conversation so far (system + history + latest user turn).
    on_search : callable, optional
        Callback ``(query: str, results: list)`` invoked when a search runs,
        so the UI can display live progress.

    Returns
    -------
    (reply_text, tool_messages)
        The assistant's final answer and any intermediate tool messages that
        should be appended to memory.
    """
    client = _build_client()
    tool_messages: list[dict[str, Any]] = []

    # Loop: the LLM may issue one or more tool calls before answering
    for _round in range(5):                       # safety cap
        start = time.perf_counter()

        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            tools=[TOOL_SCHEMA],
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1024,
        )

        elapsed = time.perf_counter() - start
        choice = response.choices[0]
        logger.info("LLM round %d  (%.2fs)  finish=%s",
                     _round, elapsed, choice.finish_reason)

        # ── Final text answer ─────────────────────────────────
        if choice.finish_reason == "stop" or not choice.message.tool_calls:
            return choice.message.content or "", tool_messages

        # ── Tool calls ────────────────────────────────────────
        # Append assistant message with tool_calls to context
        assistant_msg = {
            "role": "assistant",
            "content": choice.message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ],
        }
        messages.append(assistant_msg)
        tool_messages.append(assistant_msg)

        for tc in choice.message.tool_calls:
            args = json.loads(tc.function.arguments)
            result = execute_tool_call(tc.function.name, args)

            if on_search and tc.function.name == "web_search":
                on_search(args.get("query", ""), json.loads(result))

            tool_msg = {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            }
            messages.append(tool_msg)
            tool_messages.append(tool_msg)

    return "I ran out of search rounds — please try rephrasing.", tool_messages

