import pytest

import packages.agents.crew as crew_module
from packages.model_gateway.client import ChatCompletionResult


@pytest.mark.asyncio
async def test_run_crew_native_tool_loop(monkeypatch):
    monkeypatch.setattr(crew_module.settings, "enable_agent_tool_calls", True)
    monkeypatch.setattr(crew_module.settings, "agent_native_tool_calling_enabled", True)
    monkeypatch.setattr(crew_module.settings, "agent_legacy_tool_planner_fallback", True)
    monkeypatch.setattr(crew_module.settings, "allow_exec_tools", False)
    monkeypatch.setattr(crew_module.settings, "agent_allow_mutating_tools", False)
    monkeypatch.setattr(crew_module.settings, "agent_tool_loop_max_iterations", 3)
    monkeypatch.setattr(crew_module.settings, "agent_tool_loop_max_calls", 3)

    async def fake_build_context(*args, **kwargs):
        return "ctx"

    async def fake_search(*args, **kwargs):
        return []

    async def fake_format(*args, **kwargs):
        return "tool-context"

    async def fake_chat(messages, **kwargs):
        return "stub-response"

    state = {"calls": 0}

    async def fake_chat_completion(messages, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            return ChatCompletionResult(
                content="",
                tool_calls=[
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "search_documents", "arguments": '{"query":"test"}'},
                    }
                ],
            )
        return ChatCompletionResult(content="done", tool_calls=[])

    async def fake_execute_registered_tool(name, args, **kwargs):
        return {
            "name": name,
            "success": True,
            "error": None,
            "payload": {"items": [1]},
            "preview": "ok",
        }

    async def fake_extract(*args, **kwargs):
        return {"extracted": 0}

    monkeypatch.setattr(crew_module, "build_context", fake_build_context)
    monkeypatch.setattr(crew_module, "chat", fake_chat)
    monkeypatch.setattr(crew_module, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(crew_module, "execute_registered_tool", fake_execute_registered_tool)
    monkeypatch.setattr(crew_module, "search_user_memories", fake_search)
    monkeypatch.setattr(crew_module, "search_documents", fake_search)
    monkeypatch.setattr(crew_module, "format_tool_results", fake_format)
    monkeypatch.setattr(crew_module, "extract_and_store_from_turn", fake_extract)

    result = await crew_module.run_crew("hello", model="gemini")
    assert result["tool_loop"]["mode"] == "native"
    assert result["tool_loop"]["iterations"] >= 1


@pytest.mark.asyncio
async def test_run_crew_falls_back_to_legacy(monkeypatch):
    monkeypatch.setattr(crew_module.settings, "enable_agent_tool_calls", True)
    monkeypatch.setattr(crew_module.settings, "agent_native_tool_calling_enabled", True)
    monkeypatch.setattr(crew_module.settings, "agent_legacy_tool_planner_fallback", True)

    async def fake_build_context(*args, **kwargs):
        return "ctx"

    async def fake_search(*args, **kwargs):
        return []

    async def fake_format(*args, **kwargs):
        return "tool-context"

    async def fake_chat(messages, **kwargs):
        return "stub-response"

    async def fake_native_loop(**kwargs):
        raise RuntimeError("native failed")

    async def fake_legacy_plan(**kwargs):
        return [{"name": "search_documents", "args": {"query": "x"}}]

    async def fake_legacy_exec(calls):
        return [{"name": "search_documents", "success": True, "preview": "ok", "payload": {}}]

    async def fake_extract(*args, **kwargs):
        return {"extracted": 0}

    monkeypatch.setattr(crew_module, "build_context", fake_build_context)
    monkeypatch.setattr(crew_module, "chat", fake_chat)
    monkeypatch.setattr(crew_module, "_run_native_tool_loop", fake_native_loop)
    monkeypatch.setattr(crew_module, "_legacy_plan_tool_calls", fake_legacy_plan)
    monkeypatch.setattr(crew_module, "_legacy_execute_tool_calls", fake_legacy_exec)
    monkeypatch.setattr(crew_module, "search_user_memories", fake_search)
    monkeypatch.setattr(crew_module, "search_documents", fake_search)
    monkeypatch.setattr(crew_module, "format_tool_results", fake_format)
    monkeypatch.setattr(crew_module, "extract_and_store_from_turn", fake_extract)

    result = await crew_module.run_crew("hello", model="gemini")
    assert result["tool_loop"]["mode"] == "legacy"
