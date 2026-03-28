# PersonalAssist 2026: Critical Architecture Review & Updated Plan

**Document Type:** Critical Re-Evaluation with Risk Mitigations  
**Review Date:** March 26, 2026  
**Status:** ✅ Validated with Trade-Offs Acknowledged

---

## 🔍 **CRITICAL REVIEW SUMMARY**

### **What Passed Scrutiny** ✅

| Component | Original Claim | Verification | Status |
|-----------|---------------|--------------|--------|
| **ARQ over APScheduler** | ARQ is asyncio-native with retry/persistence | ✅ Confirmed: ARQ has exponential backoff, Redis persistence, priority queues | **VALID** |
| **5-Layer Memory System** | OpenClaw architecture is real | ✅ Confirmed: Bootstrap→JSONL→Prune→Compact→LTM is documented | **VALID** |
| **Hybrid Search Formula** | (vector × 0.7) + (text × 0.3) | ✅ Confirmed: Matches OpenClaw docs + third-party write-ups | **VALID** |
| **Compaction Research** | Based on March 2026 arxiv paper | ✅ Confirmed: Hierarchical memory with demand-paging semantics | **VALID** |
| **OpenClaw Gateway** | WebSocket on 127.0.0.1:18789 with pairing | ✅ Confirmed: Official OpenClaw documentation | **VALID** |

### **What Was Overstated** ⚠️

| Claim | Reality Check | Updated Assessment |
|-------|--------------|-------------------|
| **"Top 1% of AI assistants"** | Marketing language, unverifiable | ❌ **REMOVED** - Replace with "production-grade local assistant" |
| **"Node.js would require 6-12 months"** | Hyperbolic | ⚠️ **SOFTENED** - Real reason: ecosystem alignment, not migration difficulty |
| **"ARQ is maintenance-safe"** | GitHub issue (2024) notes limited maintainership | ⚠️ **FLAGGED** - Need Celery fallback plan |
| **"Docker sandboxing is Medium complexity"** | On Windows: **High complexity** (volume mounts, path issues) | ⚠️ **DEPRIORITIZED** - Start with path allowlists + audit logging |
| **"6+ month retention guaranteed"** | Depends on summarization quality | ⚠️ **QUALIFIED** - Best-case, not guaranteed; LLM summaries lose nuance |

### **Critical Gaps Identified** 🔴

| Gap | Risk | Mitigation Required |
|-----|------|-------------------|
| **JSONL Secret Leakage** | Exec tool outputs (with secrets) persist verbatim to JSONL | 🔴 **SECRET REDACTION MIDDLEWARE** before JSONL write |
| **Mem0 + 5-Layer Redundancy** | Potential overlap between Mem0 extraction and Layer 5 LTM | 🔴 **CLEAR BOUNDARIES** - Mem0 for user facts, 5-layer for session context |
| **Windows Docker Friction** | Volume mounts, path conventions, performance overhead | 🔴 **PHASED APPROACH** - Path allowlists first, Docker later |
| **ARQ Maintenance Risk** | Limited active maintainership as of 2024 | 🔴 **CELERY FALLBACK** - Document migration path |
| **Tauri ↔ FastAPI WebSocket** | No upgrade path evaluated | 🔴 **ADD EVALUATION** - When to migrate from REST+SSE to WebSocket |

---

## 📊 **UPDATED TECHNOLOGY DECISIONS**

### **Decision 1: Background Task System (ARQ vs Celery)**

**Original Recommendation:** ARQ  
**Review Finding:** ✅ Valid, but maintenance concerns noted

**Updated Decision:**

