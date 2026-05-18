"""
ReAct Agent Loop — single-pass iterative Reason + Act engine.

Replaces the 3-stage Planner → Researcher → Synthesizer crew pipeline
for standard requests. The model reasons and calls tools in one loop,
deciding when it has enough information to respond.

Design principles (from Hermes agent architecture):
  - One LLM call per iteration, not three
  - Model drives the loop; it stops when it has an answer
  - Native tool calling when the model supports it; graceful fallback otherwise
  - Streaming-first: yields tokens as they arrive
  - Context is assembled once before the loop starts
  - Memory extraction happens after the final response

Usage:
    from packages.agents.react_loop import run_react, run_react_stream

    # Non-streaming
    result = await run_react(user_message, user_id="default", model="local")

    # Streaming (yields str chunks)
    async for chunk in run_react_stream(user_message, user_id="default", model="local"):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from packages.agents.tools import (
    build_native_tool_schemas,
    execute_registered_tool,
    get_allowed_tools,
)
from packages.agents.trace import TraceEvent, trace_manager
from packages.model_gateway.client import chat_completion, chat_stream
from packages.model_gateway.registry import infer_model_capabilities
from packages.shared.config import settings
from packages.shared.text_budget import clip_text_to_token_budget

logger = logging.getLogger(__name__)

# ── System prompt ────────────────────────────────────────────────────

_REACT_SYSTEM = """You are a helpful personal AI assistant running locally on the user's computer.

You have access to tools for reading files, searching memory, running git commands, and executing safe shell commands.

Guidelines:
- Answer directly when you already know the answer — don't call tools unnecessarily.
- Use tools when they materially improve the answer (e.g. reading a file, checking git status).
- Prefer read-only tools. Ask before writing or executing.
- Keep tool calls focused — one clear purpose per call.
- When you have enough information, stop calling tools and write your final response.
- Be concise and practical. This is a local assistant, not a search engine.
- You do NOT have live internet access. If a user asks for current news, live prices,
  or real-time data, say so clearly rather than guessing or presenting stale data as current.
- Your knowledge has a training cutoff. For fast-moving topics (job market, recent releases,
  current events), acknowledge the limitation and offer what you do know up to your cutoff.
"""

# ── Constants ────────────────────────────────────────────────────────

_MAX_ITERATIONS = 8       # Hard cap on tool-calling iterations
_MAX_TOOL_CALLS = 12      # Hard cap on total tool invocations per request
_CONTEXT_TOKEN_BUDGET = 1800


# ── Helpers ──────────────────────────────────────────────────────────

def _extract_tool_call(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Normalize a tool call dict from LiteLLM into (name, args)."""
    fn = call.get("function", {}) if isinstance(call, dict) else {}
    name = fn.get("name", "")
    raw_args = fn.get("arguments", "{}")
    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args)
        except Exception:
            args = {}
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        args = {}
    return name, args if isinstance(args, dict) else {}


def _tool_model(model: str) -> tuple[str, bool]:
    """Return (model_to_use, was_rerouted). Reroutes to a tool-capable model if needed."""
    caps = infer_model_capabilities(model)
    if caps.get("supports_tool_calls", False):
        return model, False
    fallback = settings.agent_tool_loop_model
    return fallback, True


async def _build_context(user_message: str, user_id: str) -> str:
    """Assemble memory + document context for the request."""
    try:
        from packages.memory.memory_service import build_context
        ctx = await build_context(user_message, user_id=user_id)
        return clip_text_to_token_budget(ctx or "", _CONTEXT_TOKEN_BUDGET)
    except Exception as exc:
        logger.warning("Context build failed (non-fatal): %s", exc)
        return ""


def _build_messages(
    user_message: str,
    context: str,
    history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build the initial message list for the ReAct loop."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": _REACT_SYSTEM}]

    if context:
        messages.append({
            "role": "system",
            "content": f"## Retrieved Context\n{context}",
        })

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})
    return messages


async def _store_memory(user_message: str, response: str, user_id: str) -> None:
    """Extract and store memories from the completed turn (non-fatal)."""
    try:
        from packages.memory.memory_service import extract_and_store_from_turn
        from packages.memory.consolidation import consolidate_memories, increment_turn, should_consolidate

        await extract_and_store_from_turn(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response},
            ],
            user_id=user_id,
        )
        increment_turn(user_id=user_id)
        if should_consolidate(user_id=user_id):
            import asyncio
            asyncio.create_task(consolidate_memories(user_id=user_id))
    except Exception as exc:
        logger.warning("Post-turn memory extraction failed (non-fatal): %s", exc)


