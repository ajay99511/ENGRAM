"""
A2A (Agent-to-Agent) Package

Provides agent-to-agent communication infrastructure for Tier 1 agents.

Components:
- registry: A2A service registry with capability discovery
- agents: Pre-defined Tier 1 agent cards

Usage:
    from packages.agents.a2a import register_tier1_agents, get_registry
    
    # Register all Tier 1 agents
    register_tier1_agents()
    
    # Get registry
    registry = get_registry()
    
    # Discover agents
    agents = registry.discover("code_review")
    
    # Delegate task
    task = await registry.delegate("code-reviewer", {"path": "src/"})
"""

from packages.agents.a2a.registry import (
    A2ARegistry,
    AgentCard,
    TaskHandle,
    TaskStatus,
    get_registry,
    register_agent,
    discover_agents,
    delegate_task,
)

from packages.agents.a2a.agents import (
    register_tier1_agents,
    get_tier1_agent_ids,
    CODE_REVIEWER_CARD,
    WORKSPACE_ANALYZER_CARD,
    TEST_GENERATOR_CARD,
    DEPENDENCY_AUDITOR_CARD,
)

__all__ = [
    # Registry
    "A2ARegistry",
    "AgentCard",
    "TaskHandle",
    "TaskStatus",
    "get_registry",
    "register_agent",
    "discover_agents",
    "delegate_task",
    
    # Agents
    "register_tier1_agents",
    "get_tier1_agent_ids",
    "CODE_REVIEWER_CARD",
    "WORKSPACE_ANALYZER_CARD",
    "TEST_GENERATOR_CARD",
    "DEPENDENCY_AUDITOR_CARD",
]
