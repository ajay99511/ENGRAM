# PersonalAssist Project Context

## Overview
PersonalAssist is a local-first AI assistant with long-term memory, document ingestion, and a desktop UI. The backend is a FastAPI service with a LiteLLM-based model gateway. Memory combines Qdrant (vector store) and Mem0 (user-centric memory). A Tauri + React desktop app talks to the API over localhost.

## Repository Structure
- `C:\Agents\PersonalAssist\apps\api` - FastAPI backend (routes, schedulers, podcast router).
- `C:\Agents\PersonalAssist\apps\desktop` - Tauri + React desktop UI.
- `C:\Agents\PersonalAssist\packages` - Python packages (agents, memory, tools, workflows, model gateway, shared config).
- `C:\Agents\PersonalAssist\infra` - Docker Compose for Qdrant.
- `C:\Agents\PersonalAssist\storage` - Local Qdrant data volume (docker mount).
- `C:\Agents\PersonalAssist\tests` - Unit tests for tools, workflows, models, etc.

## Core Runtime Flow
- Desktop UI calls the FastAPI server at `http://127.0.0.1:8000` (override via `VITE_API_BASE_URL`).
- `/chat` and `/chat/stream` call LiteLLM through `packages.model_gateway.client`.
- `/chat/smart` adds RAG context from Mem0 + Qdrant via `packages.memory.memory_service`.
- Agent runs (`/agents/run`) use a 3-step pipeline: Planner -> Researcher -> Synthesizer (in `packages.agents.crew`).

## Data Storage
- SQLite chat history: `~/.personalassist/chat.db`.
- Qdrant vector data: `C:\Agents\PersonalAssist\storage\qdrant_data` (Docker volume).
- Qdrant snapshots for sync: `~/.personalassist/snapshots` (created hourly by background job).
- Workflow definitions: `~/.personalassist/workflows/*.json`.

## Configuration (Env Vars)
Key settings are in `.env` and `.env.example`.
- Model: `DEFAULT_LOCAL_MODEL`, `DEFAULT_REMOTE_MODEL`, `OLLAMA_API_BASE`.
- Keys: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
- Memory/Vector: `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`, `MEM0_COLLECTION`, `EMBEDDING_MODEL`.
- Budgets: `RAG_CONTEXT_CHAR_BUDGET`, `CHAT_HISTORY_MAX_MESSAGES`, `AGENT_CONTEXT_CHAR_BUDGET`.
- Server: `API_HOST`, `API_PORT`, `API_ACCESS_TOKEN`.
- Podcast: `TTS_PROVIDER`, `PODCAST_OUTPUT_DIR`, `PODCAST_QDRANT_COLLECTION`.
- Agent tools: `ENABLE_AGENT_TOOL_CALLS`, `ALLOW_EXEC_TOOLS`.
- Filesystem tools: `FS_ALLOWED_ROOTS`.

## API Surface (Key Endpoints)
- Health: `GET /health`.
- Chat: `POST /chat`, `POST /chat/stream`, `POST /chat/smart`, `POST /chat/smart/stream`.
- Chat history: `GET /chat/threads`, `GET /chat/threads/{id}`, `DELETE /chat/threads/{id}`.
- Memory: `GET /memory/health`, `POST /memory/store`, `POST /memory/query`, `GET /memory/all`, `POST /memory/forget`, `POST /memory/consolidate`.
- Ingestion: `POST /ingest` (file or directory -> Qdrant).
- Agents: `POST /agents/run`, `GET /agents/trace/{run_id}`.
- Models: `GET /models`, `GET /models/active`, `POST /models/switch`.
- Tools: `GET /tools/list`, `POST /tools/fs/read`, `/write`, `/search`, `/list`, `POST /tools/git/status`, `/log`, `/diff`, `/summary`, `POST /tools/exec`.
- Workflows: `POST /workflows/run`, `POST /workflows/save`, `GET /workflows/list`, `GET /workflows/load/{name}`.
- Context: `POST /context/report`, `GET /context/active`, `POST /context/clear`.
- Sync: `POST /sync/trigger`, `GET /sync/status`.
- Podcast: `/api/podcast/generate`, `/api/podcast/status/{id}`, `/api/podcast/status/{id}/stream`, `/api/podcast/download/{id}`.

## Agents and Tools
- Main crew: Planner -> Researcher -> Synthesizer (sequential LLM calls).
- Context injected from Mem0 and Qdrant searches.
- Optional tool planning and execution when `ENABLE_AGENT_TOOL_CALLS=true` (exec tools gated by `ALLOW_EXEC_TOOLS`).

## Background Jobs
- Daily briefing at 8:00 AM (uses the crew pipeline).
- Hourly Qdrant snapshot export for sync.

## Desktop App Pages
- Chat, Memory, Models, Agents, Ingestion, Tools, Workflows, Sync, Podcast.
- Global shortcut: Ctrl/Cmd + Space to toggle the window.

## Known Limitations (Current State)
- Backend auto-start uses system Python and `uvicorn`; packaging a bundled sidecar is not implemented.
- `/chat/stream` remains plain; smart streaming uses `/chat/smart/stream`.
- Exec tool calls are disabled for agents by default unless `ALLOW_EXEC_TOOLS=true`.

## Notes for Agents
- When responding, rely on `build_context` (Mem0 + Qdrant) for personalization.
- Use `/ingest` to index local files into Qdrant before expecting document-aware answers.
- Use `/context/report` for active IDE/terminal context injection into chat/agents.
