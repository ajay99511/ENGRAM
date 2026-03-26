"""
Agent Crew - lightweight Planner -> Researcher -> Synthesizer pipeline.

This module supports two tool-planning modes:
  - Legacy regex JSON planner (feature-flag fallback)
  - Native model tool/function-calling with iterative ReAct loop
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from packages.agents.tools import (
    build_native_tool_schemas,
    execute_registered_tool,
    format_tool_results,
    get_allowed_tools,
    search_documents,
    search_user_memories,
)
from packages.agents.trace import TraceEvent, trace_manager
from packages.memory.memory_service import build_context, extract_and_store_from_turn
from packages.model_gateway.client import chat, chat_completion, try_parse_json
from packages.model_gateway.registry import infer_model_capabilities
from packages.shared.config import settings
from packages.shared.text_budget import clip_text_to_token_budget, to_compact_json_preview

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are the Planner agent (Architect role) in a multi-agent system.
Your job is to analyze the user's request and create a clear, actionable plan.

Given the user's message and any available context, produce:
1. A brief analysis of what the user needs
2. 2-5 numbered steps to address it
3. What information the Researcher should look for
4. Any special considerations (user preferences, project context)

Be concise and specific. Output your plan in plain text, NOT JSON."""

RESEARCHER_SYSTEM = """You are the Researcher agent (Librarian role) in a multi-agent system.
Your job is to gather and organize information based on the Planner's instructions.

You have been given:
- The original user request
- The Planner's research plan
- Context from memory and documents (if available)

Produce structured research notes:
1. Key facts and findings relevant to each plan step
2. Specific details from any provided context
3. Any gaps or uncertainties
4. Recommendations based on your findings

Be thorough but concise. Focus on actionable information."""

SYNTHESIZER_SYSTEM = """You are the Synthesizer agent (Writer role) in a multi-agent system.
Your job is to produce the final, polished response for the user.

You have been given:
- The original user request
- The Planner's plan
- The Researcher's findings
- User preferences and context

Produce a clear, well-structured response that:
1. Directly answers the user's question
2. Incorporates relevant research findings
3. Respects the user's known preferences and style
4. Is actionable and practical
5. If you rely on documents or tool outputs, cite the source path or tool name in brackets.

Write naturally and helpfully - this is what the user will see."""

TOOL_REACT_SYSTEM = """You are a tool-using investigator.

Rules:
1. Use tools only when they materially improve answer quality.
2. Prefer read-only tools first.
3. Keep total tool calls low and avoid repeating identical calls.
4. If enough information is gathered, stop calling tools and provide a short summary.
"""

TOOL_PLANNER_SYSTEM = """You are a tool planning agent. Your job is to decide which tools to call.

You must output ONLY valid JSON in this exact format:
{
  "tool_calls": [
    {"name": "tool_name", "args": {"arg1": "value", "arg2": 123}}
  ]
}

Rules:
1. Use only the tools in the provided tool list.
2. Prefer read-only tools (filesystem, git, memory/document searches).
3. If no tools are needed, return {"tool_calls": []}.
4. Keep the number of tool calls small (max 3).
5. Do NOT include commentary or markdown.
"""

PLANNER_MAX_TOKENS = 450
RESEARCHER_MAX_TOKENS = 700
SYNTHESIZER_MAX_TOKENS = 1200
TRACE_PREVIEW_CHARS = 500
MAX_TOOL_CALLS = 3


