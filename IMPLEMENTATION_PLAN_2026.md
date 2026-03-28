# PersonalAssist 2026: Production-Grade Implementation Plan

**Document Purpose:** Comprehensive, user-centric roadmap to elevate PersonalAssist into the top 1% of local AI assistants.

**Vision:** A personal agentic system that is fully attached to the user perspective, works seamlessly with user data and projects, and leverages both local (Ollama) and cloud AI models efficiently.

**Date:** March 26, 2026  
**Status:** Ready for Implementation

---

## 📊 **EXECUTIVE SUMMARY: CURRENT STATE ASSESSMENT**

### **What You Already Have RIGHT (85% Production-Ready)** ✅

| Component | Your Implementation | Industry Benchmark | Verdict |
|-----------|-------------------|-------------------|---------|
| **Backend Architecture** | FastAPI + LiteLLM | ✅ Matches best practices | **KEEP** |
| **Memory Foundation** | Qdrant + Mem0 (local Ollama) | ✅ Industry-standard vector + user memory | **KEEP + ENHANCE** |
| **Agent Orchestration** | CrewAI (Planner→Researcher→Synthesizer) | ✅ Role-based multi-agent pattern | **KEEP + ADOPT PI PATTERNS** |
| **Desktop App** | Tauri v2 + React + TypeScript | ✅ Modern, efficient, secure | **KEEP + POLISH** |
| **Chat Interface** | Full-featured with streaming, threads, smart mode | ✅ Production-ready UX | **KEEP** |
| **Model Gateway** | Unified interface (Ollama + Cloud) | ✅ Future-proof abstraction | **KEEP** |
| **RAG System** | Hybrid (Mem0 facts + Qdrant docs) | ✅ Correct dual-layer approach | **ENHANCE** |
| **Context Management** | Active context (IDE/Terminal) injection | ✅ Key differentiator | **KEEP + EXPAND** |

### **Critical Gaps (15% Missing)** ⚠️

| Gap | Current State | Target State | Business Impact |
|-----|--------------|--------------|-----------------|
| **Background Task System** | APScheduler (volatile, no retry) | ARQ + Redis (persistent, retry) | 🔴 **CRITICAL** - Jobs lost on restart |
| **5-Layer Memory** | Basic (Mem0 + Qdrant only) | OpenClaw 5-layer (Bootstrap+JSONL+Prune+Compact+LTM) | 🟡 **HIGH** - No 6-month retention |
| **Workspace Isolation** | Path allowlists only | Docker sandboxing + permission policies | 🟡 **HIGH** - Security risk for code agents |
| **Tool Policy System** | Global flags only | Per-agent allow/deny + audit logging | 🟡 **HIGH** - No fine-grained control |
| **Messaging Integration** | None | Telegram → Multi-channel | 🟢 **MEDIUM** - Limited accessibility |
| **Context Engine** | Basic RAG | Adaptive compaction + session pruning | 🟢 **MEDIUM** - Token inefficiency |
| **Desktop Polish** | Basic React | TanStack Query + agent trace visualization | 🟢 **MEDIUM** - UX gaps |

---

## 🎯 **DESIGN PRINCIPLES (USER-CENTRIC)**

### **1. User Data Sovereignty**
- **Local-first:** All sensitive data stays on user's machine
- **User controls:** Inspect, delete, export memories anytime
- **No vendor lock-in:** Models are swappable via config

### **2. Project-Aware Intelligence**
- **Workspace isolation:** Each project has dedicated context
- **Permission-based access:** User configures what agents can do
- **Audit trail:** All agent actions logged for transparency

### **3. Model Agnosticism**
- **Local-first routing:** Ollama by default, cloud for heavy tasks
- **Seamless fallback:** Auto-switch when local model unavailable
- **Cost optimization:** Route simple tasks to cheap models

### **4. Memory Richness (6+ Month Retention)**
- **Multi-layer storage:** Hot (recent), warm (summarized), cold (archived)
- **Temporal awareness:** Recent memories weighted higher
- **Deduplication:** Merge similar memories automatically

### **5. Always-Available Assistance**
- **Background tasks:** Proactive monitoring and summaries
- **Messaging integration:** Chat via Telegram (expandable)
- **Resilient execution:** Jobs survive restarts with retry logic

---

