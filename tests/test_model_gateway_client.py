import pytest

import packages.model_gateway.client as client_module


class _Fn:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, call_id: str, name: str, arguments: str):
        self.id = call_id
        self.type = "function"
        self.function = _Fn(name, arguments)


class _Message:
    def __init__(self, content: str, tool_calls=None, reasoning_content=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.reasoning_content = reasoning_content


class _Choice:
    def __init__(self, message):
        self.message = message
        self.finish_reason = "stop"


class _Usage:
    def model_dump(self):
        return {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


class _Response:
    def __init__(self, message):
        self.choices = [_Choice(message)]
        self.usage = _Usage()
        self.model = "mock-model"


@pytest.mark.asyncio
async def test_chat_completion_parses_tool_calls(monkeypatch):
    async def fake_completion(**kwargs):
        msg = _Message(
            content="",
            tool_calls=[_ToolCall("c1", "search_documents", '{"query":"test","k":3}')],
            reasoning_content="thinking",
        )
        return _Response(msg)

    monkeypatch.setattr(client_module.litellm, "acompletion", fake_completion)

    result = await client_module.chat_completion(
        [{"role": "user", "content": "Find docs"}],
        model="gemini",
        tools=[{"type": "function", "function": {"name": "search_documents"}}],
    )
    assert result.tool_calls
    assert result.tool_calls[0]["function"]["name"] == "search_documents"
    assert result.reasoning_content == "thinking"


@pytest.mark.asyncio
async def test_chat_wrapper_returns_content(monkeypatch):
    async def fake_completion(**kwargs):
        return _Response(_Message(content="hello"))

    monkeypatch.setattr(client_module.litellm, "acompletion", fake_completion)

    text = await client_module.chat([{"role": "user", "content": "hi"}], model="gemini")
    assert text == "hello"


@pytest.mark.asyncio
async def test_reasoner_filters_temperature(monkeypatch):
    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return _Response(_Message(content="ok"))

    monkeypatch.setattr(client_module.litellm, "acompletion", fake_completion)

    await client_module.chat_completion(
        [{"role": "user", "content": "reason"}],
        model="deepseek-reasoner",
        temperature=0.2,
    )
    assert "temperature" not in captured