# ── Core ReAct loop ──────────────────────────────────────────────────

async def run_react(
    user_message: str,
    *,
    user_id: str = "default",
    model: str = "local",
    history: list[dict[str, Any]] | None = None,
    run_id: str | None = None,
    store_memory: bool = True,
) -> dict[str, Any]:
    """
    Run the ReAct loop and return the final response.

    Returns a dict with:
      - response: str — the final assistant response
      - model_used: str — resolved model identifier
      - tool_calls_made: int — total tool invocations
      - iterations: int — number of LLM calls
      - run_id: str — trace run ID (empty if not tracing)
    """
    emit = run_id is not None

    # ── 1. Assemble context ──────────────────────────────────────────
    if emit:
        await trace_manager.emit(run_id, TraceEvent(
            agent_name="system", event_type="thinking",
            content="Assembling context from memory...",
        ))

    context = await _build_context(user_message, user_id)
    messages = _build_messages(user_message, context, history)

    # ── 2. Resolve model + tools ─────────────────────────────────────
    resolved_model = settings.resolve_model(model)
    tool_model, rerouted = _tool_model(resolved_model)

    allow_exec = settings.allow_exec_tools
    allow_mutating = settings.agent_allow_mutating_tools
    tool_schemas = build_native_tool_schemas(
        allow_exec_tools=allow_exec,
        allow_mutating_tools=allow_mutating,
    )

    # ── 3. ReAct loop ────────────────────────────────────────────────
    iterations = 0
    total_calls = 0
    seen_signatures: set[str] = set()
    final_response = ""
    stop_reason = "max_iterations"

    for i in range(1, _MAX_ITERATIONS + 1):
        iterations = i

        if emit:
            await trace_manager.emit(run_id, TraceEvent(
                agent_name="agent", event_type="thinking",
                content=f"Iteration {i} — calling {tool_model}",
                metadata={"iteration": i, "model": tool_model},
            ))

        completion = await chat_completion(
            messages,
            model=tool_model,
            temperature=0.3,
            max_tokens=1800,
            tools=tool_schemas if tool_schemas else None,
            tool_choice="auto" if tool_schemas else None,
        )

        # Build assistant message for history
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": completion.content or "",
        }
        if completion.tool_calls:
            assistant_msg["tool_calls"] = completion.tool_calls
        messages.append(assistant_msg)

        # No tool calls → model is done
        if not completion.tool_calls:
            final_response = completion.content or ""
            stop_reason = "model_finished"
            break

        # ── Execute tool calls ───────────────────────────────────────
        for idx, call in enumerate(completion.tool_calls, start=1):
            if total_calls >= _MAX_TOOL_CALLS:
                stop_reason = "max_calls_reached"
                break

            name, args = _extract_tool_call(call)
            sig = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"

            if sig in seen_signatures:
                result = {
                    "name": name, "success": False,
                    "error": "Duplicate call skipped", "payload": None, "preview": "",
                }
            else:
                seen_signatures.add(sig)
                result = await execute_registered_tool(
                    name, args,
                    allow_exec_tools=allow_exec,
                    allow_mutating_tools=allow_mutating,
                    timeout_seconds=settings.agent_tool_call_timeout_seconds,
                )
                total_calls += 1

            if emit:
                await trace_manager.emit(run_id, TraceEvent(
                    agent_name="agent", event_type="tool_result",
                    content=f"{name}: {'ok' if result.get('success') else result.get('error', 'error')}",
                    metadata={"tool": name, "success": result.get("success"), "preview": result.get("preview", "")[:200]},
                ))

            # Append tool result to messages
            tool_call_id = call.get("id") or f"call_{i}_{idx}"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": json.dumps({
                    "success": result.get("success", False),
                    "error": result.get("error"),
                    "result": _truncate_payload(result.get("payload"), settings.agent_tool_input_token_budget),
                }, ensure_ascii=False),
            })

        if stop_reason == "max_calls_reached":
            # Ask model to wrap up with what it has
            messages.append({
                "role": "user",
                "content": "You've reached the tool call limit. Please provide your best answer with the information gathered so far.",
            })
            wrap_up = await chat_completion(messages, model=tool_model, temperature=0.3, max_tokens=1200)
            final_response = wrap_up.content or ""
            break

    # If loop exhausted without a final response, use last content
    if not final_response:
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                final_response = msg["content"]
                break

    # ── 4. Store memory ──────────────────────────────────────────────
    if store_memory and final_response:
        await _store_memory(user_message, final_response, user_id)

    if emit:
        await trace_manager.finish(run_id)

    return {
        "response": final_response,
        "model_used": settings.resolve_model(tool_model),
        "tool_calls_made": total_calls,
        "iterations": iterations,
        "stop_reason": stop_reason,
        "run_id": run_id or "",
        "rerouted": rerouted,
    }


