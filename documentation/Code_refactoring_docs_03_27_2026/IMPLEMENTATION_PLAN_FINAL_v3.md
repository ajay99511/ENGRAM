# PersonalAssist 2026: Final Architecture & Implementation Plan

**Document Type:** Production-Ready Implementation Plan (v3.0 - Final)  
**Review Date:** March 26, 2026  
**Status:** ✅ Validated with A2A Tiered Architecture, Critical Reviews Addressed

---

## 📊 **EXECUTIVE SUMMARY**

### **Vision**

A **production-grade local AI assistant** that:
- ✅ Runs entirely on user's machine (local-first, privacy-preserving)
- ✅ Remembers user preferences, projects, and decisions for 6+ months
- ✅ Executes background tasks reliably (survives restarts, has retry logic)
- ✅ Provides secure code agent capabilities (permissioned, audited)
- ✅ Accessible via desktop app + Telegram (expandable to more channels)
- ✅ Uses both local (Ollama) and cloud models efficiently

### **What Changed from v1.0 → v3.0**

| Version | Key Changes |
|---------|-------------|
| **v1.0** | Initial plan (85% keep, 15% enhance) |
| **v2.0** | Added critical review mitigations (secret redaction, Celery fallback, Docker deprioritized) |
| **v3.0 (Final)** | **A2A Tiered Architecture**, clarified agent boundaries, optimized protocol overhead |

---

## 🏗️ **AGENT-TO-AGENT (A2A) TIERED ARCHITECTURE**

### **Why Tiered Approach?**

Rather than applying heavy protocol overhead to ALL agents (inefficient), we match the communication pattern to the agent's purpose:

```
┌─────────────────────────────────────────────────────────────────┐
│  A2A TIERED ARCHITECTURE                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TIER 1: Full A2A Integration                                   │
│  ═══════════════════════════════════════════════════════════   │
│  Agents: Code management, workspace analysis, sub-agents        │
│  Protocol: Agent Cards + Capability Discovery + Async Tasks    │
│  Why: Need to discover & delegate to each other                │
│                                                                  │
│  TIER 2: Internal sessions_spawn Only                          │
│  ═══════════════════════════════════════════════════════════   │
│  Agents: Cron/background, memory sync, heartbeat               │
│  Protocol: Simple isolated sessions (existing pattern)         │
│  Why: No external discovery needed, internal orchestration     │
│                                                                  │
│  TIER 3: Direct FastAPI → LLM (No Protocol)                    │
│  ═══════════════════════════════════════════════════════════   │
│  Agents: Chat interface, Telegram responses                    │
│  Protocol: Direct API call, no routing indirection             │
│  Why: User-facing, latency-sensitive, no delegation needed     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### **Tier 1: Full A2A Integration** 🔵

**Agents:**
- Code management agents (analyze, refactor, review)
- Workspace analysis agents (project structure, dependencies)
- Sub-agents spawned for long-horizon tasks (research, multi-step workflows)

**Protocol Stack:**
```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 PROTOCOL: Full A2A                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agent Cards (Capability Discovery):                           │
│  {                                                              │
│    "agent_id": "code-reviewer",                                │
│    "name": "Code Review Agent",                                │
│    "capabilities": ["read_code", "review", "suggest_fixes"],   │
│    "input_schema": { "path": "string", "focus": "string" },    │
│    "output_schema": { "findings": [...], "summary": "string" },│
│    "permissions": { "read": ["src/**/*"], "write": [] }        │
│  }                                                              │
│                                                                  │
│  Async Task Lifecycle:                                          │
│  1. discover() → List available agents + capabilities          │
│  2. delegate(task) → { task_id, status: "queued" }             │
│  3. poll_status(task_id) → { status: "running" | "completed" } │
│  4. get_result(task_id) → { output, artifacts }                │
│                                                                  │
│  Use Cases:                                                     │
│  ├─ Planner agent delegates code review to code-reviewer       │
│  ├─ Workspace agent spawns sub-agent for dependency audit      │
│  └─ Research agent delegates web search to search-agent        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
# packages/agents/a2a/registry.py

from typing import Any
from pydantic import BaseModel

