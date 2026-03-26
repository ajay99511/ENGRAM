"""
Token-aware text budgeting helpers.

The project currently uses character budgets in multiple places. These helpers
provide approximate token budgeting and safer truncation boundaries while
remaining lightweight (no hard dependency on tokenizer packages).
"""

from __future__ import annotations

from typing import Any


def estimate_tokens(text: str) -> int:
    """
    Approximate token count using a conservative chars/token ratio.
    """
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _safe_boundary_slice(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 0:
        return ""

    chunk = text[:max_chars]
    boundary_chars = ["\n", ".", "!", "?", ";", ":", ",", " "]
    last_boundary = -1
    for marker in boundary_chars:
        idx = chunk.rfind(marker)
        if idx > last_boundary:
            last_boundary = idx

    if last_boundary > max_chars // 2:
        return chunk[: last_boundary + 1].rstrip()
    return chunk.rstrip()


def clip_text_to_token_budget(text: str, max_tokens: int, *, ellipsis: str = "...") -> str:
    """
    Clip text by approximate token budget while avoiding harsh mid-structure cuts.
    """
    text = (text or "").strip()
    if max_tokens <= 0:
        return ""
    if estimate_tokens(text) <= max_tokens:
        return text

    max_chars = max(1, max_tokens * 4)
    clipped = _safe_boundary_slice(text, max_chars)
    if clipped == text:
        return text
    if not clipped:
        return ""
    return clipped.rstrip() + ellipsis


def to_compact_json_preview(payload: Any, max_tokens: int) -> str:
    """
    Produce a bounded, readable preview of structured payloads.
    """
    if isinstance(payload, str):
        return clip_text_to_token_budget(payload, max_tokens)

    try:
        import json

        text = json.dumps(payload, ensure_ascii=False, default=str)
        return clip_text_to_token_budget(text, max_tokens)
    except Exception:
        return clip_text_to_token_budget(str(payload), max_tokens)
