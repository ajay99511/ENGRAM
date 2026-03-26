"""
Model Registry — discover and manage available LLM models.

Auto-discovers locally installed Ollama models and merges them with
statically defined remote models (Gemini, Claude, etc.).

Usage:
    from packages.model_gateway.registry import get_all_models, get_active_model

    models = await get_all_models()
    active = get_active_model()
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
from pydantic import BaseModel

from packages.shared.config import settings

logger = logging.getLogger(__name__)


# ── Data Models ──────────────────────────────────────────────────────


class ModelInfo(BaseModel):
    """Metadata for a single LLM model."""
    id: str                            # e.g. "ollama/llama3.2"
    name: str                          # e.g. "llama3.2:latest"
    provider: str                      # "ollama" | "gemini" | "anthropic" | "deepseek"
    size_gb: float | None = None       # disk size in GB (Ollama only)
    parameter_size: str | None = None  # e.g. "7B", "24B"
    is_local: bool = True
    is_active: bool = False
    is_embedding: bool = False         # True for embedding-only models
    modified_at: str | None = None
    # Extended metadata
    description: str | None = None
    context_window: str | None = None  # e.g. "1M tokens"
    pricing_input: str | None = None   # e.g. "$0.10 / 1M"
    pricing_output: str | None = None  # e.g. "$0.40 / 1M"
    is_recommended: bool = False
    api_key_set: bool = True           # Whether required API key is configured
    # Capability metadata
    supports_tool_calls: bool = False
    supports_reasoning: bool = False
    supports_temperature: bool = True
    requires_reasoning_echo: bool = False


# ── Active model state ───────────────────────────────────────────────

_active_model: str | None = None
_ACTIVE_MODEL_FILE = Path(settings.data_dir) / "active_model.json"


def _load_active_model() -> None:
    """Load the active model from disk, if present."""
    global _active_model
    try:
        if _ACTIVE_MODEL_FILE.exists():
            data = json.loads(_ACTIVE_MODEL_FILE.read_text(encoding="utf-8"))
            model_id = data.get("active_model")
            if model_id:
                _active_model = model_id
    except Exception as exc:
        logger.warning("Failed to load active model from disk: %s", exc)


def _save_active_model(model_id: str) -> None:
    """Persist the active model to disk."""
    try:
        _ACTIVE_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ACTIVE_MODEL_FILE.write_text(
            json.dumps({"active_model": model_id}, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Failed to save active model to disk: %s", exc)


# Load active model on import
_load_active_model()


def get_active_model() -> str:
    """Return the currently active model ID."""
    return _active_model or settings.default_local_model


def set_active_model(model_id: str) -> str:
    """Set the active model and return its ID."""
    global _active_model
    _active_model = model_id
    _save_active_model(model_id)
    logger.info("Active model switched to: %s", model_id)
    return model_id


# ── Ollama discovery ─────────────────────────────────────────────────

# Models that are embedding-only (should not be used for chat)
_EMBEDDING_MODELS = {"nomic-embed-text", "all-minilm", "mxbai-embed-large"}


async def list_ollama_models() -> list[ModelInfo]:
    """
    Query the local Ollama instance for installed models.
    Returns a list of ModelInfo for each locally available model.
    """
    url = f"{settings.ollama_api_base}/api/tags"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        logger.warning("Ollama not reachable at %s", settings.ollama_api_base)
        return []
    except Exception as exc:
        logger.warning("Failed to list Ollama models: %s", exc)
        return []

    models: list[ModelInfo] = []
    active = get_active_model()

    for entry in data.get("models", []):
        name = entry.get("name", "")
        model_id = f"ollama/{name}"
        size_bytes = entry.get("size", 0)
        size_gb = round(size_bytes / (1024 ** 3), 1) if size_bytes else None

        # Extract parameter size from details if available
        details = entry.get("details", {})
        param_size = details.get("parameter_size", None)

        # Check if this is an embedding-only model
        base_name = name.split(":")[0]
        is_embedding = base_name in _EMBEDDING_MODELS

        models.append(ModelInfo(
            id=model_id,
            name=name,
            provider="ollama",
            size_gb=size_gb,
            parameter_size=param_size,
            is_local=True,
            is_active=(model_id == active),
            is_embedding=is_embedding,
            modified_at=entry.get("modified_at"),
            supports_tool_calls=False,
            supports_reasoning=False,
            supports_temperature=True,
            requires_reasoning_echo=False,
        ))

    return models


# ── Static remote models ─────────────────────────────────────────────

# Gemini model catalog — ordered by cost efficiency
_GEMINI_MODELS = [
    {
        "id": "gemini/gemini-2.5-flash-lite",
        "name": "Gemini 2.5 Flash-Lite",
        "description": "Most cost-efficient. Great for everyday chat and high-volume tasks.",
        "context_window": "1M tokens",
        "pricing_input": "$0.10 / 1M",
        "pricing_output": "$0.40 / 1M",
        "is_recommended": True,
    },
    {
        "id": "gemini/gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "description": "Fast and capable. Ideal for RAG, search, and general queries.",
        "context_window": "1M tokens",
        "pricing_input": "$0.30 / 1M",
        "pricing_output": "$2.50 / 1M",
        "is_recommended": True,
    },
    {
        "id": "gemini/gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "description": "Top-tier reasoning and coding. Use for complex problem-solving.",
        "context_window": "1M tokens",
        "pricing_input": "$1.25 / 1M",
        "pricing_output": "$10.00 / 1M",
        "is_recommended": False,
    },
    {
        "id": "gemini/gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "description": "Previous-gen fallback. Reliable and low-cost.",
        "context_window": "1M tokens",
        "pricing_input": "$0.10 / 1M",
        "pricing_output": "$0.40 / 1M",
        "is_recommended": False,
    },
]

_DEEPSEEK_MODELS = [
    {
        "id": "deepseek/deepseek-chat",
        "name": "DeepSeek Chat (V3.2)",
        "description": "DeepSeek general chat model with tool-calling support.",
        "context_window": "128K tokens",
        "pricing_input": "$0.028 / 1M (cache hit), $0.28 / 1M (cache miss)",
        "pricing_output": "$0.42 / 1M",
        "is_recommended": True,
        "supports_tool_calls": True,
        "supports_reasoning": False,
        "supports_temperature": True,
        "requires_reasoning_echo": False,
    },
    {
        "id": "deepseek/deepseek-reasoner",
        "name": "DeepSeek Reasoner (V3.2 Thinking)",
        "description": "Reasoning mode with chain-of-thought and tool-calling support.",
        "context_window": "128K tokens",
        "pricing_input": "$0.028 / 1M (cache hit), $0.28 / 1M (cache miss)",
        "pricing_output": "$0.42 / 1M",
        "is_recommended": False,
        "supports_tool_calls": True,
        "supports_reasoning": True,
        "supports_temperature": False,
        "requires_reasoning_echo": True,
    },
]


def _check_api_key(provider: str) -> bool:
    """Check if the API key for a provider is configured."""
    key_map = {
        "gemini": settings.gemini_api_key,
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "deepseek": settings.deepseek_api_key,
    }
    key = key_map.get(provider, "")
    return bool(key and key.strip())


def _static_remote_models() -> list[ModelInfo]:
    """
    Return statically defined remote model entries.
    These are always available (if API keys are configured).
    """
    active = get_active_model()
    remotes: list[ModelInfo] = []

    # Gemini models
    gemini_key_set = _check_api_key("gemini")
    for gm in _GEMINI_MODELS:
        remotes.append(ModelInfo(
            id=gm["id"],
            name=gm["name"],
            provider="gemini",
            is_local=False,
            is_active=(gm["id"] == active),
            description=gm["description"],
            context_window=gm["context_window"],
            pricing_input=gm["pricing_input"],
            pricing_output=gm["pricing_output"],
            is_recommended=gm["is_recommended"],
            api_key_set=gemini_key_set,
            supports_tool_calls=True,
            supports_reasoning=False,
            supports_temperature=True,
            requires_reasoning_echo=False,
        ))

    # Claude
    claude_id = "anthropic/claude-sonnet-4-20250514"
    remotes.append(ModelInfo(
        id=claude_id,
        name="Claude Sonnet 4",
        provider="anthropic",
        is_local=False,
        is_active=(claude_id == active),
        description="Anthropic's flagship. Strong at writing and analysis.",
        pricing_input="$3.00 / 1M",
        pricing_output="$15.00 / 1M",
        api_key_set=_check_api_key("anthropic"),
        supports_tool_calls=True,
        supports_reasoning=False,
        supports_temperature=True,
        requires_reasoning_echo=False,
    ))

    # DeepSeek
    deepseek_key_set = _check_api_key("deepseek")
    for dm in _DEEPSEEK_MODELS:
        remotes.append(ModelInfo(
            id=dm["id"],
            name=dm["name"],
            provider="deepseek",
            is_local=False,
            is_active=(dm["id"] == active),
            description=dm["description"],
            context_window=dm["context_window"],
            pricing_input=dm["pricing_input"],
            pricing_output=dm["pricing_output"],
            is_recommended=dm["is_recommended"],
            api_key_set=deepseek_key_set,
            supports_tool_calls=dm["supports_tool_calls"],
            supports_reasoning=dm["supports_reasoning"],
            supports_temperature=dm["supports_temperature"],
            requires_reasoning_echo=dm["requires_reasoning_echo"],
        ))

    return remotes


# ── Public API ───────────────────────────────────────────────────────


async def get_all_models() -> list[ModelInfo]:
    """
    Get all available models: local Ollama + remote providers.
    Chat-capable models are listed first, embedding models last.
    """
    ollama = await list_ollama_models()
    remotes = _static_remote_models()

    all_models = ollama + remotes

    # Sort: chat models first, embedding models last
    all_models.sort(key=lambda m: (m.is_embedding, not m.is_local, m.name))

    return all_models


async def get_chat_models() -> list[ModelInfo]:
    """Get only models usable for chat (excludes embedding-only models)."""
    all_models = await get_all_models()
    return [m for m in all_models if not m.is_embedding]


async def get_model_by_id(model_id: str) -> ModelInfo | None:
    """Find a specific model by its ID."""
    for m in await get_all_models():
        if m.id == model_id:
            return m
    return None


def infer_model_capabilities(model_id: str) -> dict[str, bool]:
    """
    Infer capabilities for a model id/key without async lookups.

    This is used by runtime call sites (gateway/crew) that need fast
    capability checks.
    """
    resolved = settings.resolve_model(model_id).lower()

    if "deepseek-reasoner" in resolved:
        return {
            "supports_tool_calls": True,
            "supports_reasoning": True,
            "supports_temperature": False,
            "requires_reasoning_echo": True,
        }
    if "deepseek-chat" in resolved:
        return {
            "supports_tool_calls": True,
            "supports_reasoning": False,
            "supports_temperature": True,
            "requires_reasoning_echo": False,
        }
    if resolved.startswith("gemini/") or resolved.startswith("anthropic/") or resolved.startswith("openai/"):
        return {
            "supports_tool_calls": True,
            "supports_reasoning": False,
            "supports_temperature": True,
            "requires_reasoning_echo": False,
        }
    if resolved.startswith("ollama/"):
        return {
            "supports_tool_calls": False,
            "supports_reasoning": False,
            "supports_temperature": True,
            "requires_reasoning_echo": False,
        }

    return {
        "supports_tool_calls": False,
        "supports_reasoning": False,
        "supports_temperature": True,
        "requires_reasoning_echo": False,
    }
