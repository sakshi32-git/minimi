"""
config.py – Central configuration for the Search Chat Agent.

All tunables live here so nothing is scattered across modules.
"""

import os
from pathlib import Path

# ──────────────────────── LLM Provider ────────────────────────
# Supported: "openai", "gemini"  (add more by extending llm.py)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

# OpenAI
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Google Gemini (optional fallback)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# ──────────────────────── Web Search ──────────────────────────
SEARCH_MAX_RESULTS: int = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
SEARCH_REGION: str = os.getenv("SEARCH_REGION", "wt-wt")       # worldwide
SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT", "8"))     # seconds

# ──────────────────────── Memory / History ────────────────────
MEMORY_DIR: Path = Path(os.getenv(
    "MEMORY_DIR",
    Path.home() / ".search_chat_agent" / "memory",
))
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

MAX_CONTEXT_TURNS: int = int(os.getenv("MAX_CONTEXT_TURNS", "50"))
MAX_CONTEXT_TOKENS: int = int(os.getenv("MAX_CONTEXT_TOKENS", "12000"))

# ──────────────────────── Agent Behaviour ─────────────────────
SYSTEM_PROMPT: str = """You are a fast, accurate research assistant.

RULES
1. Answer the user's question directly and concisely.
2. When you need up-to-date or factual information you are unsure about,
   call the `web_search` tool. Always prefer searching over guessing.
3. Cite your sources inline using [Source Title](url) markdown links.
4. If the user references something from earlier in the conversation,
   use the chat history provided to you — do NOT ask them to repeat it.
5. If you cannot find a reliable answer, say so honestly.
6. Keep answers under ~400 words unless asked for more detail.
"""

# ──────────────────────── Display ─────────────────────────────
RICH_THEME: str = "monokai"
PROMPT_STYLE: str = "bold cyan"
ASSISTANT_STYLE: str = "green"
SEARCH_STYLE: str = "dim yellow"

