"""
A2A (Agent-to-Agent) Registry

Service registry for Tier 1 agents with capability discovery and delegation.
Supports Agent Cards for capability advertisement and async task lifecycle.

Usage:
    from packages.agents.a2a.registry import A2ARegistry, AgentCard
    
    # Register an agent
    registry.register(AgentCard(
        agent_id="code-reviewer",
        name="Code Review Agent",
        capabilities=["code_review", "security_scan"],
        ...
    ))
    
    # Discover agents
    agents = registry.discover("code_review")
    
    # Delegate task
    task_handle = await registry.delegate(
        agent_id="code-reviewer",
        task={"path": "src/", "focus": "security"},
    )
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCard(BaseModel):
    """
    Capability advertisement for a Tier 1 agent.
    """
    
    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Human-readable agent name")
    description: str = Field(..., description="Agent description")
    capabilities: list[str] = Field(..., description="List of capabilities")
    input_schema: dict[str, Any] = Field(..., description="JSON schema for input")
    output_schema: dict[str, Any] = Field(..., description="JSON schema for output")
    permissions: dict[str, list[str]] = Field(
        default_factory=lambda: {"read": [], "write": [], "execute": []},
        description="Required permissions",
    )
    version: str = Field(default="1.0.0", description="Agent version")
    enabled: bool = Field(default=True, description="Whether agent is enabled")


class TaskHandle(BaseModel):
    """Handle for tracking an async task."""
    
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    status: TaskStatus = TaskStatus.QUEUED
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"arbitrary_types_allowed": True}


class A2ARegistry:
    """
    Service registry for Tier 1 agents.
    """
    
    _instance: 'A2ARegistry | None' = None
    
    def __new__(cls) -> 'A2ARegistry':
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.agents = {}
            cls._instance.task_handlers = {}
            cls._instance.task_results = {}
        return cls._instance
    
    def __init__(self):
        """Initialize registry."""
        if not hasattr(self, 'agents'):
            self.agents: dict[str, AgentCard] = {}
            self.task_handlers: dict[str, Callable] = {}
            self.task_results: dict[str, TaskHandle] = {}
    
    def register(
        self,
        card: AgentCard,
        handler: Callable | None = None,
    ) -> None:
        """
        Register an agent with the registry.
        
        Args:
            card: Agent card with capabilities
            handler: Optional async handler function
        """
        self.agents[card.agent_id] = card
        
        if handler:
            self.task_handlers[card.agent_id] = handler
        
        logger.info(f"Registered agent: {card.agent_id} ({card.name})")
    
    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if unregistered, False if not found
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            if agent_id in self.task_handlers:
                del self.task_handlers[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False
    
    def discover(self, capability: str) -> list[AgentCard]:
        """
        Find agents that provide a specific capability.
        
        Args:
            capability: Capability to search for
        
        Returns:
            List of matching agent cards
        """
        matches = []
        for card in self.agents.values():
            if card.enabled and capability in card.capabilities:
                matches.append(card)
        
        logger.debug(f"Discovered {len(matches)} agents for capability: {capability}")
        return matches
    
    def get_agent(self, agent_id: str) -> AgentCard | None:
        """
        Get agent card by ID.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Agent card or None
        """
        return self.agents.get(agent_id)
    
    async def delegate(
        self,
        agent_id: str,
        task: dict[str, Any],
        **kwargs: Any,
    ) -> TaskHandle:
        """
        Delegate a task to an agent.
        
        Args:
            agent_id: Target agent identifier
            task: Task parameters
            **kwargs: Additional arguments
        
        Returns:
            Task handle for tracking
        """
        # Check if agent exists
        if agent_id not in self.agents:
            raise ValueError(f"Agent not found: {agent_id}")
        
        card = self.agents[agent_id]
        if not card.enabled:
            raise ValueError(f"Agent is disabled: {agent_id}")
        
        # Create task handle
        task_handle = TaskHandle(agent_id=agent_id)
        self.task_results[task_handle.task_id] = task_handle
        
        # Check if handler exists
        if agent_id not in self.task_handlers:
            task_handle.status = TaskStatus.FAILED
            task_handle.error = "No handler registered for agent"
            task_handle.completed_at = datetime.now().isoformat()
            return task_handle
        
        # Queue task for execution
        handler = self.task_handlers[agent_id]
        
        # Start task in background
        asyncio.create_task(
            self._execute_task(task_handle, handler, task, **kwargs)
        )
        
        logger.info(f"Delegated task {task_handle.task_id} to {agent_id}")
        return task_handle
    
    async def _execute_task(
        self,
        task_handle: TaskHandle,
        handler: Callable,
        task: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """
        Execute a delegated task.
        
        Args:
            task_handle: Task handle to update
            handler: Async handler function
            task: Task parameters
            **kwargs: Additional arguments
        """
        try:
            # Update status to running
            task_handle.status = TaskStatus.RUNNING
            task_handle.started_at = datetime.now().isoformat()
            
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task, **kwargs)
            else:
                result = handler(task, **kwargs)
            
            # Update status to completed
            task_handle.status = TaskStatus.COMPLETED
            task_handle.result = result
            task_handle.completed_at = datetime.now().isoformat()
            
            logger.info(f"Task {task_handle.task_id} completed")
        
        except Exception as exc:
            # Update status to failed
            task_handle.status = TaskStatus.FAILED
            task_handle.error = str(exc)
            task_handle.completed_at = datetime.now().isoformat()
            
            logger.error(f"Task {task_handle.task_id} failed: {exc}")
    
    async def get_task_status(self, task_id: str) -> TaskHandle | None:
        """
        Get status of a task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Task handle with current status or None
        """
        return self.task_results.get(task_id)
    
    async def wait_for_task(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> TaskHandle:
        """
        Wait for a task to complete.
        
        Args:
            task_id: Task identifier
            timeout: Optional timeout in seconds
        
        Returns:
            Task handle with final status
        """
        task_handle = self.task_results.get(task_id)
        if not task_handle:
            raise ValueError(f"Task not found: {task_id}")
        
        start_time = datetime.now()
        
        while task_handle.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    task_handle.status = TaskStatus.CANCELLED
                    task_handle.error = "Task timed out"
                    task_handle.completed_at = datetime.now().isoformat()
                    return task_handle
            
            await asyncio.sleep(0.1)
            task_handle = self.task_results.get(task_id)
            if not task_handle:
                break
        
        return task_handle
    
    def list_agents(self) -> list[AgentCard]:
        """
        List all registered agents.
        
        Returns:
            List of agent cards
        """
        return list(self.agents.values())
    
    def list_capabilities(self) -> list[str]:
        """
        List all available capabilities.
        
        Returns:
            List of unique capabilities
        """
        capabilities = set()
        for card in self.agents.values():
            if card.enabled:
                capabilities.update(card.capabilities)
        return sorted(list(capabilities))


# Global registry instance
_registry: A2ARegistry | None = None


def get_registry() -> A2ARegistry:
    """Get or create the global A2A registry."""
    global _registry
    if _registry is None:
        _registry = A2ARegistry()
    return _registry


def register_agent(
    agent_id: str,
    name: str,
    description: str,
    capabilities: list[str],
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    permissions: dict[str, list[str]] | None = None,
    handler: Callable | None = None,
) -> None:
    """
    Convenience function to register an agent.
    
    Args:
        agent_id: Unique agent identifier
        name: Human-readable name
        description: Agent description
        capabilities: List of capabilities
        input_schema: JSON schema for input
        output_schema: JSON schema for output
        permissions: Required permissions
        handler: Optional async handler function
    """
    card = AgentCard(
        agent_id=agent_id,
        name=name,
        description=description,
        capabilities=capabilities,
        input_schema=input_schema,
        output_schema=output_schema,
        permissions=permissions or {"read": [], "write": [], "execute": []},
    )
    
    registry = get_registry()
    registry.register(card, handler)


def discover_agents(capability: str) -> list[AgentCard]:
    """
    Convenience function to discover agents.
    
    Args:
        capability: Capability to search for
    
    Returns:
        List of matching agent cards
    """
    return get_registry().discover(capability)


async def delegate_task(
    agent_id: str,
    task: dict[str, Any],
    **kwargs: Any,
) -> TaskHandle:
    """
    Convenience function to delegate a task.
    
    Args:
        agent_id: Target agent identifier
        task: Task parameters
        **kwargs: Additional arguments
    
    Returns:
        Task handle for tracking
    """
    return await get_registry().delegate(agent_id, task, **kwargs)