## 🏗️ **TARGET ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERSONAL ASSISTANT 2026 ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     DESKTOP UI (Tauri v2 + React)                │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │  │   Chat   │ │  Memory  │ │  Agents  │ │  Projects│            │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │  │
│  │  - TanStack Query (state management)                             │  │
│  │  - SSE streaming (agent traces)                                  │  │
│  │  - Global shortcut (Ctrl+Space)                                  │  │
│  └──────────────────────────┬───────────────────────────────────────┘  │
│                             │ HTTP + SSE                               │
│  ┌──────────────────────────▼───────────────────────────────────────┐  │
│  │                    FASTAPI BACKEND (Python)                       │  │
│  │                                                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  API LAYER                                                  │  │  │
│  │  │  - /chat/* (plain, stream, smart)                          │  │  │
│  │  │  - /agents/* (run, trace)                                  │  │  │
│  │  │  - /memory/* (store, query, consolidate)                   │  │  │
│  │  │  - /projects/* (workspace management) ← NEW                │  │  │
│  │  │  - /jobs/* (background task monitoring) ← NEW              │  │  │
│  │  │  - /telegram/* (messaging webhook) ← NEW                   │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  AGENT RUNTIME (CrewAI + Enhanced)                         │  │  │
│  │  │  - Planner → Researcher → Synthesizer                      │  │  │
│  │  │  - Tool loop (native + legacy fallback)                    │  │  │
│  │  │  - Hooks system (before_model_resolve, before_tool_call)   │  │  │
│  │  │  - Context engine (adaptive pruning) ← NEW                 │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  MEMORY SYSTEM (5-Layer) ← ENHANCED                        │  │  │
│  │  │  Layer 1: Bootstrap (AGENTS.md, SOUL.md, USER.md, etc.)    │  │  │
│  │  │  Layer 2: JSONL Transcripts (per session)                  │  │  │
│  │  │  Layer 3: Session Pruning (in-memory, TTL-aware)           │  │  │
│  │  │  Layer 4: Compaction (adaptive summarization)              │  │  │
│  │  │  Layer 5: LTM Search (Mem0 + Qdrant hybrid)                │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  WORKSPACE MANAGER ← NEW                                   │  │  │
│  │  │  - Project configs (~/.personalassist/workspaces/*.json)   │  │  │
│  │  │  - Permission enforcement (read/write/execute)             │  │  │
│  │  │  - Docker sandboxing (optional, per-project)               │  │  │
│  │  │  - Audit logging (.agent_audit.log)                        │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  BACKGROUND TASKS (ARQ + Redis) ← NEW                      │  │  │
│  │  │  - Persistent job queue (survives restarts)                │  │  │
│  │  │  - Retry logic (exponential backoff)                       │  │  │
│  │  │  - Priority queues (urgent vs routine)                     │  │  │
│  │  │  - Isolated sessions (token-efficient)                     │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  MESSAGING GATEWAY ← NEW                                   │  │  │
│  │  │  - Telegram adapter (python-telegram-bot)                  │  │  │
│  │  │  - Common envelope (normalize all channels)                │  │  │
│  │  │  - Auth (Telegram ID → user_id)                            │  │  │
│  │  │  - DM policy (pairing/allowlist/open)                      │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  MODEL GATEWAY (LiteLLM)                                   │  │  │
│  │  │  - Local: Ollama (llama3.2, mistral, etc.)                 │  │  │
│  │  │  - Cloud: Gemini, Claude, DeepSeek                         │  │  │
│  │  │  - Smart routing (local-first, cloud fallback)             │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────┬───────────────────────────────────────┘  │
│                             │                                           │
│  ┌──────────────────────────▼───────────────────────────────────────┐  │
│  │                    DATA LAYER                                     │  │
│  │                                                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  │
│  │  │   SQLite     │  │   Qdrant     │  │    Redis     │           │  │
│  │  │  (threads,   │  │  (vectors,   │  │  (job queue, │           │  │
│  │  │   metadata)  │  │   RAG)       │  │   cache)     │           │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │  │
│  │                                                                   │  │
│  │  ┌──────────────────────────────────────────────────────────┐    │  │
│  │  │  File System (~/.personalassist/)                        │    │  │
│  │  │    - sessions/*.jsonl (transcripts)                      │    │  │
│  │  │    - memory/YYYY-MM-DD.md (daily logs)                   │    │  │
│  │  │    - MEMORY.md (curated long-term)                       │    │  │
│  │  │    - workspaces/*.json (project configs)                 │    │  │
│  │  │    - snapshots/ (Qdrant backups)                         │    │  │
│  │  │    - sandboxes/ (Docker volumes)                         │    │  │
│  │  │    - logs/ (audit logs)                                  │    │  │
│  │  └──────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    EXTERNAL INTEGRATIONS                         │  │
│  │                                                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  │
│  │  │   Telegram   │  │   Ollama     │  │  Cloud APIs  │           │  │
│  │  │   (Phase 3)  │  │  (local LLM) │  │  (Gemini,    │           │  │
│  │  │              │  │              │  │   Claude)    │           │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 **IMPLEMENTATION PHASES (12-WEEK ROADMAP)**

### **PHASE 0: INFRASTRUCTURE PREPARATION** ⏱️ 1-2 days

**Goal:** Add Redis for background tasks, prepare directory structure.

**Tasks:**

1. **Update Docker Compose** (`infra/docker-compose.yml`):
   - Add Redis service with persistence
   - Configure health checks
   - Map volumes for data persistence

2. **Update Dependencies** (`requirements.txt`):
   ```txt
   # Background Tasks
   arq>=0.25.0
   redis>=5.0.0
   
   # Messaging (Phase 3)
   python-telegram-bot>=20.0
   
   # Sandboxing (Phase 2)
   docker>=7.0.0
   ```

3. **Create Directory Structure**:
   ```bash
   mkdir -p ~/.personalassist/{sessions,memory,workspaces,sandboxes,logs}
   ```

4. **Create Bootstrap Templates**:
   - `AGENTS.md` - Operating instructions
   - `SOUL.md` - Persona and tone
   - `USER.md` - User preferences
   - `IDENTITY.md` - Agent identity
   - `TOOLS.md` - Tool capabilities
   - `HEARTBEAT.md` - Background task checklist

**Deliverables:**
- ✅ Redis running in Docker
- ✅ Directory structure created
- ✅ Bootstrap templates in place

---

### **PHASE 1: 5-LAYER MEMORY SYSTEM** ⏱️ 7-10 days 🔴 **CRITICAL**

**Goal:** Implement OpenClaw's memory architecture for 6+ month retention.

**Why First:** Without this, your system cannot retain important context long-term. This is the foundation for user-centric intelligence.

#### **Day 1-2: Layer 1 (Bootstrap Injection)**

**Files to Create:**
- `packages/memory/bootstrap.py` - Bootstrap file manager

**Key Features:**
- Read bootstrap files from `~/.personalassist/`
- Inject into system prompt (cap: 150K chars total)
- Sub-agents get only AGENTS.md + TOOLS.md
- Graceful truncation with marker

**Integration:**
- Modify `packages/agents/crew.py` to call bootstrap manager
- Add bootstrap files to system prompt assembly

#### **Day 3-5: Layer 2 (JSONL Transcripts)**

**Files to Create:**
- `packages/memory/jsonl_store.py` - JSONL transcript manager
- `packages/memory/session_manager.py` - Session lifecycle manager

**Key Features:**
- Append-only JSONL files (`~/.personalassist/sessions/<thread_id>.jsonl`)
- Tree structure (entries have `id` + `parentId` for branching)
- Entry types: `message`, `compaction`, `session_info`
- Daily reset: 4 AM local time (configurable)
- Dual-write: SQLite (indexing) + JSONL (fast append)

**Migration Strategy:**
- Keep existing SQLite threads
- New threads use JSONL + SQLite
- Gradual migration via background job

#### **Day 6-7: Layer 3 (Session Pruning)**

**Files to Create:**
- `packages/memory/pruning.py` - In-memory session pruning

**Key Features:**
- Trim old tool results BEFORE each LLM call
- Does NOT rewrite JSONL files
- TTL-based (default 5 min since last call)
- Protects last 3 assistant messages
- Soft-trim (keeps head + tail, inserts "...")

**Integration:**
- Modify context assembly in `packages/memory/memory_service.py`
- Add pruning step before sending to LLM

#### **Day 8-10: Layer 4 (Compaction)**

**Files to Create:**
- `packages/memory/compaction.py` - Adaptive compaction engine

**Key Features:**
- Triggered when: `contextTokens > contextWindow - 4K reserve`
- Adaptive chunk ratio (0.15-0.40 based on avg message size)
- Multi-stage summarization with fallback
- Pre-compaction memory flush (silent turn to write MEMORY.md)
- Surgical JSONL rewrite (atomic temp + rename)

**Algorithm:**
```python
def compact_session(session_id: str) -> CompactionResult:
    # 1. Compute adaptive chunk ratio
    ratio = compute_adaptive_chunk_ratio(avg_message_tokens)
    
    # 2. Chunk messages with 1.2× safety margin
    chunks = chunk_messages_by_max_tokens(
        messages, 
        max_tokens=context_window * ratio,
        safety_margin=1.2
    )
    
    # 3. Summarize with fallback
    summary = summarize_with_fallback(chunks)
    
    # 4. Preserve identifiers (UUIDs, IPs, URLs, file names)
    summary = preserve_identifiers(summary, messages)
    
    # 5. Truncate JSONL (atomic write)
    truncate_session_after_compaction(session_id, summary)
    
    return CompactionResult(summary=summary, entries_removed=len(chunks))
```

**Deliverables:**
- ✅ 5-layer memory system fully implemented
- ✅ Migration path from old to new system
- ✅ Memory flush before compaction
- ✅ Adaptive summarization with fallback

---

### **PHASE 2: WORKSPACE ISOLATION** ⏱️ 5-7 days 🟡 **HIGH**

**Goal:** Docker sandboxing for code agents with permission-based access.

**Why Important:** Users need to trust agents with their code. Sandboxing provides security + audit trail.

#### **Day 1-2: Workspace Configuration**

**Files to Create:**
- `packages/agents/workspace.py` - Workspace configuration manager
- `packages/agents/schemas.py` - Pydantic models for workspace configs

**Configuration Schema:**
```json
{
  "project_id": "my-project",
  "root": "C:\\Agents\\PersonalAssist",
  "sandbox_mode": "docker",
  "scope": "session",
  "permissions": {
    "read": ["src/**/*", "tests/**/*"],
    "write": ["src/**/*"],
    "execute": false,
    "git_operations": true,
    "network_access": false
  },
  "context_collection": "project_myproject",
  "agent_instructions": "Focus on code quality, add tests for new code"
}
```

**Features:**
- Glob-based permissions (read, write, execute)
- Per-project Qdrant collections
- Agent-specific instructions injected into prompts

#### **Day 3-4: Docker Sandbox Manager**

**Files to Create:**
- `packages/agents/sandbox.py` - Docker sandbox orchestrator

**Key Features:**
- Container creation with scoped volumes
- Network isolation (blocked by default)
- Dangerous bind blocking (docker.sock, /etc, /proc, /sys, /dev)
- Setup command runs once on container creation
- Timeout enforcement per command

**Security Model:**
```python
class DockerSandbox:
    async def create(self, config: WorkspaceConfig) -> SandboxSession:
        container_config = {
            "image": "personalassist-sandbox:latest",
            "volumes": {
                config.root: {"bind": "/workspace", "mode": "ro" if ... else "rw"},
                str(self.sandbox_base): {"bind": "/sandbox", "mode": "ro"},
            },
            "network_disabled": True,  # No network by default
            "cap_drop": ["ALL"],  # Drop all capabilities
        }
        
        # Block dangerous binds
        dangerous_binds = ["/var/run/docker.sock", "/etc", "/proc", "/sys", "/dev"]
        for bind in dangerous_binds:
            if bind in container_config["volumes"]:
                raise SecurityError(f"Dangerous bind blocked: {bind}")
        
        container = await docker.containers.run(**container_config)
        return SandboxSession(container=container, config=config)
