"""
PersonalAssist CLI — terminal-first interface.

A minimal Rich + prompt_toolkit CLI that talks to the FastAPI backend.
Start the API server first, then run this script.

Usage:
    python cli.py                          # interactive chat (ReAct loop)
    python cli.py --model gemini-flash     # use a specific model
    python cli.py --url http://localhost:8000  # custom API URL
    python cli.py --jobs                   # list scheduled jobs

Requires:
    pip install rich prompt_toolkit httpx

The API server must be running:
    python -m uvicorn apps.api.main:app --reload
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

# ── Dependency check ─────────────────────────────────────────────────
try:
    import httpx
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
except ImportError as exc:
    print(f"Missing dependency: {exc}")
    print("Install with: pip install rich prompt_toolkit httpx")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────

DEFAULT_API_URL = os.getenv("PERSONALASSIST_API_URL", "http://127.0.0.1:8000")
DEFAULT_MODEL = os.getenv("PERSONALASSIST_MODEL", "local")
HISTORY_FILE = os.path.expanduser("~/.personalassist/cli_history")
API_TOKEN = os.getenv("API_ACCESS_TOKEN", "")

console = Console()

_PROMPT_STYLE = Style.from_dict({
    "prompt": "bold #7c6af7",
})

_BANNER = """[bold #7c6af7]PersonalAssist[/] [dim]— local-first AI assistant[/]
[dim]Type [bold]/help[/] for commands, [bold]/quit[/] to exit[/]"""

# ── API client ────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["x-api-token"] = API_TOKEN
    return h


async def _react_stream(message: str, model: str, thread_id: str | None, api_url: str) -> tuple[str, str]:
    """
    Call /chat/react/stream and print tokens as they arrive.
    Returns (full_response, thread_id).
    """
    payload: dict[str, Any] = {"message": message, "model": model}
    if thread_id:
        payload["thread_id"] = thread_id

    full_response = ""
    returned_thread_id = thread_id or ""

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{api_url}/chat/react/stream",
            json=payload,
            headers=_headers(),
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"API error {resp.status_code}: {body.decode()[:200]}")

            console.print()
            console.print("[bold #7c6af7]▎[/] ", end="")

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue

                if "error" in obj:
                    console.print(f"\n[red]Error: {obj['error']}[/]")
                    break
                if "thread_id" in obj:
                    returned_thread_id = obj["thread_id"]
                if "text" in obj:
                    chunk = obj["text"]
                    full_response += chunk
                    console.print(chunk, end="", highlight=False)

            console.print()  # newline after response

    return full_response, returned_thread_id


async def _list_jobs(api_url: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{api_url}/scheduler/jobs", headers=_headers())
        resp.raise_for_status()
        data = resp.json()

    jobs = data.get("jobs", [])
    if not jobs:
        console.print("[dim]No scheduled jobs registered.[/]")
        return

    from rich.table import Table
    table = Table(title="Scheduled Jobs", show_header=True, header_style="bold #7c6af7")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Schedule")
    table.add_column("Last Run", style="dim")
    table.add_column("Runs", justify="right")
    table.add_column("Enabled")

    for j in jobs:
        table.add_row(
            j.get("id", ""),
            j.get("name", ""),
            j.get("cron_expr", ""),
            (j.get("last_run_at") or "never")[:19],
            str(j.get("run_count", 0)),
            "✓" if j.get("enabled") else "✗",
        )
    console.print(table)


async def _check_health(api_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{api_url}/health")
            return resp.status_code == 200
    except Exception:
        return False


# ── Slash commands ────────────────────────────────────────────────────

_COMMANDS = {
    "/help": "Show this help",
    "/quit": "Exit the CLI",
    "/exit": "Exit the CLI",
    "/new": "Start a new conversation thread",
    "/jobs": "List scheduled background jobs",
    "/model <name>": "Switch model (local, gemini, claude, deepseek)",
    "/health": "Check API server health",
    "/clear": "Clear the screen",
}


def _show_help() -> None:
    lines = ["[bold]Available commands:[/]"]
    for cmd, desc in _COMMANDS.items():
        lines.append(f"  [bold #7c6af7]{cmd:<20}[/] {desc}")
    console.print("\n".join(lines))
    console.print()


# ── Main loop ─────────────────────────────────────────────────────────

async def run_cli(api_url: str, model: str) -> None:
    # Check API is reachable
    if not await _check_health(api_url):
        console.print(f"[red]Cannot reach API at {api_url}[/]")
        console.print("[dim]Start the server with: python -m uvicorn apps.api.main:app --reload[/]")
        sys.exit(1)

    console.print(Panel(_BANNER, border_style="#7c6af7", padding=(0, 1)))
    console.print(f"[dim]API: {api_url}  Model: {model}[/]\n")

    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    session: PromptSession = PromptSession(
        history=FileHistory(HISTORY_FILE),
        auto_suggest=AutoSuggestFromHistory(),
        style=_PROMPT_STYLE,
    )

    thread_id: str | None = None
    current_model = model

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: session.prompt("you › ", style=_PROMPT_STYLE),
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # ── Slash commands ────────────────────────────────────────────
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()

            if cmd in ("/quit", "/exit"):
                console.print("[dim]Goodbye.[/]")
                break
            elif cmd == "/help":
                _show_help()
            elif cmd == "/new":
                thread_id = None
                console.print("[dim]Started new conversation.[/]\n")
            elif cmd == "/jobs":
                await _list_jobs(api_url)
            elif cmd == "/health":
                ok = await _check_health(api_url)
                status = "[green]online[/]" if ok else "[red]offline[/]"
                console.print(f"API {api_url}: {status}\n")
            elif cmd == "/clear":
                console.clear()
            elif cmd == "/model":
                if len(parts) > 1:
                    current_model = parts[1].strip()
                    console.print(f"[dim]Model switched to: {current_model}[/]\n")
                else:
                    console.print(f"[dim]Current model: {current_model}[/]\n")
            else:
                console.print(f"[dim]Unknown command: {cmd}. Type /help for available commands.[/]\n")
            continue

        # ── Chat ──────────────────────────────────────────────────────
        try:
            _, thread_id = await _react_stream(user_input, current_model, thread_id, api_url)
            console.print()
        except KeyboardInterrupt:
            console.print("\n[dim](interrupted)[/]\n")
        except Exception as exc:
            console.print(f"\n[red]Error: {exc}[/]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PersonalAssist CLI — terminal-first AI assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API server URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model to use (local, gemini, claude, deepseek)")
    parser.add_argument("--jobs", action="store_true", help="List scheduled jobs and exit")
    args = parser.parse_args()

    if args.jobs:
        asyncio.run(_list_jobs(args.url))
        return

    asyncio.run(run_cli(args.url, args.model))


if __name__ == "__main__":
    main()