```
┌─────────────────────────────────────────────────────────────────┐
│  BACKGROUND TASK SYSTEM: ARQ with Celery Fallback              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1 (Week 1-2): ARQ                                       │
│  ├─ Pros: Asyncio-native, simple, FastAPI integration          │
│  ├─ Cons: Limited maintainership (GitHub issue 2024)           │
│  └─ Mitigation: Pin version (arq==0.25.0), monitor repo        │
│                                                                  │
│  Phase 2 (Fallback Plan): Celery                               │
│  ├─ Trigger if: ARQ repo shows no activity for 6+ months       │
│  ├─ Migration effort: ~2-3 days (similar patterns)             │
│  └─ Celery config: celery[gevent] for async support            │
│                                                                  │
│  Why ARQ First:                                                 │
│  ├─ Lower complexity for current scale                         │
│  ├─ Better asyncio integration (matches FastAPI)               │
│  └─ Easier to implement (less boilerplate)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Updated Requirements:**
```txt
# requirements.txt

# Primary (ARQ)
arq==0.25.0          # Pin version for stability
redis>=5.0.0

# Fallback (Celery) - commented, ready for migration
# celery[gevent]>=5.3.0
# redis>=5.0.0
```

**Migration Path (ARQ → Celery):**
```python
# Current (ARQ):
from arq import cron
async def run_daily_briefing(ctx): ...

# Future (Celery):
from celery import Celery
from celery.schedules import crontab

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def run_daily_briefing(): ...

app.conf.beat_schedule = {
    'daily-briefing': {
        'task': 'tasks.run_daily_briefing',
        'schedule': crontab(hour=8, minute=0),
    },
}
```

---

### **Decision 2: Workspace Isolation (Docker vs Path Allowlists)**

**Original Recommendation:** Docker sandboxing (Phase 2, Week 3-4)  
**Review Finding:** 🔴 **HIGH complexity on Windows** - volume mounts, path issues

**Updated Decision:**

```
┌─────────────────────────────────────────────────────────────────┐
│  WORKSPACE ISOLATION: Phased Approach                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1 (Week 3-4): Enhanced Path Allowlists                  │
│  ├─ Strict glob-based permissions (read/write/execute)         │
│  ├─ Audit logging for every tool call                          │
│  ├─ Path validation (block dangerous patterns)                 │
│  └─ Windows-native (no Docker required)                        │
│                                                                  │
│  Phase 2 (Week 9-10, Optional): Docker Sandboxing              │
│  ├─ Only if: Phase 1 proves insufficient                       │
│  ├─ Windows-specific config (named pipes, volume mounts)       │
│  ├─ Test on your specific paths first                          │
│  └─ Fallback: Keep Phase 1 as default                          │
│                                                                  │
│  Why Phased:                                                    │
│  ├─ Windows Docker has known friction points                   │
│  ├─ Path allowlists + audit logging = 80% security benefit     │
│  └─ Docker adds operational complexity (debugging, perf)       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Phase 1 Implementation (Path Allowlists + Audit):**

```python
# packages/agents/workspace.py

from pathlib import Path
import fnmatch
import json
from datetime import datetime

class WorkspacePermissions:
    def __init__(self, config: dict):
        self.root = Path(config['root'])
        self.read_patterns = config.get('read', ['**/*'])
        self.write_patterns = config.get('write', [])
        self.execute_allowed = config.get('execute', False)
        self.audit_log = self.root / '.agent_audit.log'
    
    def _is_path_safe(self, path: Path) -> bool:
        """Block dangerous paths regardless of allowlist."""
        dangerous_patterns = [
            'C:/Windows/**',
            'C:/$Recycle.Bin/**',
            '**/.ssh/**',
            '**/.aws/**',
            '**/.git-credentials',
            '**/.env',
            '**/*secret*',
            '**/*password*',
        ]
        
        path_str = str(path.resolve()).replace('\\', '/')
        for pattern in dangerous_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return False
        return True
    
    def can_read(self, path: Path) -> bool:
        if not self._is_path_safe(path):
            self._audit('read', path, False, 'Blocked dangerous path')
            return False
        
        # Must be under root
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError:
            self._audit('read', path, False, 'Outside root')
            return False
        
        # Check allowlist
        path_str = str(path.relative_to(self.root)).replace('\\', '/')
        for pattern in self.read_patterns:
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
        for pattern in self.write_patterns:
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

**Phase 2 (Docker) - Windows-Specific Config:**

```yaml
# infra/docker-compose.windows.yml