def _clip_text(text: str, char_limit: int) -> str:
    """
    Backward-compatible clipping helper backed by token-aware clipping.
    """
    approx_token_limit = max(1, char_limit // 4)
    return clip_text_to_token_budget(text, approx_token_limit)


def _extract_json_legacy(text: str) -> str:
    """Extract JSON object from a model response."""
    text = (text or "").strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        return text[brace_start : brace_end + 1]
    return text


def _build_tool_loop_prompt(user_message: str, plan: str, context: str) -> str:
    user_budget = settings.agent_tool_input_token_budget
    return (
        f"## User Request\n{clip_text_to_token_budget(user_message, user_budget)}\n\n"
        f"## Plan\n{clip_text_to_token_budget(plan, user_budget)}\n\n"
        f"## Context\n{clip_text_to_token_budget(context, user_budget)}\n\n"
        "Decide whether tools are needed. If yes, call tools. If not, provide a short completion note."
    )


def _tool_model_for_request(model: str) -> tuple[str, bool]:
    """
    Return (model_to_use_for_tool_loop, was_routed).
    """
    capabilities = infer_model_capabilities(model)
    if capabilities.get("supports_tool_calls", False):
        return model, False
    return settings.agent_tool_loop_model, True


def _extract_legacy_tool_call(call: dict[str, Any]) -> tuple[str, Any]:
    name = call.get("name", "")
    args = call.get("args", {}) if isinstance(call, dict) else {}
    return name, args


def _extract_native_tool_call(call: dict[str, Any]) -> tuple[str, Any]:
    fn = call.get("function", {}) if isinstance(call, dict) else {}
    name = fn.get("name", "")
    raw_args = fn.get("arguments", "{}")
    if isinstance(raw_args, str):
        parsed = try_parse_json(raw_args)
        args = parsed if isinstance(parsed, dict) else {}
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        args = {}
    return name, args


async def _legacy_plan_tool_calls(
    user_message: str,
    plan: str,
    context: str,
    model: str,
) -> list[dict[str, Any]]:
    """Legacy regex-based planner."""
    allow_exec = settings.allow_exec_tools
    allow_mutating = settings.agent_allow_mutating_tools
    tools = get_allowed_tools(
        allow_exec_tools=allow_exec,
        allow_mutating_tools=allow_mutating,
    )
    if not tools:
        return []

    tool_list = "\n".join(
        f"- {name}: {info.get('description', '')}" for name, info in tools.items()
    )

    messages = [
        {"role": "system", "content": TOOL_PLANNER_SYSTEM},
        {
            "role": "user",
            "content": (
                f"## Tool List\n{tool_list}\n\n"
                f"## User Request\n{_clip_text(user_message, 1200)}\n\n"
                f"## Plan\n{_clip_text(plan, 1200)}\n\n"
                f"## Context\n{_clip_text(context, 1200)}"
            ),
        },
    ]

    raw = await chat(messages, model=model, temperature=0.0, max_tokens=400)
    try:
        parsed = json.loads(_extract_json_legacy(raw))
        tool_calls = parsed.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            return []
        return tool_calls[:MAX_TOOL_CALLS]
    except Exception:
        return []


async def _legacy_execute_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute legacy planner output calls."""
    results: list[dict[str, Any]] = []
    for call in tool_calls[:MAX_TOOL_CALLS]:
        name, args = _extract_legacy_tool_call(call)
        tool_result = await execute_registered_tool(
            name,
            args,
            allow_exec_tools=settings.allow_exec_tools,
            allow_mutating_tools=settings.agent_allow_mutating_tools,
            timeout_seconds=settings.agent_tool_call_timeout_seconds,
        )
        tool_result["args"] = args if isinstance(args, dict) else {}
        results.append(tool_result)
    return results


async def _run_native_tool_loop(
    *,
    user_message: str,
    plan: str,
    context: str,
    model: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Native iterative tool-calling ReAct loop.
    """
    allow_exec = settings.allow_exec_tools
    allow_mutating = settings.agent_allow_mutating_tools
    tool_schemas = build_native_tool_schemas(
        allow_exec_tools=allow_exec,
        allow_mutating_tools=allow_mutating,
    )
    if not tool_schemas:
        return {
            "tool_results": [],
            "iterations": 0,
            "stop_reason": "no_tools_available",
            "tool_model": model,
            "routed": False,
        }

    tool_model, routed = _tool_model_for_request(model)
    max_iterations = max(1, settings.agent_tool_loop_max_iterations)
    max_total_calls = max(1, settings.agent_tool_loop_max_calls)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": TOOL_REACT_SYSTEM},
        {"role": "user", "content": _build_tool_loop_prompt(user_message, plan, context)},
    ]

    all_results: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()
    total_calls = 0
    stop_reason = "max_iterations_reached"
    iterations = 0

    for i in range(1, max_iterations + 1):
        iterations = i
        completion = await chat_completion(
            messages,
            model=tool_model,
            temperature=0.0,
            max_tokens=400,
            tools=tool_schemas,
            tool_choice="auto",
        )

        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": completion.content or "",
        }
        if completion.reasoning_content:
            assistant_msg["reasoning_content"] = completion.reasoning_content
        if completion.tool_calls:
            assistant_msg["tool_calls"] = completion.tool_calls
        messages.append(assistant_msg)

        if run_id:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="system",
                    event_type="thinking",
                    content=f"Tool loop iteration {i} using model {tool_model}",
                    metadata={
                        "iteration": i,
                        "tool_model": tool_model,
                        "tool_calls": len(completion.tool_calls),
                        "routed": routed,
                    },
                ),
            )

        if not completion.tool_calls:
            stop_reason = "model_finished"
            break

        for idx, call in enumerate(completion.tool_calls, start=1):
            if total_calls >= max_total_calls:
                stop_reason = "max_total_calls_reached"
                break

            name, args = _extract_native_tool_call(call)
            signature = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
            if signature in seen_signatures:
                result = {
                    "name": name,
                    "success": False,
                    "error": "Duplicate tool call skipped",
                    "payload": None,
                    "preview": "",
                    "iteration": i,
                    "args": args,
                }
            else:
                seen_signatures.add(signature)
                result = await execute_registered_tool(
                    name,
                    args,
                    allow_exec_tools=allow_exec,
                    allow_mutating_tools=allow_mutating,
                    timeout_seconds=settings.agent_tool_call_timeout_seconds,
                )
                result["iteration"] = i
                result["args"] = args if isinstance(args, dict) else {}
                total_calls += 1

            all_results.append(result)

            tool_call_id = call.get("id") or f"call_{i}_{idx}"
            tool_payload = {
                "success": result.get("success", False),
                "error": result.get("error"),
                "payload_preview": to_compact_json_preview(
                    result.get("payload"),
                    settings.agent_tool_input_token_budget,
                ),
            }
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": name,
                    "content": json.dumps(tool_payload, ensure_ascii=False),
                }
            )

        if stop_reason == "max_total_calls_reached":
            break

    return {
        "tool_results": all_results,
        "iterations": iterations,
        "stop_reason": stop_reason,
        "tool_model": settings.resolve_model(tool_model),
        "routed": routed,
    }