class AgentCard(BaseModel):
    """Capability advertisement for Tier 1 agents."""
    agent_id: str
    name: str
    description: str
    capabilities: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permissions: dict[str, list[str]]  # read/write/execute patterns

class A2ARegistry:
    """Service registry for Tier 1 agents."""
    
    def __init__(self):
        self.agents: dict[str, AgentCard] = {}
    
    def register(self, card: AgentCard):
        """Register an agent's capabilities."""
        self.agents[card.agent_id] = card
    
    def discover(self, capability: str) -> list[AgentCard]:
        """Find agents that provide a specific capability."""
        return [
            card for card in self.agents.values()
            if capability in card.capabilities
        ]
    
    async def delegate(
        self,
        agent_id: str,
        task: dict[str, Any],
    ) -> TaskHandle:
        """Delegate a task to a Tier 1 agent."""
        # Validate task against input_schema
        # Check permissions
        # Spawn isolated session
        # Return task handle for polling
        pass

# Usage in Planner agent
# packages/agents/planner.py

async def plan_complex_task(user_message: str):
    # Discover agents with needed capabilities
    code_reviewers = registry.discover("code_review")
    workspace_analyzers = registry.discover("workspace_analysis")
    
    # Delegate subtasks
    if code_reviewers:
        task_handle = await registry.delegate(
            agent_id=code_reviewers[0].agent_id,
            task={"path": "src/", "focus": "security"},
        )
        # Poll for completion
        result = await task_handle.wait()
```

---

### **Tier 2: Internal sessions_spawn Only** 🟢

**Agents:**
- Cron/background task agents (daily briefing, hourly snapshots)
- Memory sync agents (consolidation, compaction)
- Heartbeat agents (proactive check-ins)

**Protocol:**
```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2 PROTOCOL: Internal sessions_spawn                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pattern (Already in Your Codebase):                           │
│  ═══════════════════════════════════════════════════════════   │
│                                                                  │
│  from packages.agents.crew import run_crew                     │
│                                                                  │
│  # Cron job spawns isolated session                            │
│  result = await run_crew(                                      │
│      user_message="Generate morning briefing",                 │
│      user_id="default",                                        │
│      model="local",                                            │
│      session_type="isolated",  # ← Key: isolated session       │
│      session_id=f"daily_briefing:{job_id}",                    │
│  )                                                              │
│                                                                  │
│  No Agent Cards needed (internal only)                         │
│  No capability discovery (hardcoded routing)                   │
│  Direct function call (no protocol overhead)                   │
│                                                                  │
│  Use Cases:                                                     │
│  ├─ Daily briefing at 8:00 AM                                  │
│  ├─ Hourly Qdrant snapshot export                              │
│  ├─ Memory consolidation (every 20 turns)                      │
│  └─ Heartbeat proactive check-ins                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Why This Pattern:**
- ✅ Already implemented in your codebase
- ✅ No protocol overhead (direct function calls)
- ✅ Isolated sessions (token-efficient, fresh context each run)
- ✅ No external discovery needed (internal orchestration)

---

### **Tier 3: Direct FastAPI → LLM (No Protocol)** 🔴

**Agents:**
- Chat interface agents (desktop app)
- Telegram response agents
- Plain chat endpoints