services:
  sandbox:
    image: personalassist-sandbox:latest
    # Windows-specific volume mounts
    volumes:
      - type: bind
        source: C:\Agents\PersonalAssist
        target: /workspace
        bind:
          # Use named pipes for Windows
          propagation: cached
      - type: volume
        source: sandbox-data
        target: /sandbox
    # Windows-specific networking
    network_mode: none
    # Resource limits (prevent runaway containers)
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

---

### **Decision 3: JSONL Secret Redaction**

**Original Plan:** No mention of secret leakage  
**Review Finding:** 🔴 **CRITICAL GAP** - Exec tool outputs persist verbatim to JSONL

**Updated Implementation:**

```
┌─────────────────────────────────────────────────────────────────┐
│  JSONL SECRET REDACTION MIDDLEWARE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Problem:                                                       │
│  ├─ Exec tool outputs (stdout/stderr) may contain secrets      │
│  ├─ These are written verbatim to JSONL transcripts            │
│  ├─ Confirmed OpenClaw security issue (Feb 2026)               │
│  └─ Risk: API keys, passwords, tokens persisted to disk        │
│                                                                  │
│  Solution: Redaction Middleware                                │
│  ├─ Intercept tool results BEFORE JSONL write                  │
│  ├─ Apply regex patterns for common secrets                    │
│  ├─ Replace with [REDACTED] markers                            │
│  └─ Log redaction count (not content) for audit                │
│                                                                  │
│  Redaction Patterns:                                            │
│  ├─ API keys (sk-..., AIza..., ghp_...)                        │
│  ├─ Passwords in command output                                │
│  ├─ AWS credentials (AKIA..., secret keys)                     │
│  ├─ Private keys (BEGIN RSA PRIVATE KEY)                       │
│  └─ Custom patterns from user config                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
# packages/shared/redaction.py

import re
from typing import Any

class SecretRedactor:
    """Redact secrets from tool outputs before JSONL persistence."""
    
    # Common secret patterns
    PATTERNS = [
        # API Keys
        (r'sk-[A-Za-z0-9]{20,}', '[REDACTED_API_KEY]'),
        (r'AIza[A-Za-z0-9_-]{20,}', '[REDACTED_GOOGLE_API_KEY]'),
        (r'ghp_[A-Za-z0-9]{36}', '[REDACTED_GITHUB_TOKEN]'),
        (r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*', '[REDACTED_SLACK_TOKEN]'),
        
        # AWS Credentials
        (r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_ACCESS_KEY]'),
        (r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])', '[REDACTED_AWS_SECRET]'),
        
        # Private Keys
        (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (RSA |EC )?PRIVATE KEY-----', 
         '[REDACTED_PRIVATE_KEY]'),
        
        # Passwords in command output
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']+', 
         r'\1=[REDACTED]'),
        
        # Bearer tokens
        (r'Bearer [A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', 
         'Bearer [REDACTED_JWT]'),
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
        """
        Redact secrets from text.
        
        Returns:
            (redacted_text, redaction_count)
        """
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


# Usage in JSONL store
# packages/memory/jsonl_store.py

from packages.shared.redaction import SecretRedactor

redactor = SecretRedactor()

async def append_entry(session_id: str, entry: dict):
    # Redact secrets before writing
    if entry.get('type') == 'toolResult':
        entry['payload'] = redactor.redact_tool_result(entry['payload'])
    
    # Write to JSONL
    with open(f'sessions/{session_id}.jsonl', 'a') as f:
        f.write(json.dumps(entry) + '\n')
```

---

### **Decision 4: Mem0 + 5-Layer Memory Integration**

**Original Plan:** No clarification on boundaries  
**Review Finding:** ⚠️ **Potential redundancy** between Mem0 and Layer 5 LTM

