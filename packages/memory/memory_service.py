"""
Memory Service - high-level API for storing and querying memories.

Sits on top of both qdrant_store (document RAG) and mem0_client
(user-centric intelligent memory) to provide:
  - store_memory()              -> embed + persist to Qdrant
  - query_memories()            -> semantic search over Qdrant
  - build_context()             -> hybrid assembly (Qdrant docs + Mem0 facts)
  - extract_and_store_from_turn -> auto-learn from conversation via Mem0
  - get_all_user_memories()     -> transparent view into Mem0 memories
  - forget_memory()             -> delete a specific Mem0 memory
"""

from __future__ import annotations

import logging
from typing import Any

from packages.memory import qdrant_store
from packages.memory.schemas import MemoryItem, MemorySearchResult, MemoryType
from packages.shared.config import settings

logger = logging.getLogger(__name__)

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


def _clip_text(text: str, limit: int) -> str:
    text = (text or "").strip()
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


def _fit_section(sections: list[str], candidate: str, budget: int) -> bool:
    if not candidate.strip():
        return False

    current = "\n\n".join(sections)
    remaining = budget - len(current)
    if remaining <= 0:
        return False

    if sections:
        remaining -= 2
    if remaining <= 0:
        return False

    clipped = _clip_text(candidate, remaining)
    if not clipped.strip():
        return False

    sections.append(clipped)
    return True


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


async def extract_and_store_from_turn(
    messages: list[dict[str, str]],
    user_id: str = "default",
) -> dict[str, Any]:
    """
    Auto-extract facts from a conversation turn via Mem0.
    """
    try:
        from packages.memory.mem0_client import mem0_add

        result = mem0_add(messages, user_id=user_id)
        logger.info(
            "Extracted memories from turn for user=%s: %s",
            user_id,
            result,
        )
        return result if isinstance(result, dict) else {"result": result}
    except Exception as exc:
        logger.warning("Mem0 extraction failed (non-fatal): %s", exc)
        return {"error": str(exc), "extracted": 0}


async def get_all_user_memories(
    user_id: str = "default",
) -> list[dict[str, Any]]:
    """
    Get all Mem0 memories for a user (for transparency and debugging).
    """
    try:
        from packages.memory.mem0_client import mem0_get_all

        return mem0_get_all(user_id=user_id)
    except Exception as exc:
        logger.warning("Could not retrieve Mem0 memories: %s", exc)
        return []


async def forget_memory(memory_id: str) -> dict[str, Any]:
    """
    Delete a specific Mem0 memory by ID.
    """
    try:
        from packages.memory.mem0_client import mem0_delete

        result = mem0_delete(memory_id)
        return {"status": "deleted", "memory_id": memory_id, "result": result}
    except Exception as exc:
        logger.error("Failed to delete memory %s: %s", memory_id, exc)
        return {"status": "error", "error": str(exc)}


async def build_context(
    user_message: str,
    user_id: str = "default",
    k: int = 5,
) -> str:
    """
    Build a compact hybrid context string from both Qdrant RAG and Mem0 memories.
    """
    total_budget = max(settings.rag_context_char_budget, 400)
    sections: list[str] = []

    try:
        from packages.memory.mem0_client import mem0_search

        mem0_results = mem0_search(
            user_message,
            user_id=user_id,
            limit=min(k, settings.rag_memory_limit),
        )
        memory_lines = []
        for i, mem in enumerate(mem0_results[: settings.rag_memory_limit], 1):
            memory_text = mem.get("memory", mem.get("content", ""))
            clipped = _clip_text(memory_text, 220)
            if clipped:
                memory_lines.append(f"  {i}. {clipped}")
        if memory_lines:
            _fit_section(
                sections,
                "## What I Know About You\n" + "\n".join(memory_lines),
                total_budget,
            )
    except Exception as exc:
        logger.debug("Mem0 context unavailable: %s", exc)

    try:
        qdrant_results = await qdrant_store.search(query=user_message, k=k)
        doc_results = [
            r for r in qdrant_results
            if r.get("metadata", {}).get("content_type") == "document"
            or r.get("metadata", {}).get("source")
            or r.get("metadata", {}).get("source_path")
        ]
        doc_lines = []
        for i, hit in enumerate(doc_results[:3], 1):
            meta = hit.get("metadata", {})
            source = meta.get("source") or meta.get("source_path") or "unknown"
            section = meta.get("section", meta.get("section_title", ""))
            content = _clip_text(hit.get("content", ""), settings.rag_doc_snippet_chars)
            if not content:
                continue
            label = source
            if section:
                label += f" -> {section}"
            doc_lines.append(f"  {i}. [{label}] {content}")
        if doc_lines:
            _fit_section(
                sections,
                "## Relevant Documents and Code\n" + "\n".join(doc_lines),
                total_budget,
            )
    except Exception as exc:
        logger.debug("Qdrant context unavailable: %s", exc)

    if not sections:
        try:
            legacy_results = await query_memories(user_id=user_id, query=user_message, k=3)
            legacy_lines = []
            for i, mem in enumerate(legacy_results[:3], 1):
                clipped = _clip_text(mem["content"], 220)
                if clipped:
                    legacy_lines.append(f"  {i}. [{mem['memory_type']}] {clipped}")
            if legacy_lines:
                _fit_section(
                    sections,
                    "## Previous Interactions\n" + "\n".join(legacy_lines),
                    total_budget,
                )
        except Exception as exc:
            logger.debug("Legacy memory context unavailable: %s", exc)

    if not sections:
        return ""

    header = (
        "Use this context to personalize the response. "
        "Reference relevant facts briefly and only when they materially help."
    )
    return _clip_text(header + "\n\n" + "\n\n".join(sections), total_budget)