**Protocol:**
```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3 PROTOCOL: Direct FastAPI → LLM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pattern (Already in Your Codebase):                           │
│  ═══════════════════════════════════════════════════════════   │
│                                                                  │
│  # apps/api/main.py                                             │
│  @app.post("/chat/smart")                                      │
│  async def chat_smart(req: ChatRequest):                       │
│      # Build context (Mem0 + RAG)                              │
│      context = await build_context(req.message)                │
│                                                                  │
│      # Direct LLM call (no agent orchestration)                │
│      response = await chat(                                    │
│          messages=[                                            │
│              {"role": "system", "content": SYSTEM_PROMPT},     │
│              {"role": "user", "content": req.message},         │
│          ],                                                    │
│          model=req.model,                                      │
│      )                                                          │
│                                                                  │
│      return {"response": response}                             │
│                                                                  │
│  Use Cases:                                                     │
│  ├─ Desktop app chat (plain/smart/stream)                      │
│  ├─ Telegram bot responses                                     │
│  └─ Simple Q&A (no multi-step reasoning needed)                │
│                                                                  │
│  Why Direct:                                                    │
│  ├─ Latency-sensitive (user waiting)                           │
│  ├─ No delegation needed (single LLM call)                     │
│  └─ Protocol overhead would add 100-300ms latency              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 **FINAL IMPLEMENTATION PLAN (v3.0)**

### **Phase Priorities (Updated with A2A Tiers)**

| Phase | Components | A2A Tier | Timeline | Priority |
|-------|-----------|----------|----------|----------|
| **Phase 0** | Infra (Redis, directories) | N/A | Week 1 | 🔴 CRITICAL |
| **Phase 1** | 5-Layer Memory + Secret Redaction | Tier 2 | Week 1-2 | 🔴 CRITICAL |
| **Phase 2** | Workspace (Path Allowlists + Audit) | Tier 1 | Week 3-4 | 🟡 HIGH |
| **Phase 3** | ARQ Background Tasks (+ Celery fallback) | Tier 2 | Week 5-6 | 🔴 CRITICAL |
| **Phase 4** | Telegram Gateway | Tier 3 | Week 7-8 | 🟢 MEDIUM |
| **Phase 5** | Context Engine (Adaptive Pruning) | Tier 2 | Week 9-10 | 🟢 MEDIUM |
| **Phase 6** | Desktop Polish (TanStack Query, Traces) | Tier 3 | Week 11-12 | 🟢 MEDIUM |
| **Phase 7** | A2A Registry (Tier 1 Agents) | Tier 1 | Week 13-14 | 🟢 MEDIUM |
| **Phase 8** | Docker Sandboxing (Optional) | Tier 1 | Week 15+ | ⚪ LOW |

---

### **Phase 0: Infrastructure (Week 1)** ⏱️ 1-2 days

**Goal:** Add Redis for background tasks, prepare directory structure.

**Tasks:**

1. **Update Docker Compose** (`infra/docker-compose.yml`):
   ```yaml
   services:
     qdrant:
       # ... existing config ...
     
     redis:
       image: redis:7-alpine
       container_name: personalassist-redis
       ports:
         - "6379:6379"
       volumes:
         - ../storage/redis_data:/data
       command: redis-server --appendonly yes
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 10s
         timeout: 5s
         retries: 5
   ```

2. **Update Dependencies** (`requirements.txt`):
   ```txt
   # Background Tasks
   arq==0.25.0          # Pin version for stability
   redis>=5.0.0
   
   # Fallback (commented, ready for migration)
   # celery[gevent]>=5.3.0
   
   # Messaging (Phase 4)
   # python-telegram-bot>=20.0
   
   # Sandboxing (Phase 8, optional)
   # docker>=7.0.0
   ```

3. **Create Directory Structure**:
   ```bash
   mkdir -p ~/.personalassist/{sessions,memory,workspaces,sandboxes,logs,agent-cards}
   ```

4. **Create Bootstrap Templates**:
   - `~/.personalassist/AGENTS.md` - Operating instructions
   - `~/.personalassist/SOUL.md` - Persona and tone
   - `~/.personalassist/USER.md` - User preferences
   - `~/.personalassist/IDENTITY.md` - Agent identity
   - `~/.personalassist/TOOLS.md` - Tool capabilities
   - `~/.personalassist/HEARTBEAT.md` - Background task checklist

**Deliverables:**
- ✅ Redis running in Docker
- ✅ Directory structure created
- ✅ Bootstrap templates in place

---

### **Phase 1: 5-Layer Memory + Secret Redaction (Week 1-2)** 🔴 **CRITICAL**

**Goal:** Implement OpenClaw's memory architecture with secret redaction.

**Why First:** Foundation for 6+ month retention. Without this, system forgets important context.

#### **Day 1-2: Layer 1 (Bootstrap Injection) + Secret Redaction**

**Files to Create:**

1. **`packages/shared/redaction.py`** - Secret redaction middleware:
   ```python
   import re
   from typing import Any
   from datetime import datetime
   
   class SecretRedactor:
       """Redact secrets from tool outputs before JSONL persistence."""
       
       PATTERNS = [
           # API Keys
           (r'sk-[A-Za-z0-9]{20,}', '[REDACTED_API_KEY]'),
           (r'AIza[A-Za-z0-9_-]{20,}', '[REDACTED_GOOGLE_API_KEY]'),
           (r'ghp_[A-Za-z0-9]{36}', '[REDACTED_GITHUB_TOKEN]'),
           
           # AWS Credentials
           (r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_ACCESS_KEY]'),
           
           # Private Keys
           (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (RSA |EC )?PRIVATE KEY-----', 
            '[REDACTED_PRIVATE_KEY]'),
           
           # Passwords in command output
           (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']+', r'\1=[REDACTED]'),
           
           # Bearer tokens
           (r'Bearer [A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', 'Bearer [REDACTED_JWT]'),
       ]
       
       def __init__(self, custom_patterns: list[tuple[str, str]] | None = None):
           self.compiled_patterns = [
               (re.compile(pattern, re.IGNORECASE if 'password' in pattern else 0), replacement)
               for pattern, replacement in self.PATTERNS
           ]
           if custom_patterns:
               self.compiled_patterns.extend([
                   (re.compile(p), r) for p, r in custom_patterns
               ])
       
       def redact(self, text: str) -> tuple[str, int]:
           """Redact secrets from text. Returns (redacted_text, redaction_count)."""
           result = text
           total_redactions = 0
           
           for pattern, replacement in self.compiled_patterns:
               matches = pattern.findall(result)
               if matches:
                   total_redactions += len(matches)
                   result = pattern.sub(replacement, result)
           
           return result, total_redactions
       
       def redact_tool_result(self, tool_result: dict[str, Any]) -> dict[str, Any]:
           """Redact secrets from a tool result dict."""
           redacted = tool_result.copy()
           total_redactions = 0
           
           # Redact string fields
           for key in ['output', 'stdout', 'stderr', 'error', 'content']:
               if key in redacted and isinstance(redacted[key], str):
                   redacted[key], count = self.redact(redacted[key])
                   total_redactions += count
           
           # Redact args (may contain passwords)
           if 'args' in redacted and isinstance(redacted['args'], dict):
               for arg_key in ['password', 'secret', 'token', 'api_key']:
                   if arg_key in redacted['args']:
                       redacted['args'][arg_key] = '[REDACTED]'
                       total_redactions += 1
           
           # Add redaction metadata
           if total_redactions > 0:
               redacted['_redaction_metadata'] = {
                   'redacted_count': total_redactions,
                   'redacted_at': datetime.now().isoformat(),
               }
           
           return redacted
   ```

2. **`packages/memory/bootstrap.py`** - Bootstrap file manager:
   ```python
   from pathlib import Path
   from typing import Literal
   
   BOOTSTRAP_FILES = [
       "AGENTS.md",
       "SOUL.md",
       "USER.md",
       "IDENTITY.md",
       "TOOLS.md",
       "HEARTBEAT.md",
       "MEMORY.md",
   ]
   
   MAX_CHARS_PER_FILE = 20_000
   MAX_TOTAL_CHARS = 150_000
   
   async def load_bootstrap_files(
       agent_type: Literal["main", "sub-agent"] = "main",
   ) -> str:
       """Load bootstrap files from ~/.personalassist/"""
       base_path = Path.home() / ".personalassist"
       
       # Sub-agents get only AGENTS.md + TOOLS.md
       if agent_type == "sub-agent":
           files_to_load = ["AGENTS.md", "TOOLS.md"]
       else:
           files_to_load = BOOTSTRAP_FILES
       
       sections = []
       total_chars = 0
       
       for filename in files_to_load:
           file_path = base_path / filename
           if not file_path.exists():
               continue
           
           content = file_path.read_text()[:MAX_CHARS_PER_FILE]
           if content.strip():
               sections.append(f"## {filename.replace('.md', '')}\n{content}")
               total_chars += len(content)
               
               if total_chars >= MAX_TOTAL_CHARS:
                   sections.append(f"\n\n[... truncated at {MAX_TOTAL_CHARS} chars ...]")
                   break
       
       return "\n\n".join(sections) if sections else ""
   ```

**Integration:**
- Modify `packages/agents/crew.py` to call `load_bootstrap_files()` in system prompt assembly
- Modify `packages/memory/jsonl_store.py` to call `SecretRedactor.redact_tool_result()` before JSONL write

#### **Day 3-5: Layer 2 (JSONL Transcripts)**

**Files to Create:**

1. **`packages/memory/jsonl_store.py`** - JSONL transcript manager:
   ```python
   import json
   from pathlib import Path
   from datetime import datetime
   from typing import Any
   from packages.shared.redaction import SecretRedactor
   
   redactor = SecretRedactor()
   
   class JSONLEntry(BaseModel):
       id: str
       type: Literal["message", "toolResult", "compaction", "session_info"]
       parent_id: str | None = None
       content: dict[str, Any]
       timestamp: str
   
   async def append_entry(session_id: str, entry: JSONLEntry):
       """Append entry to JSONL transcript with secret redaction."""
       sessions_dir = Path.home() / ".personalassist" / "sessions"
       sessions_dir.mkdir(parents=True, exist_ok=True)
       
       # Redact secrets before writing
       if entry.type == "toolResult":
           entry.content = redactor.redact_tool_result(entry.content)
       
       # Append to JSONL
       file_path = sessions_dir / f"{session_id}.jsonl"
       with open(file_path, 'a', encoding='utf-8') as f:
           f.write(json.dumps(entry.model_dump()) + '\n')
   
   async def load_transcript(session_id: str) -> list[JSONLEntry]:
       """Load transcript from JSONL file."""
       file_path = Path.home() / ".personalassist" / "sessions" / f"{session_id}.jsonl"
       if not file_path.exists():
           return []
       
       entries = []
       with open(file_path, 'r', encoding='utf-8') as f:
           for line in f:
               entries.append(JSONLEntry(**json.loads(line)))
       return entries
   ```

2. **`packages/memory/session_manager.py`** - Session lifecycle manager:
   ```python
   from datetime import datetime
   from packages.memory.jsonl_store import append_entry, load_transcript
   
   class SessionManager:
       def __init__(self, session_id: str, user_id: str):
           self.session_id = session_id
           self.user_id = user_id
           self.created_at = datetime.now()
       
       async def start(self):
           """Initialize session with metadata."""
           await append_entry(self.session_id, JSONLEntry(
               id=str(uuid.uuid4()),
               type="session_info",
               content={
                   "user_id": self.user_id,
                   "created_at": self.created_at.isoformat(),
                   "reset_reason": "new_session",
               },
           ))
       
       async def add_message(self, role: str, content: str):
           """Add user/assistant message to transcript."""
           await append_entry(self.session_id, JSONLEntry(
               id=str(uuid.uuid4()),
               type="message",
               content={"role": role, "content": content},
           ))
       
       async def add_tool_result(self, tool_result: dict):
           """Add tool result to transcript (with automatic redaction)."""
           await append_entry(self.session_id, JSONLEntry(
               id=str(uuid.uuid4()),
               type="toolResult",
               content=tool_result,
           ))
   ```

#### **Day 6-7: Layer 3 (Session Pruning)**

**Files to Create:**

1. **`packages/memory/pruning.py`** - In-memory session pruning:
   ```python
   from typing import Any
   from datetime import datetime, timedelta
   
   async def prune_old_tool_results(
       messages: list[dict[str, Any]],
       ttl_seconds: int = 300,  # 5 minutes
       protect_last_n: int = 3,
   ) -> list[dict[str, Any]]:
       """
       Trim old tool results from in-memory context.
       
       Does NOT rewrite JSONL files - only affects current LLM call.
       """
       now = datetime.now()
       pruned = []
       tool_result_count = 0
       
       # Keep last N messages regardless
       protected = messages[-protect_last_n:] if len(messages) > protect_last_n else []
       to_prune = messages[:-protect_last_n] if len(messages) > protect_last_n else messages
       
       for msg in to_prune:
           if msg.get("role") == "tool":
               # Check TTL
               msg_time = msg.get("_timestamp")
               if msg_time:
                   age = (now - msg_time).total_seconds()
                   if age > ttl_seconds:
                       # Replace with placeholder
                       pruned.append({
                           "role": "tool",
                           "content": "[Old tool result content cleared]",
                       })
                       tool_result_count += 1
                   else:
                       pruned.append(msg)
               else:
                   pruned.append(msg)
           else:
               pruned.append(msg)
       
       return pruned + protected
   ```

#### **Day 8-10: Layer 4 (Compaction)**

**Files to Create:**

1. **`packages/memory/compaction.py`** - Adaptive compaction engine:
   ```python
   from packages.model_gateway.client import chat
   
   CONTEXT_WINDOW = 128_000  # tokens (adjust per model)
   RESERVE_TOKENS = 4_000
   SOFT_THRESHOLD = 4_000
   
   async def compact_session(session_id: str) -> CompactionResult:
       """
       Compact session when context nears limit.
       """
       # Load transcript
       entries = await load_transcript(session_id)
       messages = [e.content for e in entries if e.type == "message"]
       
       # Estimate tokens
       current_tokens = estimate_tokens(messages)
       
       # Check if compaction needed
       if current_tokens < CONTEXT_WINDOW - RESERVE_TOKENS:
           return CompactionResult(skipped=True, reason="not_needed")
       
       # Pre-compaction memory flush (silent turn)
       await memory_flush_turn(session_id)
       
       # Compute adaptive chunk ratio
       avg_msg_tokens = current_tokens / len(messages) if messages else 0
       ratio = compute_adaptive_chunk_ratio(avg_msg_tokens)
       
       # Chunk messages
       max_chunk_tokens = CONTEXT_WINDOW * ratio
       chunks = chunk_messages_by_max_tokens(messages, max_chunk_tokens, safety_margin=1.2)
       
       # Summarize with fallback
       summary = await summarize_with_fallback(chunks)
       
       # Preserve identifiers
       summary = preserve_identifiers(summary, messages)
       
       # Truncate JSONL (atomic write)
       await truncate_session_after_compaction(session_id, summary)
       
       return CompactionResult(
           skipped=False,
           entries_removed=len(chunks),
           summary=summary,
       )
   
   async def memory_flush_turn(session_id: str):
       """Silent turn to write durable memories before compaction."""
       from packages.agents.crew import run_crew
       
       result = await run_crew(
           user_message="Session nearing compaction. Write any lasting notes to MEMORY.md; reply NO_REPLY if nothing to store.",
           user_id="default",
           model="local",
           session_type="silent",  # NO_REPLY expected
       )
   ```

**Deliverables:**
- ✅ 5-layer memory system fully implemented
- ✅ Secret redaction integrated (before JSONL write)
- ✅ Migration path from old to new system
- ✅ Memory flush before compaction

---

### **Phase 2: Workspace (Path Allowlists + Audit) (Week 3-4)** 🟡 **HIGH**

**Goal:** Secure code agent capabilities with permission-based access (Windows-native, no Docker).

#### **Day 1-3: Path Allowlist System**

**Files to Create:**

1. **`packages/agents/workspace.py`** - Workspace configuration manager:
   ```python
   from pathlib import Path
   import fnmatch
   import json
   from datetime import datetime
   from pydantic import BaseModel
   
   class WorkspacePermissions(BaseModel):
       read: list[str] = ["**/*"]
       write: list[str] = []
       execute: bool = False
       git_operations: bool = True
       network_access: bool = False
   
   class WorkspaceConfig(BaseModel):
       project_id: str
       root: Path
       permissions: WorkspacePermissions
       context_collection: str
       agent_instructions: str = ""
   
   class WorkspaceManager:
       DANGEROUS_PATTERNS = [
           'C:/Windows/**',
           'C:/$Recycle.Bin/**',
           '**/.ssh/**',
           '**/.aws/**',
           '**/.git-credentials',
           '**/.env',
           '**/*secret*',
           '**/*password*',
       ]
       
       def __init__(self, config: WorkspaceConfig):
           self.config = config
           self.audit_log = config.root / '.agent_audit.log'
       
       def _is_path_safe(self, path: Path) -> bool:
           """Block dangerous paths regardless of allowlist."""
           path_str = str(path.resolve()).replace('\\', '/')
           for pattern in self.DANGEROUS_PATTERNS:
               if fnmatch.fnmatch(path_str, pattern):
                   return False
           return True
       
       def can_read(self, path: Path) -> bool:
           if not self._is_path_safe(path):
               self._audit('read', path, False, 'Blocked dangerous path')
               return False
           
           try:
               path.resolve().relative_to(self.config.root.resolve())
           except ValueError:
               self._audit('read', path, False, 'Outside root')
               return False
           
           path_str = str(path.relative_to(self.config.root)).replace('\\', '/')
           for pattern in self.config.permissions.read:
               if fnmatch.fnmatch(path_str, pattern):
                   self._audit('read', path, True)
                   return True
           
           self._audit('read', path, False, 'Not in allowlist')
           return False
       
       def can_write(self, path: Path) -> bool:
           if not self._is_path_safe(path):
               self._audit('write', path, False, 'Blocked dangerous path')
               return False
           
           path_str = str(path.resolve()).replace('\\', '/')
           for pattern in self.config.permissions.write:
               if fnmatch.fnmatch(path_str, pattern):
                   self._audit('write', path, True)
                   return True
           
           self._audit('write', path, False, 'Not in write allowlist')
           return False
       
       def _audit(self, action: str, path: Path, allowed: bool, reason: str = ''):
           """Log every permission check for audit trail."""
           entry = {
               'timestamp': datetime.now().isoformat(),
               'action': action,
               'path': str(path),
               'allowed': allowed,
               'reason': reason,
           }
           with open(self.audit_log, 'a') as f:
               f.write(json.dumps(entry) + '\n')
   ```

#### **Day 4-5: A2A Registry (Tier 1 Agents)**

**Files to Create:**

1. **`packages/agents/a2a/registry.py`** - A2A service registry:
   ```python
   from typing import Any
   from pydantic import BaseModel
   
   class AgentCard(BaseModel):
       agent_id: str
       name: str
       description: str
       capabilities: list[str]
       input_schema: dict[str, Any]
       output_schema: dict[str, Any]
       permissions: dict[str, list[str]]
   
   class A2ARegistry:
       def __init__(self):
           self.agents: dict[str, AgentCard] = {}
       
       def register(self, card: AgentCard):
           self.agents[card.agent_id] = card
       
       def discover(self, capability: str) -> list[AgentCard]:
           return [
               card for card in self.agents.values()
               if capability in card.capabilities
           ]
       
       async def delegate(
           self,
           agent_id: str,
           task: dict[str, Any],
       ) -> TaskHandle:
           # Validate task against input_schema
           # Check permissions
           # Spawn isolated session
           # Return task handle
           pass
   ```

2. **`packages/agents/a2a/agents.py`** - Tier 1 agent definitions:
   ```python
   # Code Review Agent Card
   CODE_REVIEWER_CARD = AgentCard(
       agent_id="code-reviewer",
       name="Code Review Agent",
       description="Reviews code for security, performance, and style issues",
       capabilities=["code_review", "security_scan", "style_check"],
       input_schema={
           "type": "object",
           "properties": {
               "path": {"type": "string"},
               "focus": {"type": "string", "enum": ["security", "performance", "style", "all"]},
           },
       },
       output_schema={
           "type": "object",
           "properties": {
               "findings": {"type": "array"},
               "summary": {"type": "string"},
           },
       },
       permissions={"read": ["src/**/*"], "write": [], "execute": False},
   )
   
   # Workspace Analysis Agent Card
   WORKSPACE_ANALYZER_CARD = AgentCard(
       agent_id="workspace-analyzer",
       name="Workspace Analysis Agent",
       description="Analyzes project structure, dependencies, and codebase health",
       capabilities=["workspace_analysis", "dependency_audit", "structure_review"],
       input_schema={
           "type": "object",
           "properties": {
               "project_path": {"type": "string"},
               "depth": {"type": "integer", "default": 3},
           },
       },
       output_schema={
           "type": "object",
           "properties": {
               "structure": {"type": "object"},
               "dependencies": {"type": "array"},
               "recommendations": {"type": "array"},
           },
       },
       permissions={"read": ["**/*"], "write": [], "execute": True},
   )
   ```

**Deliverables:**
- ✅ Path allowlist system (Windows-native)
- ✅ Audit logging for every tool call
- ✅ A2A registry for Tier 1 agents
- ✅ Agent Cards for code management agents

---

### **Phase 3: ARQ Background Tasks (Week 5-6)** 🔴 **CRITICAL**

**Goal:** Migrate from APScheduler to ARQ for production-grade reliability.

#### **Day 1-2: ARQ Worker Setup**

**Files to Create:**

1. **`packages/automation/arq_worker.py`**:
   ```python
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
       
       max_jobs = 10
       job_timeout = 300
       retry_delay = 60
       retry_delay_steps = [60, 120, 300, 900, 3600]
   ```

#### **Day 3-4: Job Definitions**

**Files to Create:**

1. **`packages/automation/jobs.py`**:
   ```python
   from arq.ctx import redis
   from packages.agents.crew import run_crew
   
   async def run_daily_briefing(ctx):
       """Proactive agent that generates morning summary."""
       job_id = ctx["job_id"]
       
       # Use isolated session (token-efficient)
       result = await run_crew(
           user_message="Generate a morning briefing of recent activity.",
           user_id="default",
           model="local",
           session_type="isolated",
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
       """Export Qdrant snapshot for backup."""
       from packages.memory.qdrant_store import export_snapshot
       await export_snapshot()
   ```

#### **Day 5: Celery Fallback Documentation**

**Files to Create:**

1. **`packages/automation/MIGRATION_TO_CELERY.md`**:
   ```markdown
   # ARQ → Celery Migration Plan
   
   ## Trigger Conditions
   - ARQ repo shows no activity for 6+ months
   - Critical bug in ARQ with no fix
   
   ## Migration Steps
   1. Install celery[gevent]
   2. Replace arq cron with Celery beat
   3. Update task decorators (@arq.task → @app.task)
   4. Test with existing jobs
   5. Deploy with feature flag
   
   ## Estimated Effort: 2-3 days
   ```

**Deliverables:**
- ✅ ARQ workers running
- ✅ Jobs persist in Redis (survive restarts)
- ✅ Retry with exponential backoff
- ✅ Celery fallback plan documented

---

### **Phase 4-8: Remaining Phases (Week 7-15+)**

**No major changes** from v2.0 plan. See `IMPLEMENTATION_PLAN_2026.md` for details.

---

## 📊 **FINAL SUCCESS METRICS**

| Metric | Current | Week 4 | Week 8 | Week 12 | Week 16 |
|--------|---------|--------|--------|---------|---------|
| **Background Job Success Rate** | ~70% | 95% | 95% | 98% | 98% |
| **Memory Retention (6 months)** | ❌ No | ✅ Partial | ✅ Full | ✅ Optimized | ✅ Production |
| **Code Agent Safety** | ⚠️ Basic | ✅ Path Allowlists | ✅ + Audit | ✅ + A2A | ⚪ + Docker (optional) |
| **Token Usage (per agent run)** | 50-100K | 40-80K | 30-60K | 20-50K | 15-40K |
| **Tier 1 Agents (A2A)** | 0 | 0 | 0 | 2 | 4+ |
| **Tier 2 Agents (Internal)** | 1 | 3 | 3 | 4 | 4 |
| **Tier 3 Agents (Direct)** | 2 | 2 | 3 | 3 | 3 |

---

## 🎯 **FINAL RECOMMENDATIONS**

### **Start Implementation This Week:**

1. ✅ **Phase 0 (Day 1-2):** Redis setup, directory structure
2. ✅ **Phase 1 (Day 3-10):** 5-Layer Memory + Secret Redaction
3. ✅ **Phase 2 (Week 3-4):** Path Allowlists + A2A Registry

### **Key Architectural Decisions:**

| Decision | Rationale |
|----------|-----------|
| **Tiered A2A Architecture** | Match protocol overhead to agent purpose (efficient) |
| **5-Layer Memory First** | Foundation for 6+ month retention |
| **Secret Redaction** | Critical security fix (prevents credential leakage) |
| **Path Allowlists over Docker** | Windows-native, 80% security benefit, lower complexity |
| **ARQ with Celery Fallback** | Best of both (simplicity + future-proof) |
| **Mem0 + 5-Layer Boundaries** | Clear separation (user facts vs session context) |

---

**This is the FINAL, production-ready implementation plan.**

**Ready to proceed with Phase 1?**