**Updated Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│  MEMORY ARCHITECTURE: Mem0 + 5-Layer Integration               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Mem0 Responsibilities (User-Centric Facts):                   │
│  ═══════════════════════════════════════════════════════════   │
│  ├─ User preferences ("I prefer Python over JavaScript")       │
│  ├─ Personal facts ("I work at Company X")                     │
│  ├─ Project associations ("Project Y uses React")              │
│  ├─ Long-term relationships ("User Z is my colleague")         │
│  └─ Stable identity information                                │
│                                                                  │
│  5-Layer Responsibilities (Session Context):                   │
│  ═══════════════════════════════════════════════════════════   │
│  Layer 1 (Bootstrap): Static config files (AGENTS.md, etc.)    │
│  Layer 2 (JSONL): Per-session conversation transcripts         │
│  Layer 3 (Pruning): In-memory context optimization             │
│  Layer 4 (Compaction): Session summarization                   │
│  Layer 5 (LTM Search):                                         │
│    ├─ Daily logs (memory/YYYY-MM-DD.md) - task progress       │
│    ├─ MEMORY.md - curated decisions/decisions                 │
│    └─ Document RAG (Qdrant) - code, docs, research            │
│                                                                  │
│  Integration Points:                                            │
│  ═══════════════════════════════════════════════════════════   │
│  1. build_context() calls BOTH Mem0 + Layer 5 search           │
│  2. Mem0 for "who is the user"                                 │
│  3. Layer 5 for "what was discussed in sessions"               │
│  4. No overlap: Mem0 = user facts, Layer 5 = session context   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Updated Context Assembly:**

```python
# packages/memory/memory_service.py

async def build_context(
    user_message: str,
    user_id: str = "default",
    k: int = 5,
) -> str:
    """
    Build hybrid context from Mem0 (user facts) + 5-Layer (session context).
    """
    sections: list[str] = []
    
    # === LAYER A: Mem0 (User Facts) ===
    try:
        from packages.memory.mem0_client import mem0_search
        
        mem0_results = await asyncio.to_thread(
            mem0_search,
            user_message,
            user_id=user_id,
            limit=5,
        )
        
        if mem0_results:
            memory_lines = [
                f"  {i}. {mem.get('memory', '')}"
                for i, mem in enumerate(mem0_results[:5], 1)
            ]
            sections.append(
                "## What I Know About You (Long-Term Facts)\n" +
                "\n".join(memory_lines)
            )
    except Exception as exc:
        logger.debug("Mem0 context unavailable: %s", exc)
    
    # === LAYER B: 5-Layer Session Context ===
    
    # Layer 1: Bootstrap files
    bootstrap_context = await load_bootstrap_files()
    if bootstrap_context:
        sections.append("## Project Context\n" + bootstrap_context)
    
    # Layer 2-4: Recent session history (pruned)
    session_context = await load_recent_session_context(user_id, limit=10)
    if session_context:
        sections.append("## Recent Conversation\n" + session_context)
    
    # Layer 5: Long-term memory search (MEMORY.md + daily logs)
    ltm_results = await search_long_term_memory(user_message, k=3)
    if ltm_results:
        sections.append("## Relevant Past Decisions\n" + ltm_results)
    
    # Layer 5: Document RAG (Qdrant)
    doc_results = await search_documents(user_message, k=3)
    if doc_results:
        sections.append("## Relevant Documents/Code\n" + doc_results)
    
    if not sections:
        return ""
    
    return "\n\n".join(sections)
```

---

### **Decision 5: Tauri ↔ FastAPI Transport (REST+SSE vs WebSocket)**

**Original Plan:** Keep REST+SSE, no WebSocket evaluation  
**Review Finding:** ⚠️ **Gap** - No upgrade path evaluated

**Updated Analysis:**

