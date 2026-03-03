"""
Qdrant Store — thin wrapper around qdrant-client for vector operations.

Handles:
  - Collection initialization (creates if not exists)
  - Upserting text + metadata with vector embeddings
  - Semantic search
  - Health checks
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from packages.shared.config import settings

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────
VECTOR_DIM = 768  # nomic-embed-text default dimension
COLLECTION = settings.qdrant_collection

# ── Lazy client (created on first use) ───────────────────────────────
_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    """Get or create the Qdrant client singleton."""
    global _client
    if _client is None:
        _client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
    return _client


async def init_collections() -> None:
    """Create the default collection if it doesn't exist."""
    client = _get_client()
    collections = client.get_collections().collections
    existing = {c.name for c in collections}

    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", COLLECTION)
    else:
        logger.info("Qdrant collection already exists: %s", COLLECTION)


async def health_check() -> list[str]:
    """Return list of existing collection names (proves connectivity)."""
    client = _get_client()
    collections = client.get_collections().collections
    return [c.name for c in collections]


async def upsert(
    text: str,
    metadata: dict[str, Any],
    point_id: str | None = None,
) -> str:
    """
    Embed text and upsert into Qdrant.

    Args:
        text:     The content to embed and store.
        metadata: Arbitrary metadata attached to the point.
        point_id: Optional deterministic ID; auto-generated if None.

    Returns:
        The point ID used.
    """
    client = _get_client()
    embedding = await _embed(text)

    if point_id is None:
        # Deterministic ID from content hash to avoid duplicates
        point_id = hashlib.sha256(text.encode()).hexdigest()[:32]

    # Store the original text in metadata for retrieval
    metadata["_content"] = text

    client.upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata,
            )
        ],
    )
    logger.info("Upserted point %s into %s", point_id, COLLECTION)
    return point_id


async def search(
    query: str,
    k: int = 5,
    filter_conditions: dict | None = None,
) -> list[dict[str, Any]]:
    """
    Semantic search: embed query then find nearest neighbors.

    Returns:
        List of dicts with keys: id, score, content, metadata
    """
    client = _get_client()
    query_vector = await _embed(query)

    results = client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        limit=k,
    ).points

    return [
        {
            "id": str(hit.id),
            "score": hit.score,
            "content": hit.payload.get("_content", ""),
            "metadata": {k: v for k, v in hit.payload.items() if k != "_content"},
        }
        for hit in results
    ]


# ── Embedding via Ollama ─────────────────────────────────────────────

async def _embed(text: str) -> list[float]:
    """
    Get embedding vector from Ollama's embedding endpoint.
    Uses the model configured in settings.embedding_model.
    """
    url = f"{settings.ollama_api_base}/api/embed"
    payload = {
        "model": settings.embedding_model,
        "input": text,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    embeddings = data.get("embeddings", [])
    if not embeddings:
        raise ValueError(f"No embeddings returned for text: {text[:50]}…")

    return embeddings[0]
