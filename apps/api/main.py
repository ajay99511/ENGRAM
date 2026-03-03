"""
PersonalAssist — FastAPI Backend
Routes: health, chat, memory, agents
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from packages.shared.config import settings
from packages.model_gateway.client import chat, chat_stream

# Directory containing static test pages
_STATIC_DIR = Path(__file__).parent

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App Setup ────────────────────────────────────────────────────────
app = FastAPI(
    title="PersonalAssist API",
    version="0.1.0",
    description="AI-powered personal assistant with memory & multi-model support",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response Models ────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    model: str = "local"
    temperature: float = 0.7

class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "PROFILE"
    user_id: str = "default"

class MemoryQueryRequest(BaseModel):
    query: str
    user_id: str = "default"
    k: int = Field(default=5, ge=1, le=20)


# ── Health ───────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Chat Endpoints ───────────────────────────────────────────────────

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Non-streaming chat via model gateway."""
    messages = [{"role": "user", "content": req.message}]
    try:
        response = await chat(messages, model=req.model, temperature=req.temperature)
        return {"response": response, "model_used": settings.resolve_model(req.model)}
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """SSE streaming chat via model gateway."""
    messages = [{"role": "user", "content": req.message}]

    async def generate():
        try:
            async for chunk in chat_stream(messages, model=req.model, temperature=req.temperature):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("Stream error: %s", exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/chat/smart")
async def chat_smart(req: ChatRequest):
    """
    RAG-enhanced chat — retrieves relevant memories before answering.
    Falls back to plain chat if memory layer is unavailable.
    """
    messages = [{"role": "user", "content": req.message}]
    context_prefix = ""

    # Try to build memory context (graceful degradation)
    try:
        from packages.memory.memory_service import build_context
        context = await build_context(req.message, user_id="default")
        if context:
            context_prefix = context
    except Exception as exc:
        logger.warning("Memory layer unavailable, proceeding without context: %s", exc)

    if context_prefix:
        augmented_messages = [
            {"role": "system", "content": context_prefix},
            {"role": "user", "content": req.message},
        ]
    else:
        augmented_messages = messages

    try:
        response = await chat(augmented_messages, model=req.model, temperature=req.temperature)
        return {
            "response": response,
            "model_used": settings.resolve_model(req.model),
            "memory_used": bool(context_prefix),
        }
    except Exception as exc:
        logger.error("Smart chat error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


# ── Memory Endpoints ─────────────────────────────────────────────────

@app.get("/memory/health")
async def memory_health():
    """Check Qdrant connectivity."""
    try:
        from packages.memory.qdrant_store import health_check
        result = await health_check()
        return {"status": "ok", "qdrant": "connected", "collections": result}
    except Exception as exc:
        logger.error("Qdrant health check failed: %s", exc)
        return {"status": "degraded", "qdrant": "disconnected", "error": str(exc)}


@app.post("/memory/store")
async def memory_store(req: MemoryStoreRequest):
    """Store a memory in Qdrant."""
    try:
        from packages.memory.memory_service import store_memory
        result = await store_memory(
            user_id=req.user_id,
            content=req.content,
            memory_type=req.memory_type,
        )
        return {"status": "stored", **result}
    except Exception as exc:
        logger.error("Memory store error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/memory/query")
async def memory_query(req: MemoryQueryRequest):
    """Query memories via semantic search."""
    try:
        from packages.memory.memory_service import query_memories
        results = await query_memories(
            user_id=req.user_id,
            query=req.query,
            k=req.k,
        )
        return {"results": results}
    except Exception as exc:
        logger.error("Memory query error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Agent Endpoint ───────────────────────────────────────────────────

@app.post("/agents/run")
async def agents_run(req: ChatRequest):
    """Run a simple planner agent (placeholder for CrewAI)."""
    try:
        from packages.agents.base_agent import PlannerAgent
        agent = PlannerAgent()
        result = await agent.run(context="", message=req.message)
        return {"response": result, "agent": "planner"}
    except Exception as exc:
        logger.error("Agent run error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Static Test Pages ────────────────────────────────────────────────

@app.get("/test")
async def serve_test_page():
    """Serve the original test page."""
    return FileResponse(_STATIC_DIR / "test.html")


@app.get("/prototype")
async def serve_prototype():
    """Serve the full prototype test page."""
    return FileResponse(_STATIC_DIR / "test_prototype.html")
