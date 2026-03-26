"""
Agent Tools — callable tool functions for agent orchestration.

This module provides:
  - Tool implementations (memory/filesystem/git/exec)
  - Tool registry metadata with JSON schemas and risk labels
  - Runtime arg validation + normalized execution envelopes
  - Conversion helpers for OpenAI-compatible `tools` payloads
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

TOOL_RISK_READ = "read"
TOOL_RISK_WRITE = "write"
TOOL_RISK_EXEC = "exec"


def _is_mutating_risk(risk: str) -> bool:
    return risk in {TOOL_RISK_WRITE, TOOL_RISK_EXEC}


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "null":
        return value is None
    return True


def _validate_tool_args(tool_name: str, args: Any, schema: dict[str, Any]) -> tuple[bool, str | None, dict[str, Any]]:
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return False, f"Invalid args for {tool_name}: expected object", {}

    fn_schema = schema.get("function", schema)
    params = fn_schema.get("parameters", {})
    expected_props = params.get("properties", {})
    required = set(params.get("required", []))
    additional = params.get("additionalProperties", True)

    for req in required:
        if req not in args:
            return False, f"Missing required argument '{req}' for {tool_name}", {}

    if additional is False:
        unknown = [k for k in args.keys() if k not in expected_props]
        if unknown:
            return False, f"Unknown arguments for {tool_name}: {', '.join(sorted(unknown))}", {}

    for key, spec in expected_props.items():
        if key not in args:
            continue
        value = args[key]
        expected_type = spec.get("type")
        if isinstance(expected_type, list):
            if not any(_type_matches(value, t) for t in expected_type):
                return False, f"Argument '{key}' has invalid type for {tool_name}", {}
        elif isinstance(expected_type, str):
            if not _type_matches(value, expected_type):
                return False, f"Argument '{key}' has invalid type for {tool_name}", {}

    return True, None, args


def _normalize_tool_payload(payload: Any) -> tuple[Any, str]:
    preview = ""
    try:
        if isinstance(payload, str):
            preview = payload[:400]
        elif isinstance(payload, (dict, list)):
            serialized = json.dumps(payload, ensure_ascii=False)
            preview = serialized[:400]
        else:
            preview = str(payload)[:400]
    except Exception:
        preview = str(payload)[:400]
    return payload, preview


# ── Memory Tools ─────────────────────────────────────────────────────


async def search_user_memories(
    query: str,
    user_id: str = "default",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search Mem0 for user-related facts and preferences."""
    try:
        from packages.memory.mem0_client import mem0_search

        results = mem0_search(query, user_id=user_id, limit=limit)
        return results
    except Exception as exc:
        logger.warning("Memory search failed: %s", exc)
        return []


async def search_documents(
    query: str,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Search Qdrant for ingested document/code chunks."""
    try:
        from packages.memory.qdrant_store import search

        results = await search(
            query=query,
            k=k,
            filter_conditions={"content_type": "document"},
        )
        return results
    except Exception as exc:
        logger.warning("Document search failed: %s", exc)
        return []


# ── File System Tools ────────────────────────────────────────────────


async def read_file(
    path: str,
    max_lines: int | None = None,
) -> dict[str, Any]:
    """Read a file's contents (size-capped, safe)."""
    from packages.tools.fs import read_file as _read

    return await _read(path, max_lines=max_lines)


async def write_file(
    path: str,
    content: str,
) -> dict[str, Any]:
    """Write content to a file (blocks writes to protected system dirs)."""
    from packages.tools.fs import write_file as _write

    return await _write(path, content)


async def find_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = True,
    max_results: int = 50,
) -> dict[str, Any]:
    """Search for files matching a glob pattern."""
    from packages.tools.fs import find_files as _find

    return await _find(directory, pattern=pattern, recursive=recursive, max_results=max_results)


async def list_directory(path: str) -> dict[str, Any]:
    """List contents of a directory with metadata."""
    from packages.tools.fs import list_directory as _ls

    return await _ls(path)


async def file_info(path: str) -> dict[str, Any]:
    """Get detailed metadata about a file or directory."""
    from packages.tools.fs import file_info as _info

    return await _info(path)


# ── Git / Repository Tools ───────────────────────────────────────────


async def git_status(repo_path: str) -> dict[str, Any]:
    """Get the working tree status of a git repository."""
    from packages.tools.repo import git_status as _status

    return await _status(repo_path)


async def git_log(
    repo_path: str,
    max_commits: int = 10,
) -> dict[str, Any]:
    """Get recent commit history."""
    from packages.tools.repo import git_log as _log

    return await _log(repo_path, max_commits=max_commits)


