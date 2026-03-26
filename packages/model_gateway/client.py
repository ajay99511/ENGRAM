"""
Model Gateway — unified LLM interface via LiteLLM.

This module offers:
  - `chat_completion()`: structured completion result (content/tool_calls/usage)
  - `chat()`: backward-compatible string response helper
  - `chat_stream()`: async token streaming helper
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import litellm

from packages.model_gateway.registry import infer_model_capabilities
from packages.shared.config import settings

logger = logging.getLogger(__name__)

# Suppress litellm printing to stdout
litellm.set_verbose = False

# Pass API keys to LiteLLM via environment (LiteLLM reads these)
if settings.gemini_api_key:
    os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.deepseek_api_key:
    os.environ["DEEPSEEK_API_KEY"] = settings.deepseek_api_key
if settings.deepseek_base_url:
    os.environ["DEEPSEEK_BASE_URL"] = settings.deepseek_base_url


@dataclass
class ChatCompletionResult:
    """Normalized structured completion response."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    reasoning_content: str | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    model: str = ""
    raw_message: dict[str, Any] = field(default_factory=dict)


def _redact_sensitive(text: str) -> str:
    """Redact common API key patterns and query parameters from logs/errors."""
    redacted = text
    redacted = re.sub(r"(key=)[^&\s'\"]+", r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "[REDACTED_GOOGLE_API_KEY]", redacted)
    redacted = re.sub(r"(api[_-]?key\s*[:=]\s*)([^\s,;]+)", r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"sk-[A-Za-z0-9_\-]{20,}", "[REDACTED_API_KEY]", redacted)
    return redacted


def _message_to_dict(message: Any) -> dict[str, Any]:
    if message is None:
        return {}
    if isinstance(message, dict):
        return dict(message)
    if hasattr(message, "model_dump"):
        dumped = message.model_dump()
        return dumped if isinstance(dumped, dict) else {}

    out: dict[str, Any] = {}
    for key in ("role", "content", "reasoning_content", "tool_calls", "function_call", "name"):
        if hasattr(message, key):
            out[key] = getattr(message, key)
    return out


def _tool_call_to_dict(tool_call: Any) -> dict[str, Any]:
    if isinstance(tool_call, dict):
        return dict(tool_call)

    fn_obj = getattr(tool_call, "function", None)
    fn_name = ""
    fn_args = ""
    if fn_obj is not None:
        fn_name = getattr(fn_obj, "name", "") or ""
        fn_args = getattr(fn_obj, "arguments", "") or ""

    return {
        "id": getattr(tool_call, "id", ""),
        "type": getattr(tool_call, "type", "function"),
        "function": {
            "name": fn_name,
            "arguments": fn_args,
        },
    }


def _normalize_response(response: Any, resolved_model: str) -> ChatCompletionResult:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ChatCompletionResult(content="", model=resolved_model)

    choice = choices[0]
    message = getattr(choice, "message", None)
    msg_dict = _message_to_dict(message)

    content = msg_dict.get("content")
    if isinstance(content, list):
        content = "".join(str(x) for x in content)
    if content is None:
        content = ""

    raw_tool_calls = msg_dict.get("tool_calls") or []
    tool_calls = [_tool_call_to_dict(tc) for tc in raw_tool_calls]

    usage_obj = getattr(response, "usage", None)
    if hasattr(usage_obj, "model_dump"):
        usage = usage_obj.model_dump()
    elif isinstance(usage_obj, dict):
        usage = dict(usage_obj)
    else:
        usage = {}
    if not isinstance(usage, dict):
        usage = {}

    return ChatCompletionResult(
        content=str(content),
        tool_calls=tool_calls,
        reasoning_content=msg_dict.get("reasoning_content"),
        finish_reason=getattr(choice, "finish_reason", None),
        usage=usage,
        model=getattr(response, "model", resolved_model) or resolved_model,
        raw_message=msg_dict,
    )


