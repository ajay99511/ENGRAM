"""
Tests for the dynamic model registry.
"""

import pytest
from pathlib import Path
from packages.model_gateway.registry import (
    ModelInfo,
    _static_remote_models,
    get_active_model,
    set_active_model,
    _EMBEDDING_MODELS,
    infer_model_capabilities,
)
from packages.shared.config import settings


def _isolate_registry(monkeypatch, tmp_path: Path):
    import packages.model_gateway.registry as reg
    monkeypatch.setattr(reg, "_ACTIVE_MODEL_FILE", tmp_path / "active_model.json")
    reg._active_model = None
    reg._load_active_model()
    return reg


class TestStaticRemoteModels:
    """Tests for static remote model definitions."""

    def test_returns_two_remote_models(self):
        models = _static_remote_models()
        assert len(models) == 7  # 4 Gemini models + 1 Claude + 2 DeepSeek

    def test_includes_gemini(self):
        models = _static_remote_models()
        assert any(m.provider == "gemini" for m in models)

    def test_includes_anthropic(self):
        models = _static_remote_models()
        assert any(m.provider == "anthropic" for m in models)

    def test_includes_deepseek(self):
        models = _static_remote_models()
        assert any(m.provider == "deepseek" for m in models)

    def test_all_remote_models_are_not_local(self):
        models = _static_remote_models()
        assert all(not m.is_local for m in models)

    def test_capability_metadata_present(self):
        models = _static_remote_models()
        sample = models[0]
        assert hasattr(sample, "supports_tool_calls")
        assert hasattr(sample, "supports_reasoning")
        assert hasattr(sample, "supports_temperature")
        assert hasattr(sample, "requires_reasoning_echo")


class TestActiveModel:
    """Tests for active model get/set logic."""

    def test_defaults_to_config(self, monkeypatch, tmp_path):
        _isolate_registry(monkeypatch, tmp_path)
        active = get_active_model()
        assert active == settings.default_local_model

    def test_set_and_get(self, monkeypatch, tmp_path):
        _isolate_registry(monkeypatch, tmp_path)
        set_active_model("ollama/codellama:latest")
        assert get_active_model() == "ollama/codellama:latest"
        # Reset
        import packages.model_gateway.registry as reg
        reg._active_model = None

    def test_static_models_reflect_active(self, monkeypatch, tmp_path):
        _isolate_registry(monkeypatch, tmp_path)
        set_active_model("anthropic/claude-sonnet-4-20250514")
        models = _static_remote_models()
        claude = next(m for m in models if m.provider == "anthropic")
        assert claude.is_active is True
        # Reset
        import packages.model_gateway.registry as reg
        reg._active_model = None


class TestResolveModelIntegration:
    """Tests for config.resolve_model with active model support."""

    def test_resolve_local(self):
        assert settings.resolve_model("local") == settings.default_local_model

    def test_resolve_gemini(self):
        # We explicitly resolve 'gemini' to 'gemini/gemini-2.5-flash-lite'
        assert settings.resolve_model("gemini") == "gemini/gemini-2.5-flash-lite"

    def test_resolve_active_uses_registry(self):
        set_active_model("ollama/mistral:latest")
        result = settings.resolve_model("active")
        assert result == "ollama/mistral:latest"
        # Reset
        import packages.model_gateway.registry as reg
        reg._active_model = None

    def test_resolve_passthrough(self):
        assert settings.resolve_model("ollama/phi3.5:latest") == "ollama/phi3.5:latest"

    def test_resolve_deepseek_aliases(self):
        assert settings.resolve_model("deepseek") == "deepseek/deepseek-chat"
        assert settings.resolve_model("deepseek-chat") == "deepseek/deepseek-chat"
        assert settings.resolve_model("deepseek-reasoner") == "deepseek/deepseek-reasoner"


class TestEmbeddingClassification:
    """Tests for embedding model detection."""

    def test_known_embedding_models(self):
        assert "nomic-embed-text" in _EMBEDDING_MODELS
        assert "all-minilm" in _EMBEDDING_MODELS

    def test_chat_models_not_classified_as_embedding(self):
        assert "llama3.2" not in _EMBEDDING_MODELS
        assert "codellama" not in _EMBEDDING_MODELS
        assert "mistral" not in _EMBEDDING_MODELS


class TestCapabilityInference:
    def test_reasoner_capabilities(self):
        caps = infer_model_capabilities("deepseek-reasoner")
        assert caps["supports_reasoning"] is True
        assert caps["supports_tool_calls"] is True
        assert caps["supports_temperature"] is False
        assert caps["requires_reasoning_echo"] is True

    def test_local_defaults(self):
        caps = infer_model_capabilities("local")
        assert caps["supports_tool_calls"] is False