async def git_diff(
    repo_path: str,
    staged: bool = False,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Get the diff of changes in the working tree."""
    from packages.tools.repo import git_diff as _diff

    return await _diff(repo_path, staged=staged, file_path=file_path)


async def repo_summary(repo_path: str) -> dict[str, Any]:
    """Generate a high-level summary of a git repository."""
    from packages.tools.repo import repo_summary as _summary

    return await _summary(repo_path)


# ── Command Execution Tools ─────────────────────────────────────────


async def exec_command(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Execute a shell command in a sandboxed subprocess.

    Pre-approved commands run immediately. Others return 'pending_approval'.
    """
    from packages.tools.exec import run_command

    return await run_command(command, cwd=cwd, timeout=timeout)


async def exec_approved_command(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute a user-approved command (bypasses the allowlist check)."""
    from packages.tools.exec import run_approved_command

    return await run_approved_command(command, cwd=cwd, timeout=timeout)


def check_command_safety(command: str) -> dict[str, Any]:
    """Check if a command is allowed, blocked, or requires approval."""
    from packages.tools.exec import check_allowlist

    return check_allowlist(command)


# ── Formatting ───────────────────────────────────────────────────────


async def format_tool_results(
    memories: list[dict],
    documents: list[dict],
    tool_results: list[dict] | None = None,
) -> str:
    """Format tool results into a context string for the next agent."""
    parts = []

    if memories:
        lines = ["### User Memories"]
        for i, m in enumerate(memories, 1):
            text = m.get("memory", m.get("content", ""))
            if text:
                lines.append(f"  {i}. {text}")
        parts.append("\n".join(lines))

    if documents:
        lines = ["### Relevant Documents"]
        for i, d in enumerate(documents, 1):
            source = d.get("metadata", {}).get("source_path", "unknown")
            content = d.get("content", "")[:300]
            lines.append(f"  {i}. [{source}] {content}")
        parts.append("\n".join(lines))

    if tool_results:
        lines = ["### Tool Results"]
        for i, t in enumerate(tool_results, 1):
            name = t.get("name", "unknown")
            success = t.get("success")
            if success is False or "error" in t:
                lines.append(f"  {i}. {name}: ERROR - {t.get('error', 'unknown error')}")
            else:
                preview = t.get("preview")
                if not preview:
                    preview = str(t.get("payload", t.get("result", "")))[:400]
                lines.append(f"  {i}. {name}: {preview}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts) if parts else "No relevant context found."


def build_native_tool_schemas(
    *,
    allow_exec_tools: bool = False,
    allow_mutating_tools: bool = False,
) -> list[dict[str, Any]]:
    """
    Convert tool registry entries into OpenAI-compatible tool schemas.
    """
    schemas: list[dict[str, Any]] = []
    for name, info in TOOL_REGISTRY.items():
        risk = info.get("risk", TOOL_RISK_READ)
        if risk == TOOL_RISK_EXEC and not allow_exec_tools:
            continue
        if _is_mutating_risk(risk) and not allow_mutating_tools:
            continue
        schema = info.get("schema")
        if schema:
            schemas.append(schema)
    return schemas


def get_allowed_tools(
    *,
    allow_exec_tools: bool = False,
    allow_mutating_tools: bool = False,
) -> dict[str, dict[str, Any]]:
    """
    Return registry filtered by risk policy.
    """
    allowed: dict[str, dict[str, Any]] = {}
    for name, info in TOOL_REGISTRY.items():
        risk = info.get("risk", TOOL_RISK_READ)
        if risk == TOOL_RISK_EXEC and not allow_exec_tools:
            continue
        if _is_mutating_risk(risk) and not allow_mutating_tools:
            continue
        allowed[name] = info
    return allowed


async def execute_registered_tool(
    name: str,
    args: Any,
    *,
    allow_exec_tools: bool = False,
    allow_mutating_tools: bool = False,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    """
    Validate + execute a tool call and return a normalized envelope.
    """
    tools = get_allowed_tools(
        allow_exec_tools=allow_exec_tools,
        allow_mutating_tools=allow_mutating_tools,
    )
    if name not in tools:
        return {
            "name": name,
            "success": False,
            "error": "Tool not allowed or not found",
            "payload": None,
            "preview": "",
        }

    tool_info = tools[name]
    schema = tool_info.get("schema", {})
    valid, validation_error, normalized_args = _validate_tool_args(name, args, schema)
    if not valid:
        return {
            "name": name,
            "success": False,
            "error": validation_error or "Invalid arguments",
            "payload": None,
            "preview": "",
        }

    try:
        fn = tool_info["fn"]
        if inspect.iscoroutinefunction(fn):
            call = fn(**normalized_args)
            result = await asyncio.wait_for(call, timeout=timeout_seconds)
        else:
            maybe = fn(**normalized_args)
            if inspect.isawaitable(maybe):
                result = await asyncio.wait_for(maybe, timeout=timeout_seconds)
            else:
                result = maybe
        payload, preview = _normalize_tool_payload(result)
        return {
            "name": name,
            "success": True,
            "error": None,
            "payload": payload,
            "preview": preview,
        }
    except asyncio.TimeoutError:
        return {
            "name": name,
            "success": False,
            "error": f"Tool timed out after {timeout_seconds}s",
            "payload": None,
            "preview": "",
        }
    except Exception as exc:
        return {
            "name": name,
            "success": False,
            "error": str(exc),
            "payload": None,
            "preview": "",
        }


# ── Tool Registry ───────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    # Memory
    "search_user_memories": {
        "fn": search_user_memories,
        "category": "memory",
        "risk": TOOL_RISK_READ,
        "description": "Search for user-related facts/preferences in Mem0",
        "schema": {
            "type": "function",
            "function": {
                "name": "search_user_memories",
                "description": "Search user memories by semantic query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "user_id": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "search_documents": {
        "fn": search_documents,
        "category": "memory",
        "risk": TOOL_RISK_READ,
        "description": "Search for ingested documents/code in Qdrant",
        "schema": {
            "type": "function",
            "function": {
                "name": "search_documents",
                "description": "Search indexed documents by semantic query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "k": {"type": "integer"},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
    },
    # File System
    "read_file": {
        "fn": read_file,
        "category": "filesystem",
        "risk": TOOL_RISK_READ,
        "description": "Read the contents of a local file",
        "schema": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a local file with optional line limit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "max_lines": {"type": ["integer", "null"]},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "write_file": {
        "fn": write_file,
        "category": "filesystem",
        "risk": TOOL_RISK_WRITE,
        "description": "Write content to a local file (safe)",
        "schema": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write text to a local file path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "find_files": {
        "fn": find_files,
        "category": "filesystem",
        "risk": TOOL_RISK_READ,
        "description": "Search for files matching a glob pattern",
        "schema": {
            "type": "function",
            "function": {
                "name": "find_files",
                "description": "Search files in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string"},
                        "pattern": {"type": "string"},
                        "recursive": {"type": "boolean"},
                        "max_results": {"type": "integer"},
                    },
                    "required": ["directory"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "list_directory": {
        "fn": list_directory,
        "category": "filesystem",
        "risk": TOOL_RISK_READ,
        "description": "List contents of a directory",
        "schema": {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List directory entries and metadata.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "file_info": {
        "fn": file_info,
        "category": "filesystem",
        "risk": TOOL_RISK_READ,
        "description": "Get detailed metadata about a file or directory",
        "schema": {
            "type": "function",
            "function": {
                "name": "file_info",
                "description": "Get metadata for a file or directory path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
    },
    # Git
    "git_status": {
        "fn": git_status,
        "category": "git",
        "risk": TOOL_RISK_READ,
        "description": "Get working tree status of a git repo",
        "schema": {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Get git status for a repository path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string"},
                    },
                    "required": ["repo_path"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "git_log": {
        "fn": git_log,
        "category": "git",
        "risk": TOOL_RISK_READ,
        "description": "Get recent commit history",
        "schema": {
            "type": "function",
            "function": {
                "name": "git_log",
                "description": "Get recent commit history for a repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string"},
                        "max_commits": {"type": "integer"},
                    },
                    "required": ["repo_path"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "git_diff": {
        "fn": git_diff,
        "category": "git",
        "risk": TOOL_RISK_READ,
        "description": "Get diff of changes in working tree",
        "schema": {
            "type": "function",
            "function": {
                "name": "git_diff",
                "description": "Get git diff for a repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string"},
                        "staged": {"type": "boolean"},
                        "file_path": {"type": ["string", "null"]},
                    },
                    "required": ["repo_path"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "repo_summary": {
        "fn": repo_summary,
        "category": "git",
        "risk": TOOL_RISK_READ,
        "description": "Generate a high-level summary of a git repository",
        "schema": {
            "type": "function",
            "function": {
                "name": "repo_summary",
                "description": "Summarize repository status and branches.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string"},
                    },
                    "required": ["repo_path"],
                    "additionalProperties": False,
                },
            },
        },
    },
    # Execution
    "exec_command": {
        "fn": exec_command,
        "category": "execution",
        "risk": TOOL_RISK_EXEC,
        "description": "Execute a shell command (sandboxed, requires allowlist or approval)",
        "schema": {
            "type": "function",
            "function": {
                "name": "exec_command",
                "description": "Execute a shell command in a sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": ["string", "null"]},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        },
    },
}