async def run_crew(
    user_message: str,
    user_id: str = "default",
    model: str = "local",
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute the full Planner -> Researcher -> Synthesizer pipeline.
    """
    emit_traces = run_id is not None

    try:
        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="system",
                    event_type="thinking",
                    content="Gathering context from memory and documents...",
                ),
            )

        context = ""
        try:
            context = _clip_text(
                await build_context(user_message, user_id=user_id),
                settings.agent_context_char_budget,
            )
        except Exception as exc:
            logger.warning("Context build failed: %s", exc)

        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="planner",
                    event_type="thinking",
                    content="Analyzing request and creating execution plan...",
                ),
            )

        planner_messages = [{"role": "system", "content": PLANNER_SYSTEM}]
        if context:
            planner_messages.append(
                {
                    "role": "system",
                    "content": f"Available context:\n{clip_text_to_token_budget(context, settings.agent_planner_input_token_budget)}",
                }
            )
        planner_messages.append({"role": "user", "content": user_message})

        plan = await chat(
            planner_messages,
            model=model,
            temperature=0.2,
            max_tokens=PLANNER_MAX_TOKENS,
        )
        plan = clip_text_to_token_budget(plan, settings.agent_planner_input_token_budget)

        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="planner",
                    event_type="output",
                    content=plan[:TRACE_PREVIEW_CHARS],
                ),
            )

        tool_results: list[dict[str, Any]] = []
        tool_loop_meta: dict[str, Any] = {}

        if settings.enable_agent_tool_calls:
            if emit_traces:
                await trace_manager.emit(
                    run_id,
                    TraceEvent(
                        agent_name="system",
                        event_type="thinking",
                        content="Planning tool usage...",
                    ),
                )

            native_enabled = settings.agent_native_tool_calling_enabled
            native_failed = False

            if native_enabled:
                try:
                    loop_result = await _run_native_tool_loop(
                        user_message=user_message,
                        plan=plan,
                        context=context,
                        model=model,
                        run_id=run_id,
                    )
                    tool_results = loop_result.get("tool_results", [])
                    tool_loop_meta = {
                        "mode": "native",
                        "iterations": loop_result.get("iterations", 0),
                        "stop_reason": loop_result.get("stop_reason", ""),
                        "tool_model": loop_result.get("tool_model", settings.resolve_model(model)),
                        "routed": loop_result.get("routed", False),
                    }
                except Exception as exc:
                    native_failed = True
                    logger.warning("Native tool loop failed: %s", exc)
                    if emit_traces:
                        await trace_manager.emit(
                            run_id,
                            TraceEvent(
                                agent_name="system",
                                event_type="error",
                                content=f"Native tool loop failed: {exc}",
                            ),
                        )

            if (not native_enabled) or (native_failed and settings.agent_legacy_tool_planner_fallback):
                tool_calls = await _legacy_plan_tool_calls(
                    user_message=user_message,
                    plan=plan,
                    context=context,
                    model=model,
                )
                tool_results = await _legacy_execute_tool_calls(tool_calls)
                tool_loop_meta = {
                    "mode": "legacy",
                    "iterations": 1 if tool_calls else 0,
                    "stop_reason": "legacy_completed",
                    "tool_model": settings.resolve_model(model),
                    "routed": False,
                }

            if emit_traces:
                await trace_manager.emit(
                    run_id,
                    TraceEvent(
                        agent_name="system",
                        event_type="tool_result",
                        content=f"Tool usage completed with {len(tool_results)} result(s)",
                        metadata={
                            "tool_results": tool_results[:5],
                            "tool_loop": tool_loop_meta,
                        },
                    ),
                )

        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="researcher",
                    event_type="thinking",
                    content="Searching memories and documents...",
                ),
            )

        memories = await search_user_memories(user_message, user_id=user_id)
        documents = await search_documents(user_message)
        tool_context = _clip_text(
            await format_tool_results(memories, documents, tool_results),
            settings.agent_context_char_budget,
        )

        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="researcher",
                    event_type="tool_result",
                    content=f"Found {len(memories)} memories, {len(documents)} documents",
                    metadata={
                        "memory_count": len(memories),
                        "doc_count": len(documents),
                        "tool_loop": tool_loop_meta,
                    },
                ),
            )

        researcher_messages = [
            {"role": "system", "content": RESEARCHER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"## Original Request\n{clip_text_to_token_budget(user_message, settings.agent_researcher_input_token_budget)}\n\n"
                    f"## Plan\n{clip_text_to_token_budget(plan, settings.agent_researcher_input_token_budget)}\n\n"
                    f"## Available Context\n{tool_context or 'No additional context found.'}"
                ),
            },
        ]

        research = await chat(
            researcher_messages,
            model=model,
            temperature=0.2,
            max_tokens=RESEARCHER_MAX_TOKENS,
        )
        research = clip_text_to_token_budget(research, settings.agent_researcher_input_token_budget)

        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="researcher",
                    event_type="output",
                    content=research[:TRACE_PREVIEW_CHARS],
                ),
            )

        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="synthesizer",
                    event_type="thinking",
                    content="Producing final response...",
                ),
            )

        synthesizer_messages = [
            {"role": "system", "content": SYNTHESIZER_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"## Original Request\n{clip_text_to_token_budget(user_message, settings.agent_synthesizer_input_token_budget)}\n\n"
                    f"## Plan\n{clip_text_to_token_budget(plan, settings.agent_synthesizer_input_token_budget)}\n\n"
                    f"## Research Findings\n{clip_text_to_token_budget(research, settings.agent_synthesizer_input_token_budget)}\n\n"
                    f"## User Context\n{context or 'No user context available.'}"
                ),
            },
        ]

        final_response = await chat(
            synthesizer_messages,
            model=model,
            temperature=0.5,
            max_tokens=SYNTHESIZER_MAX_TOKENS,
        )

        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="synthesizer",
                    event_type="output",
                    content=final_response[:TRACE_PREVIEW_CHARS],
                ),
            )

        try:
            turn_messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": final_response},
            ]
            await extract_and_store_from_turn(turn_messages, user_id=user_id)
        except Exception as exc:
            logger.warning("Post-crew memory extraction failed: %s", exc)

        return {
            "response": final_response,
            "plan": plan,
            "research": research,
            "model_used": model,
            "run_id": run_id or "",
            "tool_loop": tool_loop_meta,
        }

    except Exception as exc:
        if emit_traces:
            await trace_manager.emit(
                run_id,
                TraceEvent(
                    agent_name="system",
                    event_type="error",
                    content=str(exc),
                ),
            )
        raise
    finally:
        if emit_traces:
            await trace_manager.finish(run_id)
