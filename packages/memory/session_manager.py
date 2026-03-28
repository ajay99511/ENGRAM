"""
Session Manager (Layer 2 of 5-Layer Memory System)

Manages session lifecycle, providing a high-level API for session operations.
Wraps JSONL store with session-specific logic.

Features:
- Session creation with metadata
- Message tracking
- Tool result tracking
- Session reset/compaction triggers
- Daily reset at 4 AM local time

Usage:
    from packages.memory.session_manager import SessionManager
    
    async with SessionManager(user_id="default") as session:
        await session.add_message("user", "Hello")
        response = await get_llm_response()
        await session.add_message("assistant", response)
"""

import logging
from datetime import datetime, time
from typing import Literal
import uuid

from packages.memory.jsonl_store import (
    JSONLEntry,
    append_entry,
    load_transcript,
    get_session_stats,
    SessionStats,
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    High-level session manager for conversation lifecycle.
    """
    
    DAILY_RESET_HOUR = 4  # 4 AM local time
    
    def __init__(
        self,
        user_id: str = "default",
        session_id: str | None = None,
        session_type: Literal["main", "isolated", "silent"] = "main",
    ):
        """
        Initialize session manager.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID (auto-generated if not provided)
            session_type: "main" for persistent, "isolated" for fresh each time, "silent" for no delivery
        """
        self.user_id = user_id
        self.session_type = session_type
        self.session_id = session_id or self._generate_session_id()
        self.created_at = datetime.now()
        self._stats: SessionStats | None = None
    
    def _generate_session_id(self) -> str:
        """Generate a session ID based on session type."""
        if self.session_type == "isolated":
            # Include timestamp for unique isolated sessions
            return f"{self.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        else:
            # Stable session ID for main sessions
            return f"{self.user_id}_main"
    
    async def __aenter__(self) -> "SessionManager":
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.finish()
    
    async def start(self) -> None:
        """Initialize session with metadata."""
        # Check for daily reset (4 AM)
        if self._should_daily_reset():
            logger.info(f"Daily reset triggered for session {self.session_id}")
            await self.reset(reason="daily_reset")
        
        # Add session info entry
        await append_entry(
            self.session_id,
            JSONLEntry(
                type="session_info",
                content={
                    "user_id": self.user_id,
                    "session_type": self.session_type,
                    "started_at": self.created_at.isoformat(),
                    "reset_reason": "new_session",
                },
            ),
        )
        
        logger.info(f"Started session {self.session_id} for user {self.user_id}")
    
    async def finish(self) -> None:
        """Finish session, update metadata."""
        await append_entry(
            self.session_id,
            JSONLEntry(
                type="session_info",
                content={
                    "user_id": self.user_id,
                    "session_type": self.session_type,
                    "finished_at": datetime.now().isoformat(),
                },
            ),
        )
        
        logger.debug(f"Finished session {self.session_id}")
    
    def _should_daily_reset(self) -> bool:
        """Check if daily reset should trigger."""
        if self.session_type != "main":
            return False
        
        now = datetime.now()
        reset_time = time(self.DAILY_RESET_HOUR, 0)
        
        # Check if we're within the reset window (4:00-4:01 AM)
        if now.time().hour == self.DAILY_RESET_HOUR and now.minute == 0:
            return True
        
        return False
    
    async def reset(self, reason: str = "manual_reset") -> None:
        """
        Reset session (create new session ID).
        
        Args:
            reason: Reason for reset (manual_reset, daily_reset, command_reset)
        """
        old_session_id = self.session_id
        
        # Archive old session stats
        old_stats = await get_session_stats(old_session_id)
        logger.info(
            f"Archiving session {old_session_id}: "
            f"{old_stats.total_entries} entries, "
            f"{old_stats.estimated_tokens} tokens"
        )
        
        # Generate new session ID
        self.session_id = self._generate_session_id()
        self.created_at = datetime.now()
        
        logger.info(f"Reset session from {old_session_id} to {self.session_id} (reason: {reason})")
    
    async def add_message(
        self,
        role: Literal["user", "assistant", "system"],
        content: str,
        model_used: str | None = None,
        memory_used: bool = False,
    ) -> str:
        """
        Add a user/assistant/system message to the transcript.
        
        Args:
            role: Message role
            content: Message content
            model_used: Model identifier (for assistant messages)
            memory_used: Whether RAG memory was used
        
        Returns:
            Entry ID
        """
        entry_content = {
            "role": role,
            "content": content,
        }
        
        if role == "assistant":
            if model_used:
                entry_content["model_used"] = model_used
            if memory_used:
                entry_content["memory_used"] = memory_used
        
        entry = JSONLEntry(
            type="message",
            content=entry_content,
        )
        
        return await append_entry(self.session_id, entry)
    
    async def add_tool_result(
        self,
        tool_name: str,
        tool_result: dict,
        tool_call_id: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> str:
        """
        Add a tool result to the transcript.
        
        Args:
            tool_name: Name of the tool called
            tool_result: Tool result dict (will be redacted)
            tool_call_id: Optional tool call identifier
            success: Whether tool execution succeeded
            error: Error message if failed
        
        Returns:
            Entry ID
        """
        entry_content = {
            "tool_name": tool_name,
            "tool_result": tool_result,
            "success": success,
            "tool_call_id": tool_call_id or str(uuid.uuid4()),
        }
        
        if error:
            entry_content["error"] = error
        
        entry = JSONLEntry(
            type="toolResult",
            content=entry_content,
        )
        
        return await append_entry(self.session_id, entry)
    
    async def add_compaction(
        self,
        summary: str,
        first_kept_entry_id: str,
        entries_removed: int,
    ) -> str:
        """
        Add a compaction entry to the transcript.
        
        Args:
            summary: Compaction summary
            first_kept_entry_id: ID of first entry kept after compaction
            entries_removed: Number of entries removed
        
        Returns:
            Entry ID
        """
        entry = JSONLEntry(
            type="compaction",
            content={
                "summary": summary,
                "firstKeptEntryId": first_kept_entry_id,
                "entries_removed": entries_removed,
            },
            metadata={
                "compacted_at": datetime.now().isoformat(),
            },
        )
        
        return await append_entry(self.session_id, entry)
    
    async def get_messages(
        self,
        limit: int | None = None,
        include_tool_results: bool = True,
    ) -> list[dict]:
        """
        Get messages from transcript suitable for LLM API.
        
        Args:
            limit: Maximum number of messages to return (None for all)
            include_tool_results: Whether to include tool results
        
        Returns:
            List of message dicts
        """
        entries = await load_transcript(self.session_id)
        
        messages = []
        for entry in entries:
            if entry.type == "message":
                content = entry.content
                if isinstance(content, dict):
                    messages.append({
                        "role": content.get("role", "user"),
                        "content": content.get("content", ""),
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": str(content),
                    })
            
            elif include_tool_results and entry.type == "toolResult":
                messages.append({
                    "role": "tool",
                    "content": str(entry.content),
                    "tool_call_id": entry.content.get("tool_call_id", entry.id),
                })
        
        # Apply limit (from end for recent messages)
        if limit and len(messages) > limit:
            messages = messages[-limit:]
        
        return messages
    
    async def get_stats(self) -> SessionStats:
        """Get session statistics."""
        if self._stats is None:
            self._stats = await get_session_stats(self.session_id)
        return self._stats
    
    async def get_token_count(self) -> int:
        """Get estimated token count for session."""
        stats = await self.get_stats()
        return stats.estimated_tokens
    
    async def should_compact(
        self,
        context_window: int = 128_000,
        reserve_tokens: int = 4_000,
    ) -> bool:
        """
        Check if session should be compacted.
        
        Args:
            context_window: Model's context window size
            reserve_tokens: Tokens to reserve for new input/output
        
        Returns:
            True if compaction should trigger
        """
        token_count = await self.get_token_count()
        threshold = context_window - reserve_tokens
        
        return token_count > threshold


async def create_session(
    user_id: str = "default",
    session_type: Literal["main", "isolated", "silent"] = "main",
    session_id: str | None = None,
) -> SessionManager:
    """
    Create and start a new session.
    
    Args:
        user_id: User identifier
        session_type: Session type
        session_id: Optional custom session ID
    
    Returns:
        Started SessionManager instance
    """
    session = SessionManager(user_id=user_id, session_type=session_type, session_id=session_id)
    await session.start()
    return session
