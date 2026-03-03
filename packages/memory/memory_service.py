"""
Memory Service — high-level API for storing and querying memories.

Sits on top of qdrant_store and provides:
  - store_memory()   → embed + persist
  - query_memories() → semantic search
  - build_context()  → assemble relevant memories into a prompt prefix
"""

from __future__ import annotations

import logging
from typing import Any

from packages.memory.schemas import MemoryItem, MemorySearchResult, MemoryType
from packages.memory import qdrant_store

logger = logging.getLogger(__name__)

# Ensure collections exist on first import
_initialized = False


async def _ensure_init() -> None:
    global _initialized
    if not _initialized:
        try:
            await qdrant_store.init_collections()
            _initialized = True
        except Exception as exc:
            logger.warning("Could not initialize Qdrant collections: %s", exc)
            raise


async def store_memory(
    user_id: str,
    content: str,
    memory_type: str = "PROFILE",
) -> dict[str, Any]:
    """
    Store a new memory in Qdrant.

    Returns:
        Dict with 'id' and 'memory_type' of the stored item.
    """
    await _ensure_init()

    item = MemoryItem(
        user_id=user_id,
        content=content,
        memory_type=MemoryType(memory_type),
    )

    metadata = {
        "user_id": item.user_id,
        "memory_type": item.memory_type.value,
        "timestamp": item.timestamp.isoformat(),
    }

    point_id = await qdrant_store.upsert(
        text=item.content,
        metadata=metadata,
        point_id=item.id,
    )

    logger.info("Stored memory %s (type=%s) for user %s", point_id, memory_type, user_id)
    return {"id": point_id, "memory_type": memory_type}


async def query_memories(
    user_id: str,
    query: str,
    k: int = 5,
) -> list[dict[str, Any]]:
    """
    Semantic search for memories related to a query.

    Returns:
        List of MemorySearchResult-like dicts sorted by relevance.
    """
    await _ensure_init()

    raw_results = await qdrant_store.search(query=query, k=k)

    # Filter by user_id and map to response format
    results = []
    for hit in raw_results:
        meta = hit.get("metadata", {})
        if meta.get("user_id", "default") == user_id:
            results.append(
                MemorySearchResult(
                    id=hit["id"],
                    content=hit["content"],
                    memory_type=meta.get("memory_type", "PROFILE"),
                    score=hit["score"],
                    metadata=meta,
                ).model_dump()
            )

    return results


async def build_context(
    user_message: str,
    user_id: str = "default",
    k: int = 5,
) -> str:
    """
    Build a context string from relevant memories for RAG.

    Returns:
        A system-prompt-style string with relevant memories,
        or empty string if no memories found.
    """
    try:
        memories = await query_memories(user_id=user_id, query=user_message, k=k)
    except Exception as exc:
        logger.warning("Could not query memories for context: %s", exc)
        return ""

    if not memories:
        return ""

    # Build a concise context block
    lines = ["Here are relevant facts about the user from previous interactions:\n"]
    for i, mem in enumerate(memories, 1):
        lines.append(f"  {i}. [{mem['memory_type']}] {mem['content']}")

    lines.append("\nUse these facts to personalize your response when relevant.")
    return "\n".join(lines)
