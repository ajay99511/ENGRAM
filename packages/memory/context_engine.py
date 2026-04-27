"""
Context Engine

Adaptive context management for LLM interactions.
Features:
- Adaptive context window (based on message size)
- Token budget management
- Session pruning (TTL-aware)
- Soft/hard trimming
- Provider-specific optimizations

Usage:
    from packages.memory.context_engine import ContextEngine
    
    engine = ContextEngine(session_id="user_main", model="local")
    context = await engine.assemble(messages, budget=8000)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

# Default context window sizes (tokens)
CONTEXT_WINDOWS = {
    "ollama": 8_000,  # Default Ollama models
    "llama3": 8_000,
    "llama3.1": 128_000,
    "gemini": 1_048_576,  # Gemini 1.5 Pro
    "claude": 200_000,  # Claude 3
    "gpt-4": 128_000,
    "default": 8_000,
}

# Reserve tokens for system prompt and response
RESERVE_TOKENS = 4_000

# Compaction trigger threshold
COMPACTION_THRESHOLD = 0.8  # Trigger at 80% of context window

# Pruning configuration
DEFAULT_TTL_SECONDS = 300  # 5 minutes for tool results
PROTECT_LAST_N = 3  # Always protect last N messages
SOFT_TRIM_THRESHOLD = 0.7  # Start soft trim at 70%

# Token estimation (1 token ≈ 4 characters for English)
CHARS_PER_TOKEN = 4


# ─────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ContextResult:
    """Result of context assembly."""
    messages: list[dict[str, Any]]
    estimated_tokens: int
    context_window: int
    reserve_tokens: int
    available_tokens: int
    compression_ratio: float
    metadata: dict[str, Any]


@dataclass
class TokenBudget:
    """Token budget configuration."""
    total: int
    system: int
    history: int
    context: int
    response: int
    
    @property
    def available(self) -> int:
        """Get available tokens for history."""
        return self.history


# ─────────────────────────────────────────────────────────────────────
# Context Engine
# ─────────────────────────────────────────────────────────────────────

class ContextEngine:
    """
    Adaptive context management for LLM interactions.
    """
    
    def __init__(
        self,
        session_id: str,
        model: str = "local",
        context_window: int | None = None,
    ):
        """
        Initialize context engine.
        
        Args:
            session_id: Session identifier
            model: Model identifier (for context window lookup)
            context_window: Override context window size
        """
        self.session_id = session_id
        self.model = model
        self.context_window = context_window or self._get_context_window(model)
        self.reserve_tokens = RESERVE_TOKENS
    
    def _get_context_window(self, model: str) -> int:
        """Get context window for a model."""
        model_lower = model.lower()
        
        # Check specific models
        for key, window in CONTEXT_WINDOWS.items():
            if key in model_lower:
                return window
        
        # Default
        return CONTEXT_WINDOWS["default"]
    
    async def assemble(
        self,
        messages: list[dict[str, Any]],
        budget: int | None = None,
        system_context: str = "",
        include_tool_results: bool = True,
        include_skills: bool = True,
    ) -> ContextResult:
        """
        Assemble context for LLM call.
        """
        # Inject skill schemas if requested
        if include_skills:
            from packages.skills import registry
            skill_schemas = registry.get_all_schemas()
            if skill_schemas:
                skill_text = "\n## Available Skills\n" + "\n".join([f"- {s['name']}: {s['description']}" for s in skill_schemas])
                system_context = (system_context + "\n" + skill_text).strip()

        # Calculate budget
        if budget is None:
            budget = self.context_window - self.reserve_tokens
        
        # Create budget allocation
        token_budget = self._allocate_budget(budget, system_context)
        
        # Prune old tool results
        pruned_messages = await self._prune_messages(
            messages,
            ttl_seconds=DEFAULT_TTL_SECONDS,
            protect_last_n=PROTECT_LAST_N,
            include_tool_results=include_tool_results,
        )
        
        # Apply token limit
        trimmed_messages = await self._apply_token_limit(
            pruned_messages,
            token_budget.history,
        )
        
        # Add system context
        final_messages = await self._add_system_context(
            trimmed_messages,
            system_context,
            token_budget.system,
        )
        
        # Estimate final tokens
        estimated_tokens = self._estimate_tokens(final_messages)
        
        # Calculate compression ratio
        original_tokens = self._estimate_tokens(messages)
        compression_ratio = estimated_tokens / original_tokens if original_tokens > 0 else 1.0
        
        return ContextResult(
            messages=final_messages,
            estimated_tokens=estimated_tokens,
            context_window=self.context_window,
            reserve_tokens=self.reserve_tokens,
            available_tokens=budget,
            compression_ratio=compression_ratio,
            metadata={
                "original_messages": len(messages),
                "final_messages": len(final_messages),
                "pruned_count": len(messages) - len(pruned_messages),
                "trimmed_count": len(pruned_messages) - len(trimmed_messages),
            },
        )
    
    def _allocate_budget(self, total_budget: int, system_context: str) -> TokenBudget:
        """
        Allocate token budget across components.
        
        Args:
            total_budget: Total available tokens
            system_context: System context string
        
        Returns:
            TokenBudget with allocations
        """
        # Estimate system context tokens
        system_tokens = len(system_context) // CHARS_PER_TOKEN if system_context else 500
        
        # Allocate
        system = min(system_tokens + 500, total_budget // 4)  # Max 25% for system
        response = 2_000  # Reserve for response
        context = total_budget // 5  # 20% for RAG context
        
        # Remaining for history
        history = total_budget - system - response - context
        
        return TokenBudget(
            total=total_budget,
            system=system,
            history=max(history, 1_000),  # Min 1K for history
            context=context,
            response=response,
        )
    
    async def _prune_messages(
        self,
        messages: list[dict[str, Any]],
        ttl_seconds: int,
        protect_last_n: int,
        include_tool_results: bool,
    ) -> list[dict[str, Any]]:
        """
        Prune old tool results from messages.
        
        Args:
            messages: Message list
            ttl_seconds: TTL for tool results
            protect_last_n: Protect last N messages
            include_tool_results: Whether to include tool results
        
        Returns:
            Pruned message list
        """
        if not messages:
            return messages
        
        if not include_tool_results:
            # Filter out all tool results
            return [m for m in messages if m.get("role") != "tool"]
        
        now = datetime.now()
        pruned = []
        
        # Separate protected and prunable
        protected_count = min(protect_last_n, len(messages))
        to_prune = messages[:-protected_count] if protected_count < len(messages) else []
        protected = messages[-protected_count:] if protected_count > 0 else []
        
        # Prune old tool results
        for msg in to_prune:
            if msg.get("role") == "tool":
                # Check TTL
                msg_time = self._get_message_timestamp(msg)
                if msg_time:
                    age = (now - msg_time).total_seconds()
                    if age > ttl_seconds:
                        # Replace with placeholder
                        pruned.append({
                            "role": "tool",
                            "content": "[Old tool result content cleared]",
                        })
                        continue
            
            pruned.append(msg)
        
        # Add protected messages
        pruned.extend(protected)
        
        return pruned
    
    def _get_message_timestamp(self, msg: dict[str, Any]) -> datetime | None:
        """Extract timestamp from message."""
        # Check _timestamp field
        if "_timestamp" in msg:
            try:
                return datetime.fromisoformat(msg["_timestamp"])
            except (ValueError, TypeError):
                pass
        
        # Check metadata
        metadata = msg.get("metadata", {})
        if "timestamp" in metadata:
            try:
                return datetime.fromisoformat(metadata["timestamp"])
            except (ValueError, TypeError):
                pass
        
        return None
    
    async def _apply_token_limit(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
    ) -> list[dict[str, Any]]:
        """
        Apply token limit by trimming oldest messages.
        
        Args:
            messages: Message list
            max_tokens: Maximum tokens
        
        Returns:
            Trimmed message list
        """
        if not messages:
            return messages
        
        current_tokens = self._estimate_tokens(messages)
        
        if current_tokens <= max_tokens:
            return messages
        
        # Keep head (system) and tail (recent)
        head = []
        tail = []
        
        # Find system messages (always keep)
        for msg in messages:
            if msg.get("role") == "system":
                head.append(msg)
            else:
                break
        
        # Calculate how many recent messages to keep
        remaining_budget = max_tokens - self._estimate_tokens(head)
        messages_per_token = len(messages) / current_tokens if current_tokens > 0 else 1
        messages_to_keep = int(remaining_budget * messages_per_token * 0.9)  # 10% safety
        
        # Keep most recent
        if messages_to_keep > 0:
            tail = messages[-messages_to_keep:]
        
        # Insert trim marker
        if head and tail:
            trimmed_count = len(messages) - len(head) - len(tail)
            if trimmed_count > 0:
                tail.insert(0, {
                    "role": "system",
                    "content": f"[... {trimmed_count} older messages trimmed for brevity ...]",
                })
        
        result = head + tail
        
        logger.debug(
            f"Applied token limit: {current_tokens} → {self._estimate_tokens(result)} tokens, "
            f"kept {len(result)} of {len(messages)} messages"
        )
        
        return result
    
    async def _add_system_context(
        self,
        messages: list[dict[str, Any]],
        system_context: str,
        max_tokens: int,
    ) -> list[dict[str, Any]]:
        """
        Add system context to messages.
        
        Args:
            messages: Message list
            system_context: System context string
            max_tokens: Maximum tokens for system context
        
        Returns:
            Message list with system context
        """
        if not system_context:
            return messages
        
        # Truncate system context if needed
        context_tokens = len(system_context) // CHARS_PER_TOKEN
        if context_tokens > max_tokens:
            system_context = system_context[:max_tokens * CHARS_PER_TOKEN]
            system_context += " [... truncated ...]"
        
        # Add as first system message
        return [
            {"role": "system", "content": system_context},
            *messages,
        ]
    
    def _estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """
        Estimate tokens in messages.
        
        Args:
            messages: Message list
        
        Returns:
            Estimated token count
        """
        total_chars = 0
        
        for msg in messages:
            # Count content
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, (dict, list)):
                total_chars += len(str(content))
            
            # Count role and other fields
            total_chars += len(msg.get("role", ""))
            for key, value in msg.items():
                if key != "content" and isinstance(value, str):
                    total_chars += len(value)
        
        # Rough estimation: 1 token ≈ 4 chars
        return total_chars // CHARS_PER_TOKEN
    
    def should_compact(self, current_tokens: int) -> bool:
        """
        Check if context should be compacted.
        
        Args:
            current_tokens: Current token count
        
        Returns:
            True if compaction should trigger
        """
        threshold = int(self.context_window * COMPACTION_THRESHOLD)
        return current_tokens > threshold
    
    def get_context_stats(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Get context statistics.
        
        Args:
            messages: Message list
        
        Returns:
            Statistics dict
        """
        estimated_tokens = self._estimate_tokens(messages)
        available = self.context_window - self.reserve_tokens - estimated_tokens
        
        return {
            "session_id": self.session_id,
            "model": self.model,
            "context_window": self.context_window,
            "reserve_tokens": self.reserve_tokens,
            "current_tokens": estimated_tokens,
            "available_tokens": available,
            "usage_percent": (estimated_tokens / self.context_window) * 100,
            "message_count": len(messages),
            "should_compact": self.should_compact(estimated_tokens),
        }


# ─────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────

async def assemble_context(
    messages: list[dict[str, Any]],
    session_id: str,
    model: str = "local",
    system_context: str = "",
    budget: int | None = None,
) -> ContextResult:
    """
    Convenience function to assemble context.
    
    Args:
        messages: Message history
        session_id: Session identifier
        model: Model identifier
        system_context: System context
        budget: Token budget override
    
    Returns:
        ContextResult
    """
    engine = ContextEngine(session_id=session_id, model=model)
    return await engine.assemble(
        messages=messages,
        budget=budget,
        system_context=system_context,
    )


def get_context_window(model: str) -> int:
    """
    Get context window for a model.
    
    Args:
        model: Model identifier
    
    Returns:
        Context window size
    """
    return CONTEXT_WINDOWS.get(model, CONTEXT_WINDOWS["default"])