```

#### **Day 5-7: Tool Policy Enforcement**

**Files to Create:**
- `packages/agents/tool_policy.py` - Tool policy engine
- `packages/agents/audit.py` - Audit logging

**Policy Schema:**
```json
{
  "agents": {
    "list": [{
      "id": "code-reviewer",
      "tools": {
        "allow": ["read", "git_status", "exec"],
        "deny": ["write", "edit", "exec_mutating"]
      }
    }]
  }
}
```

**Features:**
- Wildcards supported (`read*`, `exec*`)
- Deny wins over allow
- Case-insensitive matching
- Applied BEFORE sandbox rules
- Audit log for every tool call

**Deliverables:**
- ✅ Workspace configuration system
- ✅ Docker sandboxing (optional per-project)
- ✅ Tool policy enforcement
- ✅ Audit logging

---

### **PHASE 3: BACKGROUND TASKS (ARQ + Redis)** ⏱️ 4-5 days 🔴 **CRITICAL**

**Goal:** Migrate from APScheduler to ARQ for production-grade reliability.

**Why Critical:** Current system loses jobs on restart. This blocks reliable automation.

#### **Day 1-2: ARQ Worker Setup**

**Files to Create:**
- `packages/automation/arq_worker.py` - ARQ worker definitions
- `packages/automation/settings.py` - ARQ configuration

**Worker Configuration:**
```python
# packages/automation/arq_worker.py

