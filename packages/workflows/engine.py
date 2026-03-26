"""
Workflow Execution Engine
Parses React Flow graphs and executes nodes in topological order.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from typing import Any

from packages.agents.crew import run_crew
from packages.agents.tools import TOOL_REGISTRY
from packages.shared.config import settings

logger = logging.getLogger(__name__)

VALID_NODE_TYPES = {"trigger", "agent", "tool"}


def _clip_text(text: str, limit: int) -> str:
    text = (text or "").strip()
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


class WorkflowEngine:
    def __init__(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]):
        self.original_node_count = len(nodes)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.duplicate_node_ids: set[str] = set()
        self.missing_node_ids = 0

        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                self.missing_node_ids += 1
                continue
            if node_id in self.nodes:
                self.duplicate_node_ids.add(node_id)
            self.nodes[node_id] = node

        self.edges = edges
        self.adjacency = {node_id: [] for node_id in self.nodes}
        self.in_degree = {node_id: 0 for node_id in self.nodes}

        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src in self.adjacency and tgt in self.in_degree:
                self.adjacency[src].append(tgt)
                self.in_degree[tgt] += 1

    def _validate_graph(self) -> None:
        if self.original_node_count == 0:
            raise ValueError("Workflow must contain at least one node.")

        if self.missing_node_ids:
            raise ValueError("Workflow contains node entries without ids.")

        if self.duplicate_node_ids:
            duplicates = ", ".join(sorted(self.duplicate_node_ids))
            raise ValueError(f"Workflow contains duplicate node ids: {duplicates}.")

        trigger_count = 0
        for node_id, node in self.nodes.items():
            node_type = node.get("type")
            if node_type not in VALID_NODE_TYPES:
                raise ValueError(f"Unsupported node type '{node_type}' for node {node_id}.")
            if node_type == "trigger":
                trigger_count += 1

        if trigger_count == 0:
            raise ValueError("Workflow must contain at least one trigger node.")

        for edge in self.edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src not in self.nodes or tgt not in self.nodes:
                raise ValueError("Workflow contains an edge pointing to a missing node.")

    def _topological_sort(self) -> list[str]:
        in_degree = dict(self.in_degree)
        queue: deque[str] = deque(node_id for node_id, degree in in_degree.items() if degree == 0)
        sorted_nodes: list[str] = []

        while queue:
            current = queue.popleft()
            sorted_nodes.append(current)
            for neighbor in self.adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(self.nodes):
            raise ValueError("Cycle detected in workflow graph. Execution halted.")

        return sorted_nodes

    def _compact_context(self, context: dict[str, Any]) -> str:
        if not context:
            return "No prior workflow context available."
        serialized = json.dumps(context, indent=2, default=str)
        return _clip_text(serialized, settings.workflow_context_char_budget)

    async def _execute_node(self, node: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        node_type = node.get("type")
        label = node.get("data", {}).get("label", "Unknown")
        config = node.get("data", {}).get("config", {})

        logger.info("Executing workflow node [%s] %s", node_type, label)

        if node_type == "trigger":
            return {
                "status": "triggered",
                "label": label,
                "type": node_type,
            }

        if node_type == "agent":
            prompt = (config.get("prompt") or "").strip()
            if not prompt:
                prompt = f"Execute workflow step '{label}' using the available workflow context."

            message = (
                f"Workflow Node: {label}\n\n"
                f"Instruction:\n{prompt}\n\n"
                f"Context:\n{self._compact_context(context)}"
            )
            model = config.get("model", "local")
            result = await run_crew(user_message=message, user_id="default", model=model)
            return {
                "status": "completed",
                "label": label,
                "type": node_type,
                "model": model,
                "response": result.get("response", ""),
                "plan": result.get("plan", ""),
                "research": result.get("research", ""),
            }

        if node_type == "tool":
            tool_name = config.get("toolName", "")

            # Backward compatibility alias
            if tool_name == "toolExecCommand":
                tool_name = "exec_command"

            tool = TOOL_REGISTRY.get(tool_name)
            if not tool:
                return {
                    "status": "error",
                    "label": label,
                    "type": node_type,
                    "error": f"Tool {tool_name or 'unknown'} is not implemented.",
                }

            args = config.get("args", {}) if isinstance(config.get("args", {}), dict) else {}

            # Legacy exec_command config support
            if tool_name == "exec_command":
                command = (config.get("command") or "").strip()
                if not command:
                    return {
                        "status": "error",
                        "label": label,
                        "type": node_type,
                        "error": "Tool node requires a command.",
                    }
                args = {
                    "command": command,
                    "cwd": config.get("cwd"),
                    "timeout": int(config.get("timeout", 30)),
                }

            try:
                result = await tool["fn"](**args)
            except Exception as exc:
                return {
                    "status": "error",
                    "label": label,
                    "type": node_type,
                    "error": str(exc),
                }

            return {
                "status": "completed" if result.get("success", True) else result.get("status", "failed"),
                "label": label,
                "type": node_type,
                "tool": tool_name,
                "output": result,
            }

        return {
            "status": "skipped",
            "label": label,
            "type": node_type,
        }

    async def run(self) -> dict[str, Any]:
        try:
            self._validate_graph()
            order = self._topological_sort()
            logger.info("Workflow execution order: %s", order)
        except Exception as exc:
            return {"success": False, "error": str(exc), "trace": []}

        global_context: dict[str, Any] = {}
        execution_trace: list[dict[str, Any]] = []

        for node_id in order:
            node = self.nodes[node_id]
            label = node.get("data", {}).get("label", node_id)
            node_type = node.get("type", "unknown")

            try:
                result = await self._execute_node(node, global_context)
                execution_trace.append(
                    {
                        "node_id": node_id,
                        "label": label,
                        "type": node_type,
                        "result": result,
                    }
                )
                global_context[node_id] = result

                output = result.get("output") if isinstance(result, dict) else None
                if isinstance(output, dict) and output.get("blocked"):
                    return {
                        "success": False,
                        "trace": execution_trace,
                        "error": output.get("error", "Workflow command was blocked."),
                    }
                if isinstance(output, dict) and output.get("status") == "pending_approval":
                    return {
                        "success": False,
                        "trace": execution_trace,
                        "error": output.get("message", "Workflow command requires manual approval."),
                    }
                if isinstance(result, dict) and result.get("status") == "error":
                    return {
                        "success": False,
                        "trace": execution_trace,
                        "error": result.get("error", f"Workflow node {label} failed."),
                    }
            except Exception as exc:
                logger.error("Workflow node %s failed: %s", node_id, exc)
                execution_trace.append(
                    {
                        "node_id": node_id,
                        "label": label,
                        "type": node_type,
                        "error": str(exc),
                    }
                )
                return {"success": False, "trace": execution_trace, "error": str(exc)}

        return {"success": True, "trace": execution_trace}