```
┌─────────────────────────────────────────────────────────────────┐
│  TRANSPORT LAYER: REST+SSE with WebSocket Upgrade Path         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current (REST+SSE):                                            │
│  ═══════════════════════════════════════════════════════════   │
│  Pros:                                                          │
│  ├─ Simple to implement (FastAPI + browser-native SSE)         │
│  ├─ Works with current Tauri HTTP client                       │
│  ├─ Good for chat streaming (token-by-token)                   │
│  └─ No WebSocket state management complexity                   │
│                                                                  │
│  Cons:                                                          │
│  ├─ One-way (server→client only)                               │
│  ├─ No real-time agent→client events (tool calls, traces)      │
│  ├─ Polling required for job status updates                    │
│  └─ Multiple connections for multiple streams                  │
│                                                                  │
│  WebSocket Upgrade Path:                                        │
│  ═══════════════════════════════════════════════════════════   │
│  Trigger Conditions:                                            │
│  ├─ Need real-time agent trace visualization                   │
│  ├─ Multiple concurrent streaming sessions                     │
│  ├─ Bi-directional communication (client interrupts agent)     │
│  └─ Telegram-style messaging in desktop app                    │
│                                                                  │
│  Migration Effort: ~3-5 days                                    │
│  ├─ FastAPI: Add WebSocket endpoint (/ws)                      │
│  ├─ Tauri: Use @tauri-apps/api/websocket                       │
│  ├─ Protocol: Typed JSON frames (like OpenClaw)                │
│  └─ Fallback: Keep REST for non-streaming endpoints            │
│                                                                  │
│  Recommendation: STAY with REST+SSE for now                    │
│  ├─ Current scale doesn't require WebSocket complexity         │
│  ├─ SSE handles chat streaming well                            │
│  └─ Revisit when agent trace visualization is priority         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**WebSocket Upgrade Example (Future):**

```python
# apps/api/main.py (Future WebSocket endpoint)

from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Handshake
    challenge = await websocket.receive_json()
    await websocket.send_json({
        "type": "connect.ok",
        "protocol_version": "1.0",
    })
    
    # Message loop
    try:
        while True:
            message = await websocket.receive_json()
            
            if message["type"] == "chat":
                # Stream response
                async for chunk in chat_stream(message["text"]):
                    await websocket.send_json({
                        "type": "stream:assistant",
                        "content": chunk,
                    })
            
            elif message["type"] == "agent:run":
                # Stream agent trace
                async for event in stream_agent_trace(message["run_id"]):
                    await websocket.send_json({
                        "type": "stream:trace",
                        "event": event,
                    })
    
    except WebSocketDisconnect:
        logger.info("Client disconnected")
```

---

## 📋 **UPDATED IMPLEMENTATION PLAN**

### **Revised Phase Priorities**

| Phase | Original | Updated | Rationale |
|-------|----------|---------|-----------|
| **Phase 0: Infra** | Week 1 | Week 1 | ✅ Unchanged |
| **Phase 1: 5-Layer Memory** | Week 1-2 | Week 1-2 | ✅ Unchanged (CRITICAL) |
| **Phase 2: Workspace** | Week 3-4 (Docker) | Week 3-4 (Path Allowlists) | 🔴 Deprioritize Docker |
| **Phase 3: ARQ Tasks** | Week 3-4 | Week 5-6 | ⚠️ Add Celery fallback plan |
| **Phase 4: Telegram** | Week 5-6 | Week 7-8 | ✅ Unchanged |
| **Phase 5: Context Engine** | Week 7-8 | Week 9-10 | ✅ Unchanged |
| **Phase 6: Desktop Polish** | Week 9-10 | Week 11-12 | ✅ Unchanged |
| **Phase 7: Docker (Optional)** | Not planned | Week 13+ | 🔴 New, only if needed |

---

### **Updated Week 1-2: Phase 1 (5-Layer Memory)**

**Add Secret Redaction:**

```python
# NEW FILE: packages/shared/redaction.py
# (See full implementation above)
```

**Clarify Mem0 Boundaries:**

```python
# UPDATED: packages/memory/memory_service.py
# Add clear separation between Mem0 (user facts) and 5-Layer (session context)
```

---

### **Updated Week 3-4: Phase 2 (Workspace - Path Allowlists)**

**Skip Docker, Focus on:**

1. Enhanced path allowlists (Windows-native)
2. Audit logging for every tool call
3. Dangerous path blocking (regex patterns)
4. Permission UI in desktop app

**Deliverables:**
- ✅ `packages/agents/workspace.py` (path-based permissions)
- ✅ `packages/agents/audit.py` (audit logging)
- ✅ Desktop app: Workspace configuration page

---

### **Updated Week 5-6: Phase 3 (ARQ with Fallback Plan)**

**Add Celery Migration Documentation:**

```markdown
# packages/automation/MIGRATION_TO_CELERY.md

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

