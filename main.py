"""
main.py – Rich terminal UI for the Search Chat Agent.

Run:  python main.py [--session <id>] [--list-sessions]
"""

from __future__ import annotations

import sys
import argparse
import logging

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

import config
from agent import SearchAgent
from memory import ConversationMemory

console = Console()


# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-14s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.FileHandler(config.MEMORY_DIR / "agent.log", encoding="utf-8")],
)


def _on_search(query: str, results: list[dict]) -> None:
    """Callback: show a brief search indicator in the terminal."""
    console.print(f"  🔍 Searched: [bold yellow]{query}[/]  ({len(results)} results)")


def _print_banner(session_id: str) -> None:
    banner = Text.assemble(
        ("╭─── Search Chat Agent ───╮\n", "bold cyan"),
        ("│                         │\n", "cyan"),
        ("│  One tool. Fast answers. │\n", "cyan"),
        ("│  Type /help for commands │\n", "cyan"),
        ("│                         │\n", "cyan"),
        (f"│  Session: {session_id[:16]}… │\n", "dim"),
        ("╰─────────────────────────╯", "bold cyan"),
    )
    console.print(banner)
    console.print()


def _handle_slash(cmd: str, agent: SearchAgent) -> bool:
    """Handle /commands. Returns True if the command was handled."""
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()

    if command in ("/help", "/h"):
        console.print(Panel(
            "[bold]/help[/]       – Show this help\n"
            "[bold]/sessions[/]   – List saved sessions\n"
            "[bold]/info[/]       – Current session info\n"
            "[bold]/clear[/]      – Start a new session\n"
            "[bold]/exit, /quit[/] – Exit the agent",
            title="Commands", border_style="cyan",
        ))
        return True

    if command == "/sessions":
        sessions = ConversationMemory.list_sessions()
        if not sessions:
            console.print("[dim]No saved sessions.[/]")
        for s in sessions[:10]:
            console.print(
                f"  [cyan]{s['session_id']}[/]  "
                f"msgs={s['message_count']}  "
                f"started={s['started']}  "
                f"[dim]{s.get('first_query', '')}[/]"
            )
        return True

    if command == "/info":
        info = agent.session_info()
        for k, v in info.items():
            console.print(f"  [cyan]{k}:[/] {v}")
        return True

    if command == "/clear":
        console.print("[dim]Starting new session…[/]")
        agent.__init__(on_search=_on_search)  # type: ignore[misc]
        _print_banner(agent.session_id)
        return True

    if command in ("/exit", "/quit", "/q"):
        console.print("[dim]Goodbye! Session saved.[/]")
        sys.exit(0)

    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Chat Agent")
    parser.add_argument("--session", "-s", help="Resume a previous session by ID")
    parser.add_argument("--list-sessions", "-l", action="store_true",
                        help="List saved sessions and exit")
    args = parser.parse_args()

    if args.list_sessions:
        for s in ConversationMemory.list_sessions():
            print(f"{s['session_id']}  msgs={s['message_count']}  {s.get('first_query', '')}")
        return

    # ── Validate API key ──────────────────────────────────────
    if not config.OPENAI_API_KEY:
        console.print(
            "[bold red]Error:[/] Set your OpenAI API key:\n"
            "  [cyan]set OPENAI_API_KEY=sk-...[/]  (Windows)\n"
            "  [cyan]export OPENAI_API_KEY=sk-...[/]  (Linux/Mac)\n"
        )
        sys.exit(1)

    agent = SearchAgent(session_id=args.session, on_search=_on_search)
    _print_banner(agent.session_id)

    # ── REPL ──────────────────────────────────────────────────
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye! Session saved.[/]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if _handle_slash(user_input, agent):
                continue

        with console.status("[bold green]Thinking…[/]", spinner="dots"):
            try:
                reply = agent.ask(user_input)
            except Exception as exc:
                console.print(f"[bold red]Error:[/] {exc}")
                logging.exception("Agent error")
                continue

        console.print()
        console.print(Markdown(reply))
        console.print()


if __name__ == "__main__":
    main()

