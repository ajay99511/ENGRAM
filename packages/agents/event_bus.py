"""
Autonomous Agent Event Bus

Provides pub/sub event system for autonomous agent events.
Features:
- Event publishing with persistence
- Event subscriptions with filtering
- SSE stream support for real-time updates
- Event history with pagination

Event Types:
- watch_change: Repository changes detected
- research_complete: Research task completed
- gap_found: Gap analysis found issues
- error: Error occurred during autonomous operation

Usage:
    from packages.agents.event_bus import EventBus, get_event_bus
    
    # Get event bus instance
    bus = get_event_bus()
    
    # Publish event
    await bus.publish("watch_change", {
        "repo_path": "/path/to/repo",
        "files_changed": 5,
        "risk_level": "medium"
    })
    
    # Subscribe to events
    async for event in bus.subscribe(event_types=["watch_change", "gap_found"]):
        print(f"Event received: {event}")
    
    # Get event history
    events = await bus.get_history(limit=50, event_type="research_complete")
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Event type constants
EVENT_WATCH_CHANGE = "watch_change"
EVENT_RESEARCH_COMPLETE = "research_complete"
EVENT_GAP_FOUND = "gap_found"
EVENT_ERROR = "error"

# Default settings
DEFAULT_HISTORY_LIMIT = 100
DEFAULT_HISTORY_TTL = timedelta(hours=24)
MAX_SUBSCRIBERS_PER_QUEUE = 100


class Event:
    """
    Autonomous agent event.
    
    Attributes:
        id: Unique event identifier
        type: Event type (watch_change, research_complete, etc.)
        data: Event payload data
        timestamp: When event was created
        source: Event source (watch_mode, research, gap_analysis)
        workspace_id: Workspace identifier
    """
    
    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "autonomous",
        workspace_id: str = "default",
    ):
        """
        Create a new event.
        
        Args:
            event_type: Type of event
            data: Event payload
            source: Event source
            workspace_id: Workspace identifier
        """
        import uuid
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now().isoformat()
        self.source = source
        self.workspace_id = workspace_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "workspace_id": self.workspace_id,
        }
    
    def to_sse_data(self) -> str:
        """Convert event to SSE data format."""
        return f"data: {json.dumps(self.to_dict())}\n\n"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        event = cls(
            event_type=data["type"],
            data=data["data"],
            source=data.get("source", "autonomous"),
            workspace_id=data.get("workspace_id", "default"),
        )
        event.id = data["id"]
        event.timestamp = data["timestamp"]
        return event
    
    def __repr__(self) -> str:
        return f"Event(id={self.id}, type={self.type}, timestamp={self.timestamp})"


class EventBus:
    """
    Event bus for autonomous agent events.
    
    Provides:
    - Event publishing with persistence
    - Event subscriptions with filtering
    - SSE stream support
    - Event history
    
    Usage:
        bus = EventBus()
        await bus.publish("watch_change", {"repo": "/path"})
        async for event in bus.subscribe(["watch_change"]):
            print(event)
    """
    
    def __init__(self, workspace_id: str = "default"):
        """
        Initialize event bus.
        
        Args:
            workspace_id: Workspace identifier
        """
        self.workspace_id = workspace_id
        
        # Event queues (type -> list of events)
        self._queues: Dict[str, List[Event]] = defaultdict(list)
        
        # Subscribers (queue_id -> list of asyncio.Queue)
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        
        # Event history
        self._history: List[Event] = []
        
        # History settings
        self.history_limit = DEFAULT_HISTORY_LIMIT
        self.history_ttl = DEFAULT_HISTORY_TTL
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        logger.info(f"EventBus initialized for workspace: {workspace_id}")
    
    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "autonomous",
    ) -> Event:
        """
        Publish an event.
        
        Args:
            event_type: Type of event
            data: Event payload
            source: Event source
            
        Returns:
            Published event
            
        Example:
            await bus.publish("watch_change", {
                "repo_path": "/path/to/repo",
                "files_changed": 5
            })
        """
        async with self._lock:
            # Create event
            event = Event(
                event_type=event_type,
                data=data,
                source=source,
                workspace_id=self.workspace_id,
            )
            
            # Add to queue
            self._queues[event_type].append(event)
            
            # Trim queue if too large
            if len(self._queues[event_type]) > self.history_limit:
                self._queues[event_type] = self._queues[event_type][-self.history_limit:]
            
            # Add to history
            self._history.append(event)
            if len(self._history) > self.history_limit:
                self._history = self._history[-self.history_limit:]
            
            # Notify subscribers
            await self._notify_subscribers(event_type, event)
            
            logger.debug(f"Published event: {event}")
            return event
    
    async def _notify_subscribers(self, event_type: str, event: Event) -> None:
        """
        Notify subscribers of an event.
        
        Args:
            event_type: Type of event
            event: Event to notify
        """
        # Notify type-specific subscribers
        for queue in self._subscribers.get(event_type, []):
            try:
                await queue.put(event)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full for {event_type}")
        
        # Notify wildcard subscribers
        for queue in self._subscribers.get("*", []):
            try:
                await queue.put(event)
            except asyncio.QueueFull:
                logger.warning("Wildcard subscriber queue full")
    
    async def subscribe(
        self,
        event_types: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> AsyncGenerator[Event, None]:
        """
        Subscribe to events.
        
        Args:
            event_types: List of event types to subscribe to (None for all)
            timeout: Timeout for waiting (None for infinite)
            
        Yields:
            Events matching subscription
            
        Example:
            async for event in bus.subscribe(["watch_change", "gap_found"]):
                print(f"Event: {event.type} - {event.data}")
        """
        # Create queue for this subscriber
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        
        # Determine subscription keys
        keys = event_types if event_types else ["*"]
        
        async with self._lock:
            # Register subscriber
            for key in keys:
                if len(self._subscribers[key]) >= MAX_SUBSCRIBERS_PER_QUEUE:
                    logger.warning(f"Max subscribers reached for {key}")
                    continue
                self._subscribers[key].append(queue)
        
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                    yield event
                except asyncio.TimeoutError:
                    if timeout is not None:
                        break
        finally:
            # Unregister subscriber
            async with self._lock:
                for key in keys:
                    if queue in self._subscribers[key]:
                        self._subscribers[key].remove(queue)
    
    async def get_history(
        self,
        limit: int = 50,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Event]:
        """
        Get event history.
        
        Args:
            limit: Maximum events to return
            event_type: Filter by event type (None for all)
            since: Filter by timestamp (None for all)
            
        Returns:
            List of events matching filters
            
        Example:
            events = await bus.get_history(
                limit=50,
                event_type="watch_change",
                since=datetime.now() - timedelta(hours=1)
            )
        """
        async with self._lock:
            events = self._history.copy()
        
        # Filter by type
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        # Filter by timestamp
        if since:
            events = [
                e for e in events
                if datetime.fromisoformat(e.timestamp) >= since
            ]
        
        # Limit and reverse (newest first)
        events = events[-limit:][::-1]
        
        return events
    
    async def clear_history(self, older_than: Optional[timedelta] = None) -> int:
        """
        Clear event history.
        
        Args:
            older_than: Only clear events older than this (None for all)
            
        Returns:
            Number of events cleared
        """
        async with self._lock:
            if older_than:
                cutoff = datetime.now() - older_than
                original_count = len(self._history)
                self._history = [
                    e for e in self._history
                    if datetime.fromisoformat(e.timestamp) >= cutoff
                ]
                cleared = original_count - len(self._history)
            else:
                cleared = len(self._history)
                self._history = []
            
            # Clear queues
            cleared += sum(len(q) for q in self._queues.values())
            self._queues.clear()
            
            logger.info(f"Cleared {cleared} events from history")
            return cleared
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.
        
        Returns:
            Stats dict with queue sizes, subscriber counts, etc.
        """
        return {
            "workspace_id": self.workspace_id,
            "history_size": len(self._history),
            "queue_sizes": {
                event_type: len(events)
                for event_type, events in self._queues.items()
            },
            "subscriber_counts": {
                event_type: len(subs)
                for event_type, subs in self._subscribers.items()
            },
            "history_limit": self.history_limit,
            "history_ttl_hours": self.history_ttl.total_seconds() / 3600,
        }


