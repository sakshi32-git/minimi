# 🔍 Search Chat Agent

A fast, accurate, memory-aware conversational AI agent with **one tool — web search**.

## Features

| Feature | Detail |
|---------|--------|
| ⚡ **Fast** | `gpt-4o-mini` + 5-result search cap = sub-3s responses |
| 🎯 **Accurate** | DuckDuckGo search via OpenAI function-calling; cites sources inline |
| 🧠 **Memory** | Every message timestamped (ISO 8601 UTC), persisted to JSON, session resume |
| 🖥️ **Rich CLI** | Markdown rendering, spinners, `/commands` |

## Quick Start

```bash
pip install -r requirements.txt
set OPENAI_API_KEY=sk-...           # Windows
export OPENAI_API_KEY=sk-...        # Linux/Mac
python main.py
```

## Commands

| Command | Action |
|---------|--------|
| `/help` | Show all commands |
| `/sessions` | List saved sessions |
| `/info` | Current session metadata |
| `/clear` | Start a new session |
| `/exit` | Save & quit |

## CLI Flags

```bash
python main.py                      # New session
python main.py --session <id>       # Resume a session
python main.py --list-sessions      # Show saved sessions
```

## Architecture

```
main.py  →  agent.py  →  llm.py  →  search_tool.py  →  DuckDuckGo
                ↕
            memory.py  →  ~/.search_chat_agent/memory/*.json
```

See [DESIGN.md](DESIGN.md) for full architecture diagrams and design decisions.

## Tests

```bash
python -m pytest tests/ -v
```

14 unit tests covering memory, search, schema, and error handling.

## License

MIT