async def run_react_stream(
    user_message: str,
    *,
    user_id: str = "default",
    model: str = "local",
    history: list[dict[str, Any]] | None = None,
    store_memory: bool = True,
) -> AsyncIterator[str]:
    """
    Streaming variant of run_react.

    Runs the tool loop synchronously (tools must complete before streaming),
    then streams the final response token-by-token.

    Yields str chunks. The last chunk is always "[DONE]".
    """
    # ── 1. Context + tool loop (non-streaming) ───────────────────────
    context = await _build_context(user_message, user_id)
    messages = _build_messages(user_message, context, history)

    resolved_model = settings.resolve_model(model)
    tool_model, _ = _tool_model(resolved_model)

    allow_exec = settings.allow_exec_tools
    allow_mutating = settings.agent_allow_mutating_tools
    tool_schemas = build_native_tool_schemas(
        allow_exec_tools=allow_exec,
        allow_mutating_tools=allow_mutating,
    )

    total_calls = 0
    seen_signatures: set[str] = set()

    for i in range(1, _MAX_ITERATIONS + 1):
        completion = await chat_completion(
            messages,
            model=tool_model,
            temperature=0.3,
            max_tokens=1800,
            tools=tool_schemas if tool_schemas else None,
            tool_choice="auto" if tool_schemas else None,
        )

        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": completion.content or "",
        }
        if completion.tool_calls:
            assistant_msg["tool_calls"] = completion.tool_calls
        messages.append(assistant_msg)

        if not completion.tool_calls:
            break

        for idx, call in enumerate(completion.tool_calls, start=1):
            if total_calls >= _MAX_TOOL_CALLS:
                break
            name, args = _extract_tool_call(call)
            sig = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
            if sig in seen_signatures:
                result = {"name": name, "success": False, "error": "Duplicate", "payload": None, "preview": ""}
            else:
                seen_signatures.add(sig)
                result = await execute_registered_tool(
                    name, args,
                    allow_exec_tools=allow_exec,
                    allow_mutating_tools=allow_mutating,
                    timeout_seconds=settings.agent_tool_call_timeout_seconds,
                )
                total_calls += 1

            tool_call_id = call.get("id") or f"call_{i}_{idx}"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": json.dumps({
                    "success": result.get("success", False),
                    "error": result.get("error"),
                    "result": _truncate_payload(result.get("payload"), settings.agent_tool_input_token_budget),
                }, ensure_ascii=False),
            })

    # ── 2. Stream the final response ─────────────────────────────────
    # Remove tool schemas for the final streaming call — we want prose, not more tool calls
    full_response = ""
    try:
        async for chunk in chat_stream(messages, model=tool_model, temperature=0.5, max_tokens=2000):
            full_response += chunk
            yield chunk
    except Exception as exc:
        logger.error("ReAct stream error: %s", exc)
        yield f"\n[Error: {exc}]"

    yield "[DONE]"

    # ── 3. Store memory ──────────────────────────────────────────────
    if store_memory and full_response:
        await _store_memory(user_message, full_response, user_id)


# ── Utility ──────────────────────────────────────────────────────────

def _truncate_payload(payload: Any, token_budget: int) -> Any:
    """Truncate a tool payload to fit within the token budget."""
    if payload is None:
        return None
    if isinstance(payload, str):
        return clip_text_to_token_budget(payload, token_budget)
    try:
        serialized = json.dumps(payload, ensure_ascii=False)
        truncated = clip_text_to_token_budget(serialized, token_budget)
        if truncated == serialized:
            return payload
        return truncated
    except Exception:
        return str(payload)[:token_budget * 4]