from arq import cron
from packages.automation.jobs import run_daily_briefing, run_hourly_snapshot

class WorkerSettings:
    functions = [run_daily_briefing, run_hourly_snapshot]
    
    cron_jobs = [
        cron(run_daily_briefing, hour=8, minute=0),  # 8:00 AM daily
        cron(run_hourly_snapshot, minute=0),  # Every hour
    ]
    
    redis_settings = {
        "host": "localhost",
        "port": 6379,
        "db": 0,
    }
    
    max_jobs = 10  # Max concurrent jobs
    job_timeout = 300  # 5 minutes default
    retry_delay = 60  # 1 minute before first retry
    retry_delay_steps = [60, 120, 300, 900, 3600]  # Exponential backoff
```

#### **Day 3-4: Job Definitions**

**Files to Create:**
- `packages/automation/jobs.py` - Job definitions (migrate from APScheduler)
- `packages/automation/models.py` - Job status models

**Job Examples:**
```python
# packages/automation/jobs.py

from arq.ctx import redis
from packages.agents.crew import run_crew
from packages.memory.qdrant_store import export_snapshot

async def run_daily_briefing(ctx):
    """
    Proactive agent that generates morning summary.
    """
    job_id = ctx["job_id"]
    
    # Use isolated session (token-efficient)
    result = await run_crew(
        user_message="Generate a morning briefing of recent activity.",
        user_id="default",
        model="local",
        session_type="isolated",  # NEW: isolated session
        session_id=f"daily_briefing:{job_id}",
    )
    
    # Store result in Redis for monitoring
    await redis.hset(f"job:{job_id}", mapping={
        "status": "completed",
        "result": result["response"],
        "completed_at": datetime.now().isoformat(),
    })
    
    return result

