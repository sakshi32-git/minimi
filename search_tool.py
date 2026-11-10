"""
search_tool.py – The agent's ONE tool: web search via DuckDuckGo.

Returns a JSON-serialisable list of {title, url, snippet} dicts.
Fast timeout + result cap keeps latency low.
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any

from duckduckgo_search import DDGS

import config

logger = logging.getLogger(__name__)

# ── Tool schema (OpenAI function-calling format) ──────────────
TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information. Use when the user asks "
            "about recent events, facts you're unsure about, or anything that "
            "needs up-to-date data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string.",
                },
            },
            "required": ["query"],
        },
    },
}


def web_search(query: str) -> list[dict[str, str]]:
    """Execute a DuckDuckGo search and return structured results."""
    start = time.perf_counter()
    logger.info("🔍  Searching: %s", query)

    try:
        with DDGS() as ddgs:
            raw = ddgs.text(
                keywords=query,
                region=config.SEARCH_REGION,
                max_results=config.SEARCH_MAX_RESULTS,
                backend="auto",
            )
    except Exception as exc:
        logger.warning("Search failed: %s", exc)
        return [{"title": "Search error", "url": "", "snippet": str(exc)}]

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("href", r.get("link", "")),
            "snippet": r.get("body", r.get("snippet", "")),
        }
        for r in (raw or [])
    ]

    elapsed = time.perf_counter() - start
    logger.info("   ↳ %d results in %.2fs", len(results), elapsed)
    return results


def execute_tool_call(name: str, arguments: str | dict) -> str:
    """Dispatch a tool call by name. Returns JSON string."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if name == "web_search":
        return json.dumps(web_search(arguments["query"]), ensure_ascii=False)

    raise ValueError(f"Unknown tool: {name}")