def _sanitize_messages_for_model(messages: list[dict[str, Any]], model: str) -> list[dict[str, Any]]:
    """
    Normalize messages and remove unsupported fields for non-reasoning models.
    """
    capabilities = infer_model_capabilities(model)
    supports_reasoning = capabilities.get("supports_reasoning", False)

    clean: list[dict[str, Any]] = []
    for msg in messages:
        copy_msg = dict(msg)
        if not supports_reasoning:
            copy_msg.pop("reasoning_content", None)
        clean.append(copy_msg)
    return clean


def _build_kwargs(
    model: str,
    messages: list[dict[str, Any]],
    temperature: float | None,
    max_tokens: int | None,
    *,
    stream: bool = False,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the kwargs dict for litellm.acompletion."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": _sanitize_messages_for_model(messages, model),
        "stream": stream,
    }

    capabilities = infer_model_capabilities(model)
    if temperature is not None and capabilities.get("supports_temperature", True):
        kwargs["temperature"] = temperature

    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if tools is not None:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    if extra_body is not None:
        kwargs["extra_body"] = extra_body
    if response_format is not None:
        kwargs["response_format"] = response_format

    # For Ollama models, ensure the api_base is set
    if model.startswith("ollama/"):
        kwargs["api_base"] = settings.ollama_api_base

    # For DeepSeek models, prefer configured base URL
    if model.startswith("deepseek/") and settings.deepseek_base_url:
        kwargs["api_base"] = settings.deepseek_base_url

    return kwargs


async def chat_completion(
    messages: list[dict[str, Any]],
    model: str = "local",
    *,
    temperature: float | None = 0.7,
    max_tokens: int | None = None,
    max_retries: int = 2,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> ChatCompletionResult:
    """
    Send messages to an LLM and return normalized structured output.
    """
    resolved = settings.resolve_model(model)
    kwargs = _build_kwargs(
        resolved,
        messages,
        temperature,
        max_tokens,
        stream=False,
        tools=tools,
        tool_choice=tool_choice,
        extra_body=extra_body,
        response_format=response_format,
    )

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await litellm.acompletion(**kwargs)
            return _normalize_response(response, resolved)
        except Exception as exc:
            last_exc = exc
            safe_exc = _redact_sensitive(str(exc))
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(
                    "model_gateway.chat_completion attempt %d failed (%s), retrying in %ss...",
                    attempt + 1,
                    safe_exc,
                    wait,
                )
                await asyncio.sleep(wait)
            else:
                logger.error("model_gateway.chat_completion failed after %d attempts", max_retries + 1)

    safe_last = _redact_sensitive(str(last_exc)) if last_exc else "Unknown model error"
    raise RuntimeError(f"Model request failed: {safe_last}") from last_exc


async def chat(
    messages: list[dict[str, Any]],
    model: str = "local",
    *,
    temperature: float | None = 0.7,
    max_tokens: int | None = None,
    max_retries: int = 2,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> str:
    """
    Backward-compatible helper that returns assistant text content only.
    """
    result = await chat_completion(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=max_retries,
        tools=tools,
        tool_choice=tool_choice,
        extra_body=extra_body,
        response_format=response_format,
    )
    return result.content


async def chat_stream(
    messages: list[dict[str, Any]],
    model: str = "local",
    *,
    temperature: float | None = 0.7,
    max_tokens: int | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    extra_body: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    """
    Stream tokens from an LLM as an async generator.
    """
    resolved = settings.resolve_model(model)
    kwargs = _build_kwargs(
        resolved,
        messages,
        temperature,
        max_tokens,
        stream=True,
        tools=tools,
        tool_choice=tool_choice,
        extra_body=extra_body,
        response_format=response_format,
    )

    try:
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as exc:
        safe_exc = _redact_sensitive(str(exc))
        logger.error("model_gateway.chat_stream failed: %s", safe_exc)
        raise RuntimeError(f"Model stream failed: {safe_exc}") from exc


def try_parse_json(text: str) -> dict[str, Any] | list[Any] | None:
    """Best-effort JSON parsing helper for callers that need strict parsing."""
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, (dict, list)):
            return parsed
    except Exception:
        return None
    return None