# Global event bus instance (singleton pattern)
_event_bus: Optional[EventBus] = None


def get_event_bus(workspace_id: str = "default") -> EventBus:
    """
    Get or create the global event bus.
    
    Args:
        workspace_id: Workspace identifier
        
    Returns:
        Global EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus(workspace_id)
    return _event_bus


def reset_event_bus() -> None:
    """
    Reset the global event bus (for testing).
    
    Clears the singleton instance.
    """
    global _event_bus
    if _event_bus:
        _event_bus = None


# Convenience functions

async def publish_event(
    event_type: str,
    data: Dict[str, Any],
    source: str = "autonomous",
) -> Event:
    """
    Publish an event (convenience function).
    
    Args:
        event_type: Type of event
        data: Event payload
        source: Event source
        
    Returns:
        Published event
    """
    bus = get_event_bus()
    return await bus.publish(event_type, data, source)


async def get_event_history(
    limit: int = 50,
    event_type: Optional[str] = None,
) -> List[Event]:
    """
    Get event history (convenience function).
    
    Args:
        limit: Maximum events to return
        event_type: Filter by event type
        
    Returns:
        List of events
    """
    bus = get_event_bus()
    return await bus.get_history(limit, event_type)


async def subscribe_to_events(
    event_types: Optional[List[str]] = None,
) -> AsyncGenerator[Event, None]:
    """
    Subscribe to events (convenience function).
    
    Args:
        event_types: Event types to subscribe to
        
    Yields:
        Events matching subscription
    """
    bus = get_event_bus()
    async for event in bus.subscribe(event_types):
        yield event


def get_event_stats() -> Dict[str, Any]:
    """
    Get event bus statistics (convenience function).
    
    Returns:
        Stats dict
    """
    bus = get_event_bus()
    return bus.get_stats()
