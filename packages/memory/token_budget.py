"""
Token Budget Management

Utilities for managing token budgets across LLM interactions.
Features:
- Token estimation
- Budget allocation
- Message prioritization
- Provider-specific optimizations

Usage:
    from packages.memory.token_budget import TokenBudgetManager
    
    manager = TokenBudgetManager()
    budget = manager.allocate_budget(total=8000, system=500, response=2000)
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

# Token estimation constants
CHARS_PER_TOKEN = 4  # 1 token ≈ 4 characters for English
WORDS_PER_TOKEN = 0.75  # 1 token ≈ 0.75 words

# Provider-specific overhead
PROVIDER_OVERHEAD = {
    "ollama": 50,  # Small overhead
    "openai": 100,  # Larger overhead for API
    "anthropic": 150,  # Claude has more overhead
    "gemini": 100,
    "default": 50,
}

# Safety margins
SAFETY_MARGIN = 1.2  # 20% safety margin for token estimation


# ─────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────

@dataclass
class BudgetAllocation:
    """Token budget allocation."""
    total: int
    system: int
    history: int
    context: int
    response: int
    overhead: int
    
    @property
    def allocated(self) -> int:
        """Get total allocated tokens."""
        return self.system + self.history + self.context + self.response + self.overhead
    
    @property
    def remaining(self) -> int:
        """Get remaining tokens."""
        return self.total - self.allocated


# ─────────────────────────────────────────────────────────────────────
# Token Budget Manager
# ─────────────────────────────────────────────────────────────────────

class TokenBudgetManager:
    """
    Manage token budgets for LLM interactions.
    """
    
    def __init__(self, safety_margin: float = SAFETY_MARGIN):
        """
        Initialize token budget manager.
        
        Args:
            safety_margin: Safety margin for token estimation
        """
        self.safety_margin = safety_margin
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate tokens in text.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Basic estimation: chars / 4
        char_count = len(text)
        token_estimate = char_count // CHARS_PER_TOKEN
        
        # Apply safety margin
        return int(token_estimate * self.safety_margin)
    
    def estimate_message_tokens(self, message: dict[str, Any]) -> int:
        """
        Estimate tokens in a message.
        
        Args:
            message: Message dict
    
        Returns:
            Estimated token count
        """
        total = 0
        
        # Content
        content = message.get("content", "")
        if isinstance(content, str):
            total += self.estimate_tokens(content)
        elif isinstance(content, (dict, list)):
            total += self.estimate_tokens(str(content))
        
        # Role
        total += self.estimate_tokens(message.get("role", ""))
        
        # Other string fields
        for key, value in message.items():
            if key != "content" and isinstance(value, str):
                total += self.estimate_tokens(value)
        
        return total
    
    def estimate_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """
        Estimate tokens in multiple messages.
        
        Args:
            messages: Message list
    
        Returns:
            Estimated token count
        """
        return sum(self.estimate_message_tokens(m) for m in messages)
    
    def allocate_budget(
        self,
        total: int,
        system: int = 500,
        response: int = 2_000,
        context_ratio: float = 0.2,
        provider: str = "default",
    ) -> BudgetAllocation:
        """
        Allocate token budget across components.
        
        Args:
            total: Total available tokens
            system: System prompt tokens
            response: Reserve for response tokens
            context_ratio: Ratio for RAG context (0.0-1.0)
            provider: Provider for overhead calculation
    
        Returns:
            BudgetAllocation
        """
        # Calculate overhead
        overhead = PROVIDER_OVERHEAD.get(provider, PROVIDER_OVERHEAD["default"])
        
        # Calculate context tokens
        available = total - system - response - overhead
        context = int(available * context_ratio)
        
        # Remaining for history
        history = available - context
        
        return BudgetAllocation(
            total=total,
            system=system,
            history=max(history, 1_000),  # Min 1K for history
            context=context,
            response=response,
            overhead=overhead,
        )
    
    def prioritize_messages(
        self,
        messages: list[dict[str, Any]],
        budget: int,
        protect_last_n: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Prioritize messages to fit within budget.
        
        Keeps system messages, recent messages, and prunes old tool results.
        
        Args:
            messages: Message list
            budget: Token budget
            protect_last_n: Protect last N messages
    
        Returns:
            Prioritized message list
        """
        if not messages:
            return messages
        
        current_tokens = self.estimate_messages_tokens(messages)
        
        if current_tokens <= budget:
            return messages
        
        # Separate by type
        system_msgs = []
        user_msgs = []
        assistant_msgs = []
        tool_msgs = []
        
        for msg in messages:
            role = msg.get("role", "")
            if role == "system":
                system_msgs.append(msg)
            elif role == "user":
                user_msgs.append(msg)
            elif role == "assistant":
                assistant_msgs.append(msg)
            elif role == "tool":
                tool_msgs.append(msg)
        
        # Protect recent messages
        protected_count = protect_last_n
        protected_user = user_msgs[-protected_count:] if len(user_msgs) > protected_count else user_msgs
        protected_assistant = assistant_msgs[-protected_count:] if len(assistant_msgs) > protected_count else assistant_msgs
        
        # Calculate remaining budget
        protected_tokens = (
            self.estimate_messages_tokens(system_msgs) +
            self.estimate_messages_tokens(protected_user) +
            self.estimate_messages_tokens(protected_assistant)
        )
        
        remaining_budget = budget - protected_tokens
        
        if remaining_budget <= 0:
            # Can only keep protected messages
            return system_msgs + protected_user + protected_assistant
        
        # Try to keep some older messages
        older_user = user_msgs[:-protected_count] if len(user_msgs) > protected_count else []
        older_assistant = assistant_msgs[:-protected_count] if len(assistant_msgs) > protected_count else []
        
        # Add older messages while within budget
        result = system_msgs.copy()
        
        for msg in older_user + older_assistant:
            msg_tokens = self.estimate_message_tokens(msg)
            if msg_tokens <= remaining_budget:
                result.append(msg)
                remaining_budget -= msg_tokens
        
        # Add protected messages
        result.extend(protected_user)
        result.extend(protected_assistant)
        
        logger.debug(
            f"Prioritized messages: {len(messages)} → {len(result)}, "
            f"{current_tokens} → {self.estimate_messages_tokens(result)} tokens"
        )
        
        return result
    
    def trim_message(self, message: dict[str, Any], max_tokens: int) -> dict[str, Any]:
        """
        Trim a message to fit within token limit.
        
        Args:
            message: Message dict
            max_tokens: Maximum tokens
    
        Returns:
            Trimmed message
        """
        content = message.get("content", "")
        if not content:
            return message
        
        current_tokens = self.estimate_tokens(content)
        
        if current_tokens <= max_tokens:
            return message
        
        # Calculate trim position
        trim_ratio = max_tokens / current_tokens
        trim_chars = int(len(content) * trim_ratio)
        
        # Trim and add marker
        trimmed_content = content[:trim_chars] + " [... truncated ...]"
        
        return {**message, "content": trimmed_content}
    
    def get_budget_stats(
        self,
        messages: list[dict[str, Any]],
        budget: int,
    ) -> dict[str, Any]:
        """
        Get budget statistics.
        
        Args:
            messages: Message list
            budget: Token budget
    
        Returns:
            Statistics dict
        """
        current_tokens = self.estimate_messages_tokens(messages)
        available = budget - current_tokens
        usage_percent = (current_tokens / budget) * 100 if budget > 0 else 0
        
        return {
            "total_budget": budget,
            "current_tokens": current_tokens,
            "available_tokens": available,
            "usage_percent": usage_percent,
            "message_count": len(messages),
            "avg_tokens_per_message": current_tokens / len(messages) if messages else 0,
            "over_budget": current_tokens > budget,
        }


# ─────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Convenience function to estimate tokens."""
    manager = TokenBudgetManager()
    return manager.estimate_tokens(text)


def estimate_messages(messages: list[dict[str, Any]]) -> int:
    """Convenience function to estimate message tokens."""
    manager = TokenBudgetManager()
    return manager.estimate_messages_tokens(messages)


def allocate_budget(total: int, **kwargs) -> BudgetAllocation:
    """Convenience function to allocate budget."""
    manager = TokenBudgetManager()
    return manager.allocate_budget(total, **kwargs)
