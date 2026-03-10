"""
Centralized configuration for PersonalAssist.
All settings are loaded from environment variables via .env file.
"""

import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Data Directory ---
    data_dir: str = Field(
        default=os.path.expanduser("~/.personalassist"),
        alias="DATA_DIR",
        description="Unified directory for all app data, snapshots, and workflows",
    )

    # --- Model Configuration ---
    default_local_model: str = Field(
        default="ollama/llama3.2",
        alias="DEFAULT_LOCAL_MODEL",
        description="LiteLLM model identifier for local Ollama inference",
    )
    default_remote_model: str = Field(
        default="gemini/gemini-2.5-flash-lite",
        alias="DEFAULT_REMOTE_MODEL",
        description="LiteLLM model identifier for remote inference",
    )

    # --- API Keys / Access Control ---
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    api_access_token: str = Field(
        default="",
        alias="API_ACCESS_TOKEN",
        description="Optional shared token for local desktop-to-API requests",
    )

    # --- Ollama ---
    ollama_api_base: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_API_BASE",
    )

    # --- Qdrant ---
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_collection: str = Field(
        default="personal_memories", alias="QDRANT_COLLECTION"
    )

    # --- Mem0 ---
    mem0_collection: str = Field(
        default="mem0_memories",
        alias="MEM0_COLLECTION",
        description="Qdrant collection name for Mem0 memories",
    )

    # --- Learning Loop ---
    consolidation_threshold: int = Field(
        default=20,
        alias="CONSOLIDATION_THRESHOLD",
        description="Auto-consolidate memories every N conversation turns",
    )

    # --- Embedding ---
    embedding_model: str = Field(
        default="nomic-embed-text",
        alias="EMBEDDING_MODEL",
        description="Ollama embedding model for vector generation",
    )

    # --- Prompt / Context Budgets ---
    rag_context_char_budget: int = Field(
        default=3200,
        alias="RAG_CONTEXT_CHAR_BUDGET",
        description="Maximum characters returned by hybrid memory/document context assembly",
    )
    rag_doc_snippet_chars: int = Field(
        default=500,
        alias="RAG_DOC_SNIPPET_CHARS",
        description="Maximum characters per document snippet included in RAG context",
    )
    rag_memory_limit: int = Field(
        default=4,
        alias="RAG_MEMORY_LIMIT",
        description="Maximum number of memory facts included in assembled context",
    )
    chat_history_max_messages: int = Field(
        default=10,
        alias="CHAT_HISTORY_MAX_MESSAGES",
        description="Maximum recent thread messages sent back to the model",
    )
    chat_history_char_budget: int = Field(
        default=6000,
        alias="CHAT_HISTORY_CHAR_BUDGET",
        description="Maximum combined characters from recent thread history",
    )
    agent_context_char_budget: int = Field(
        default=4000,
        alias="AGENT_CONTEXT_CHAR_BUDGET",
        description="Maximum characters of retrieved context passed into agent stages",
    )
    workflow_context_char_budget: int = Field(
        default=2500,
        alias="WORKFLOW_CONTEXT_CHAR_BUDGET",
        description="Maximum serialized workflow context passed between nodes",
    )

    # --- Podcast Agent ---
    podcast_output_dir: str = Field(
        default="~/Downloads",
        alias="PODCAST_OUTPUT_DIR",
        description="Directory to save generated podcast MP3 files",
    )
    tts_provider: str = Field(
        default="edge-tts",
        alias="TTS_PROVIDER",
        description="TTS engine: 'edge-tts' (free) or 'elevenlabs' (premium)",
    )
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(
        default="21m00Tcm4TlvDq8ikWAM",
        alias="ELEVENLABS_VOICE_ID",
        description="ElevenLabs voice ID (default: Rachel)",
    )
    podcast_qdrant_collection: str = Field(
        default="podcast_research",
        alias="PODCAST_QDRANT_COLLECTION",
        description="Separate Qdrant collection for podcast research data",
    )
    podcast_max_duration: int = Field(
        default=120,
        alias="PODCAST_MAX_DURATION",
        description="Hard cap on podcast duration in minutes",
    )

    # --- Server ---
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    def resolve_model(self, model_key: str) -> str:
        """
        Resolve a model key to a LiteLLM model string.

        Priority: short alias -> runtime active model -> raw model string.
        """
        model_map = {
            "local": self.default_local_model,
            "gemini": "gemini/gemini-2.5-flash-lite",
            "gemini-lite": "gemini/gemini-2.5-flash-lite",
            "gemini-flash": "gemini/gemini-2.5-flash",
            "gemini-pro": "gemini/gemini-2.5-pro",
            "claude": "anthropic/claude-sonnet-4-20250514",
        }
        if model_key in model_map:
            return model_map[model_key]

        if model_key == "active":
            try:
                from packages.model_gateway.registry import get_active_model

                return get_active_model()
            except ImportError:
                return self.default_local_model

        return model_key


settings = Settings()
