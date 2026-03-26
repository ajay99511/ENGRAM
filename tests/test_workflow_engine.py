import pytest

import packages.workflows.engine as engine_module
from packages.workflows.engine import WorkflowEngine


def _node(node_id: str, node_type: str, label: str, config: dict | None = None) -> dict:
    return {
        "id": node_id,
        "type": node_type,
        "data": {"label": label, "config": config or {}},
    }


@pytest.mark.asyncio
async def test_requires_trigger_node():
    nodes = [_node("agent-1", "agent", "Agent")]
    result = await WorkflowEngine(nodes, []).run()
    assert result["success"] is False
    assert "trigger" in result["error"].lower()


@pytest.mark.asyncio
async def test_missing_node_id_rejected():
    nodes = [{"type": "trigger", "data": {"label": "Start", "config": {}}}]
    result = await WorkflowEngine(nodes, []).run()
    assert result["success"] is False
    assert "without ids" in result["error"].lower()


@pytest.mark.asyncio
async def test_duplicate_node_id_rejected():
    nodes = [
        _node("dup-1", "trigger", "Start"),
        _node("dup-1", "agent", "Agent"),
    ]
    result = await WorkflowEngine(nodes, []).run()
    assert result["success"] is False
    assert "duplicate" in result["error"].lower()


@pytest.mark.asyncio
async def test_cycle_detection():
    nodes = [
        _node("t1", "trigger", "Start"),
        _node("a1", "agent", "Agent"),
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1"},
        {"id": "e2", "source": "a1", "target": "t1"},
    ]
    result = await WorkflowEngine(nodes, edges).run()
    assert result["success"] is False
    assert "cycle" in result["error"].lower()


@pytest.mark.asyncio
async def test_tool_pending_approval_halts(monkeypatch):
    async def fake_run_command(command: str, cwd=None, timeout=30):
        return {
            "status": "pending_approval",
            "success": False,
            "message": "needs approval",
        }

    monkeypatch.setitem(engine_module.TOOL_REGISTRY, "exec_command", {
        **engine_module.TOOL_REGISTRY["exec_command"],
        "fn": fake_run_command,
    })

    nodes = [
        _node("t1", "trigger", "Start"),
        _node(
            "tool-1",
            "tool",
            "Tool",
            {"toolName": "toolExecCommand", "command": "whoami", "timeout": 5},
        ),
    ]
    edges = [{"id": "e1", "source": "t1", "target": "tool-1"}]
    result = await WorkflowEngine(nodes, edges).run()
    assert result["success"] is False
    assert "approval" in result["error"].lower()


@pytest.mark.asyncio
async def test_tool_missing_command_fails():
    nodes = [
        _node("t1", "trigger", "Start"),
        _node("tool-1", "tool", "Tool", {"toolName": "toolExecCommand"}),
    ]
    edges = [{"id": "e1", "source": "t1", "target": "tool-1"}]
    result = await WorkflowEngine(nodes, edges).run()
    assert result["success"] is False
    assert "command" in result["error"].lower()


@pytest.mark.asyncio
async def test_agent_node_executes(monkeypatch):
    async def fake_run_crew(user_message: str, user_id: str = "default", model: str = "local", run_id: str | None = None):
        return {"response": "ok", "plan": "plan", "research": "research"}

    monkeypatch.setattr(engine_module, "run_crew", fake_run_crew)

    nodes = [
        _node("t1", "trigger", "Start"),
        _node("a1", "agent", "Agent", {"prompt": "Do the thing", "model": "local"}),
    ]
    edges = [{"id": "e1", "source": "t1", "target": "a1"}]
    result = await WorkflowEngine(nodes, edges).run()

    assert result["success"] is True
    assert result["trace"]
    last = result["trace"][-1]
    assert last["result"]["status"] == "completed"
    assert last["result"]["response"] == "ok"


@pytest.mark.asyncio
async def test_tool_success(monkeypatch):
    async def fake_run_command(command: str, cwd=None, timeout=30):
        return {"success": True, "stdout": "ok", "stderr": "", "returncode": 0}

    monkeypatch.setitem(engine_module.TOOL_REGISTRY, "exec_command", {
        **engine_module.TOOL_REGISTRY["exec_command"],
        "fn": fake_run_command,
    })

    nodes = [
        _node("t1", "trigger", "Start"),
        _node(
            "tool-1",
            "tool",
            "Tool",
            {"toolName": "toolExecCommand", "command": "whoami", "timeout": 5},
        ),
    ]
    edges = [{"id": "e1", "source": "t1", "target": "tool-1"}]
    result = await WorkflowEngine(nodes, edges).run()
    assert result["success"] is True
    assert result["trace"][-1]["result"]["status"] == "completed"