async def run_hourly_snapshot(ctx):
    """
    Export Qdrant snapshot for backup.
    """
    await export_snapshot()
```

#### **Day 5: API Endpoints**

**Files to Modify:**
- `apps/api/main.py` - Add job monitoring endpoints

**New Endpoints:**
```python
@app.get("/jobs/status/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a background job."""
    status = await redis.hgetall(f"job:{job_id}")
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@app.get("/jobs/list")
async def list_jobs():
    """List all background jobs."""
    job_keys = await redis.keys("job:*")
    jobs = []
    for key in job_keys:
        status = await redis.hgetall(key)
        jobs.append(status)
    return {"jobs": jobs}

@app.post("/jobs/submit")
async def submit_job(req: JobSubmitRequest):
    """Submit a new background job."""
    job_id = str(uuid.uuid4())
    await redis.enqueue_job(req.job_type, job_id=job_id, **req.params)
    return {"job_id": job_id, "status": "queued"}
```

**Deliverables:**
- ✅ ARQ workers running
- ✅ Jobs persist in Redis (survive restarts)
- ✅ Retry with exponential backoff
- ✅ Job monitoring API

---

### **PHASE 4: TELEGRAM MESSAGING GATEWAY** ⏱️ 4-6 days 🟢 **MEDIUM**

**Goal:** Enable chat with agents via Telegram.

**Why Important:** Users want to access their AI assistant on-the-go.

#### **Day 1-2: Telegram Bot Service**

**Files to Create:**
- `packages/messaging/__init__.py`
- `packages/messaging/telegram_bot.py` - Telegram bot service
- `packages/messaging/config.py` - Messaging configuration

**Bot Service:**
```python
# packages/messaging/telegram_bot.py

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from packages.messaging.router import MessageRouter

class TelegramBotService:
    def __init__(self, token: str, api_base: str):
        self.application = Application.builder().token(token).build()
        self.router = MessageRouter(api_base=api_base)
        
        # Register handlers
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming Telegram message."""
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        # Auth check (Telegram ID → user_id mapping)
        if not await self.is_authorized(user_id):
            await update.message.reply_text(
                "🔐 You need to be authorized to use this bot. "
                "Please contact the administrator."
            )
            return
        
        # Route to agent
        response = await self.router.route(
            channel="telegram",
            sender_id=user_id,
            message=message_text,
        )
        
        # Send response (chunk if long)
        await self.send_chunked_response(update, response)
    
    async def send_chunked_response(self, update: Update, text: str):
        """Send long responses as multiple messages."""
        max_length = 4096  # Telegram message limit
        
        if len(text) <= max_length:
            await update.message.reply_text(text)
            return
        
        # Split into chunks
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for chunk in chunks:
            await update.message.reply_text(chunk)
            await asyncio.sleep(0.5)  # Avoid rate limiting
    
    async def start(self):
        """Start the Telegram bot."""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
```

#### **Day 3-4: Message Router**

**Files to Create:**
- `packages/messaging/router.py` - Message router
- `packages/messaging/models.py` - Common envelope models

**Common Envelope:**
```python
# packages/messaging/models.py

from pydantic import BaseModel
from typing import Literal, Optional

class Sender(BaseModel):
    id: str
    name: Optional[str] = None
    is_bot: bool = False

class Peer(BaseModel):
    kind: Literal["direct", "group", "channel"]
    id: str
    name: Optional[str] = None

class MessageContent(BaseModel):
    text: str
    attachments: list[str] = []
    reply_to: Optional[str] = None

class CommonEnvelope(BaseModel):
    """Normalized message format across all channels."""
    id: str
    channel: Literal["telegram", "discord", "slack", "whatsapp"]
    sender: Sender
    peer: Peer
    content: MessageContent
    timestamp: str

class RoutingResult(BaseModel):
    success: bool
    response: str
    error: Optional[str] = None
```

**Router:**
```python
# packages/messaging/router.py

class MessageRouter:
    def __init__(self, api_base: str):
        self.api_base = api_base
        self.auth_store = UserAuthStore()  # Telegram ID → user_id mapping
    
    async def route(
        self,
        channel: str,
        sender_id: str,
        message: str,
    ) -> str:
        """Route message to appropriate agent/session."""
        
        # 1. Auth check
        user_id = await self.auth_store.get_user_id(channel, sender_id)
        if not user_id:
            return "🔐 Unauthorized. Please contact administrator."
        
        # 2. DM policy check
        policy = await self.get_dm_policy(channel, sender_id)
        if policy == "pairing" and not await self.is_paired(channel, sender_id):
            code = await self.generate_approval_code(channel, sender_id)
            return f"🔐 Approval required. Use code: {code}"
        
        # 3. Rate limiting
        if await self.is_rate_limited(sender_id):
            return "⏳ Rate limit exceeded. Please wait a moment."
        
        # 4. Route to agent
        response = await self.call_agent_api(user_id, message)
        
        return response
```

#### **Day 5-6: Integration & Testing**

**Files to Modify:**
- `apps/api/main.py` - Add Telegram webhook endpoint
- `.env.example` - Add Telegram bot token config

**Webhook Endpoint:**
```python
# apps/api/main.py

from packages.messaging.telegram_bot import TelegramBotService

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook for incoming messages."""
    data = await request.json()
    update = Update.de_json(data, bot=telegram_bot.bot)
    
    # Process asynchronously (don't block webhook response)
    asyncio.create_task(
        telegram_bot.application.process_update(update)
    )
    
    return {"status": "ok"}
```

**Deliverables:**
- ✅ Telegram bot running
- ✅ Message routing to agents
- ✅ Auth system (Telegram ID → user_id)
- ✅ DM policy enforcement

---

### **PHASE 5: CONTEXT ENGINE OPTIMIZATION** ⏱️ 5-7 days 🟢 **MEDIUM**

**Goal:** Adopt OpenClaw's context management for efficiency.

#### **Day 1-3: Adaptive Context Window**

**Files to Create:**
- `packages/memory/context_engine.py` - Context assembly engine
- `packages/memory/token_budget.py` - Token budget management

**Context Engine:**
```python
# packages/memory/context_engine.py

class ContextEngine:
    def __init__(self, session_id: str, token_budget: int):
        self.session_id = session_id
        self.token_budget = token_budget
    
    async def assemble(self) -> ContextResult:
        """Assemble context for LLM call."""
        
        # 1. Limit history turns (cheap pruning)
        messages = await self.limit_history_turns(max_turns=20)
        
        # 2. Resolve context window info
        window_info = self.resolve_context_window_info()
        
        # 3. Session pruning (in-memory, TTL-aware)
        messages = self.prune_old_tool_results(
            messages,
            ttl_seconds=300,  # 5 minutes
            protect_last_n=3,
        )
        
        # 4. Transcript hygiene (provider-specific fixups)
        messages = self.apply_transcript_hygiene(messages)
        
        # 5. Memory search (inject relevant memories)
        memories = await self.search_memories()
        if memories:
            messages = self.inject_memories(messages, memories)
        
        # 6. Estimate tokens
        estimated_tokens = self.estimate_tokens(messages)
        
        return ContextResult(
            messages=messages,
            estimated_tokens=estimated_tokens,
            window_info=window_info,
        )
```

**Token Budget Management:**
```python
# packages/memory/token_budget.py

def compute_adaptive_chunk_ratio(avg_message_tokens: int) -> float:
    """
    Compute adaptive chunk ratio based on average message size.
    
    BASE=0.4, MIN=0.15
    Reduces chunk ratio when avg message > 10% of context.
    """
    BASE_RATIO = 0.4
    MIN_RATIO = 0.15
    
    if avg_message_tokens <= CONTEXT_WINDOW * 0.1:
        return BASE_RATIO
    
    # Linear interpolation
    ratio = BASE_RATIO - (avg_message_tokens / CONTEXT_WINDOW) * 0.25
    return max(ratio, MIN_RATIO)

def chunk_messages_by_max_tokens(
    messages: list[Message],
    max_tokens: int,
    safety_margin: float = 1.2,
) -> list[MessageChunk]:
    """
    Split messages into chunks with safety margin.
    
    Safety margin accounts for token estimation error.
    """
    effective_max = max_tokens / safety_margin
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for msg in messages:
        msg_tokens = estimate_tokens(msg)
        
        if current_tokens + msg_tokens > effective_max:
            # Start new chunk
            chunks.append(MessageChunk(messages=current_chunk))
            current_chunk = [msg]
            current_tokens = msg_tokens
        else:
            current_chunk.append(msg)
            current_tokens += msg_tokens
    
    if current_chunk:
        chunks.append(MessageChunk(messages=current_chunk))
    
    return chunks
```

#### **Day 4-5: Integration with Agent Runtime**

**Files to Modify:**
- `packages/agents/crew.py` - Integrate context engine
- `packages/memory/memory_service.py` - Update build_context

**Integration:**
```python
# packages/agents/crew.py

from packages.memory.context_engine import ContextEngine

async def run_crew(
    user_message: str,
    user_id: str = "default",
    model: str = "local",
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the full Planner → Researcher → Synthesizer pipeline."""
    
    # Use context engine for assembly
    context_engine = ContextEngine(
        session_id=user_id,
        token_budget=settings.agent_context_char_budget // 4,  # Approx tokens
    )
    
    context_result = await context_engine.assemble()
    
    # Inject into planner
    planner_messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        *context_result.messages,
        {"role": "user", "content": user_message},
    ]
    
    # ... rest of pipeline
```

**Deliverables:**
- ✅ Context engine implemented
- ✅ Adaptive token budgeting
- ✅ Session pruning integrated
- ✅ 20-30% token reduction

---

### **PHASE 6: DESKTOP APP POLISH** ⏱️ 5-7 days 🟢 **MEDIUM**

**Goal:** Add TanStack Query, agent trace visualization, improved streaming.

#### **Day 1-3: TanStack Query Integration**

**Install Dependencies:**
```bash
cd apps/desktop
npm install @tanstack/react-query
```

**Files to Create:**
- `apps/desktop/src/lib/query-client.ts` - TanStack Query client
- `apps/desktop/src/hooks/use-chat.ts` - Chat mutations
- `apps/desktop/src/hooks/use-memory.ts` - Memory queries

**Query Client:**
```typescript
// apps/desktop/src/lib/query-client.ts

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minutes
      retry: 2,
    },
  },
});
```

**Chat Hook:**
```typescript
// apps/desktop/src/hooks/use-chat.ts

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { chatSmart, chatPlain } from '../lib/api';

export function useChat() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (message: { text: string; model: string; smart: boolean }) => {
      const fn = message.smart ? chatSmart : chatPlain;
      return await fn(message.text, message.model);
    },
    onSuccess: () => {
      // Invalidate threads list
      queryClient.invalidateQueries({ queryKey: ['threads'] });
    },
  });
}
```

#### **Day 4-5: Agent Trace Visualization**

**Files to Create:**
- `apps/desktop/src/pages/AgentTracePage.tsx` - Agent trace viewer
- `apps/desktop/src/components/TraceTimeline.tsx` - Timeline component

**Trace Timeline:**
```typescript
// apps/desktop/src/components/TraceTimeline.tsx

interface TraceEvent {
  agent_name: string;
  event_type: string;
  content: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export function TraceTimeline({ runId }: { runId: string }) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  
  useEffect(() => {
    // Subscribe to SSE stream
    const eventSource = new EventSource(`/agents/trace/${runId}`);
    
    eventSource.onmessage = (event) => {
      const traceEvent = JSON.parse(event.data);
      setEvents(prev => [...prev, traceEvent]);
    };
    
    return () => eventSource.close();
  }, [runId]);
  
  return (
    <div className="trace-timeline">
      {events.map((event, i) => (
        <div key={i} className={`trace-event ${event.event_type}`}>
          <div className="trace-event-header">
            <span className="trace-event-agent">{event.agent_name}</span>
            <span className="trace-event-type">{event.event_type}</span>
            <span className="trace-event-time">
              {new Date(event.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="trace-event-content">
            {event.content}
          </div>
          {event.metadata && (
            <pre className="trace-event-metadata">
              {JSON.stringify(event.metadata, null, 2)}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}
```

#### **Day 6-7: Improved Streaming UI**

**Files to Modify:**
- `apps/desktop/src/pages/ChatPage.tsx` - Better streaming display

**Features:**
- Block streaming (completed paragraphs, not tokens)
- Typing indicators with human-like pacing
- Better error handling
- Copy button for responses

**Deliverables:**
- ✅ TanStack Query integrated
- ✅ Agent trace visualization
- ✅ Improved streaming UX
- ✅ Better error handling

---

## 📊 **SUCCESS METRICS**

| Metric | Current | Week 4 | Week 8 | Week 12 |
|--------|---------|--------|--------|---------|
| **Background Job Success Rate** | ~70% | 95% | 98% | 99% |
| **Memory Retention (6 months)** | ❌ No | ✅ Partial | ✅ Full | ✅ Optimized |
| **Code Agent Safety** | ⚠️ Basic | ✅ Sandboxed | ✅ Audited | ✅ Production |
| **Messaging Channels** | 0 | 0 | 1 (Telegram) | 3+ |
| **Context Efficiency** | 100% | 80% | 60% | 40% |
| **Token Usage (per agent run)** | 50-100K | 40-80K | 20-50K | 10-30K |
| **Desktop App Performance** | Good | Better | Excellent | Best-in-class |

---

## 🚨 **RISK MITIGATION**

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Redis adds complexity** | Medium | Low | Use Docker Compose, minimal config |
| **Docker sandboxing breaks tools** | High | Medium | Start with `sandbox_mode: "non-main"`, gradual rollout |
| **5-layer memory migration breaks data** | High | Medium | Dual-write during migration, rollback plan |
| **Telegram bot security** | High | Low | Pairing policy + approval codes |
| **ARQ workers consume RAM** | Medium | Medium | Limit worker pool (2-4), monitor |
| **Context compaction loses info** | High | Low | Multi-stage fallback, preserve identifiers |

---

## ✅ **IMMEDIATE NEXT STEPS**

### **Week 1 (Days 1-7):**
1. ✅ **Day 1:** Phase 0 (Infrastructure) - Redis setup
2. ✅ **Day 2-7:** Phase 1 (5-Layer Memory) - Start with Bootstrap + JSONL

### **Week 2 (Days 8-14):**
1. ✅ **Day 8-10:** Phase 1 (5-Layer Memory) - Complete Compaction
2. ✅ **Day 11-14:** Phase 2 (Workspace Isolation) - Start configuration

### **Week 3-4 (Days 15-28):**
1. ✅ **Phase 2:** Complete Workspace + Sandboxing
2. ✅ **Phase 3:** ARQ Background Tasks

### **Week 5-6 (Days 29-42):**
1. ✅ **Phase 4:** Telegram Messaging
2. ✅ **Phase 5:** Context Engine

### **Week 7-8 (Days 43-56):**
1. ✅ **Phase 6:** Desktop Polish
2. ✅ **Testing & Bug Fixes**

---

## 🎯 **CONCLUSION**

This plan positions your PersonalAssist in the **top 1%** of local AI assistants by:

1. ✅ **Keeping what works** - FastAPI, CrewAI, Qdrant+Mem0, Tauri
2. ✅ **Adopting best practices** - 5-layer memory, ARQ, Docker sandboxing
3. ✅ **Adding differentiators** - Telegram integration, workspace isolation, audit logging
4. ✅ **Ensuring longevity** - 6+ month memory retention, resilient background tasks

**Start with Phase 1 (5-Layer Memory)** - it's the foundation for everything else.

**Ready to implement?** I recommend we begin with **Phase 0 (Infrastructure)** followed immediately by **Phase 1 (5-Layer Memory)**.