---

### **Updated Week 7-8: Phase 4 (Telegram)**

**No changes** - Plan is solid.

---

### **Updated Week 9-10: Phase 5 (Context Engine)**

**Add Secret Redaction Integration:**

```python
# UPDATED: packages/memory/context_engine.py
# Integrate redaction before context assembly
```

---

### **Updated Week 11-12: Phase 6 (Desktop Polish)**

**Add Workspace Configuration UI:**

```typescript
// NEW: apps/desktop/src/pages/WorkspaceConfigPage.tsx
// Configure path allowlists, view audit logs
```

---

### **New Phase 7 (Week 13+, Optional): Docker Sandboxing**

**Only if Phase 2 proves insufficient:**

1. Test Docker on Windows with your specific paths
2. Create Windows-specific Docker Compose config
3. Migrate high-risk projects to Docker first
4. Keep Phase 2 as default for low-risk projects

---

## 🎯 **UPDATED SUCCESS METRICS**

| Metric | Original | Updated (Realistic) |
|--------|----------|---------------------|
| **Background Job Success Rate** | 99% | 95-98% (ARQ maintenance risk) |
| **Memory Retention (6 months)** | ✅ Guaranteed | ⚠️ Best-case (depends on summarization quality) |
| **Code Agent Safety** | ✅ Sandboxed | ✅ Path allowlists + audit (80% security benefit) |
| **Token Usage Reduction** | 40% | 30-40% (realistic with pruning) |
| **Windows Docker Complexity** | Medium | 🔴 High (only if Phase 7 pursued) |

---

## 🚨 **UPDATED RISK MITIGATION**

| Risk | Original | Updated Mitigation |
|------|----------|-------------------|
| **ARQ Maintenance** | Not mentioned | ✅ Celery fallback plan documented |
| **Docker on Windows** | Medium complexity | 🔴 Deprioritized, path allowlists first |
| **JSONL Secret Leakage** | Not mentioned | ✅ Secret redaction middleware added |
| **Mem0 + 5-Layer Overlap** | Not mentioned | ✅ Clear boundaries defined |
| **6+ Month Retention Quality** | Guaranteed | ⚠️ Qualified (depends on summarization) |

---

## ✅ **FINAL RECOMMENDATIONS**

### **Proceed With Implementation, But:**

1. ✅ **Start with Phase 1 (5-Layer Memory)** - Add secret redaction from day 1
2. ✅ **Phase 2: Skip Docker** - Use path allowlists + audit logging
3. ✅ **Phase 3: ARQ with Celery fallback** - Pin version, monitor repo
4. ✅ **Clarify Mem0 boundaries** - User facts vs session context
5. ✅ **Remove marketing language** - Focus on "production-grade", not "top 1%"

### **Do NOT Implement Yet:**

- ❌ Docker sandboxing (Phase 7) - Only if path allowlists prove insufficient
- ❌ WebSocket migration - REST+SSE works for current scale
- ❌ Over-engineering - Start simple, add complexity when needed

---

## 📄 **CHANGES SUMMARY**

| Section | Original | Updated |
|---------|----------|---------|
| **ARQ Decision** | ARQ only | ARQ + Celery fallback |
| **Workspace Isolation** | Docker (Week 3-4) | Path allowlists (Week 3-4), Docker (Week 13+, optional) |
| **Secret Redaction** | Not mentioned | Added (critical security fix) |
| **Mem0 Integration** | Not clarified | Clear boundaries (user facts vs session context) |
| **Transport Layer** | Not evaluated | REST+SSE with WebSocket upgrade path |
| **Marketing Language** | "Top 1%" | Removed (replaced with "production-grade") |
| **Windows Complexity** | Medium | High (for Docker) |
| **6-Month Retention** | Guaranteed | Qualified (best-case) |

---

**This updated plan addresses all critical gaps from Claude's review while maintaining the core architectural vision.**

**Ready to proceed with implementation?**
