# Agent Knowledge Base Strategy

**Version:** 1.0  
**Date:** March 27, 2026  
**Based On:** Knowledge Activation Framework (arXiv:2603.14805v1) + Context Engineering Best Practices

---

## 🎯 **PROBLEM STATEMENT**

**Challenge:** Long conversations with AI agents accumulate context that:
1. Exceeds token limits → degraded response quality
2. Increases cognitive load → slower reasoning
3. Contains outdated information → incorrect assumptions
4. Lacks structured retrieval → inefficient context usage

**Goal:** Create a documentation system that:
- ✅ Preserves critical context without code dumps
- ✅ Enables efficient agent onboarding to conversation state
- ✅ Supports graph-based retrieval for relevant context
- ✅ Is reusable across different conversation sessions
- ✅ Minimizes token consumption while maximizing information density

---

## 📚 **RESEARCH-BACKED APPROACH**

### **Knowledge Activation Framework** (arXiv:2603.14805v1)

**Core Concept:** Atomic Knowledge Units (AKUs)

```
┌─────────────────────────────────────────────────────────┐
│  KNOWLEDGE ACTIVATION PIPELINE                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. CODIFICATION                                        │
│     Capture → Structure → Validate                      │
│                                                          │
│  2. COMPRESSION                                         │
│     Distill → Minimize → Optimize density               │
│                                                          │
│  3. INJECTION                                           │
│     Retrieve → Activate → Deliver                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Metrics:**
- **Knowledge Density (ρ)** = Actionable Information / Tokens Consumed
- **Target:** Maximize ρ while maintaining completeness

**Design Principles:**
1. **Atomicity** - One coherent concept per document
2. **Trigger Precision** - Clear activation conditions
3. **Context Rot Prevention** - Pre-structured knowledge

---

## 🗂️ **DOCUMENTATION STRUCTURE**

### **Folder: `docs/agent-knowledge/`**

```
docs/agent-knowledge/
├── 00-AGENT-ONBOARDING.md          # Quick start for new sessions
├── 01-PROJECT-STATE.md             # Current state & decisions
├── 02-USER-EXPECTATIONS.md         # User preferences & working style
├── 03-ARCHITECTURE-DECISIONS.md    # ADRs with rationale
├── 04-FILE-MANIFEST.md             # File directory with relevance
├── 05-ACTIVE-TASKS.md              # Current work in progress
├── 06-COMPLETED-PHASES.md          # Finished work summaries
├── 07-KNOWN-ISSUES.md              # Technical debt & gaps
├── 08-CONTEXT-RETRIEVAL.md         # How to use this knowledge base
└── graph/
    ├── knowledge-graph.json        # Structured relationships
    └── retrieval-index.json        # Quick lookup index
```

---

## 📄 **DOCUMENT TEMPLATES**

### **Template 1: Agent Onboarding (00-AGENT-ONBOARDING.md)**

```markdown
# Agent Onboarding Guide

**Session Context:** [Session ID / Date]
**Current Phase:** [Phase Number & Name]
**Last Updated:** [Timestamp]

## Quick State Summary (30-second read)

**What We're Building:** [1-2 sentence project vision]
**Current Status:** [Completed phases + current work]
**Immediate Next Step:** [Next actionable task]

## Critical Context (2-minute read)

### Architecture
- [Key architectural decisions - NO CODE]
- [Reference to ADR documents]

### User Preferences
- [Critical user working style preferences]
- [Communication preferences]

### File Locations
- See: `04-FILE-MANIFEST.md` for complete file inventory

## How to Get Up to Speed

1. **Read This First** → `00-AGENT-ONBOARDING.md` (you are here)
2. **Understand Project** → `01-PROJECT-STATE.md`
3. **Know the User** → `02-USER-EXPECTATIONS.md`
4. **Check Current Work** → `05-ACTIVE-TASKS.md`

## When to Read More

- **Starting new session** → Read sections 1-3 completely
- **Continuing work** → Read section 5 (Active Tasks)
- **Answering questions** → Use `08-CONTEXT-RETRIEVAL.md` index
```

---

### **Template 2: File Manifest (04-FILE-MANIFEST.md)**

```markdown
# File Manifest & Relevance Map

**Purpose:** Quick reference for what files exist and why they matter

**Last Updated:** [Timestamp]

## Core Application Files

### `apps/api/main.py`
- **Purpose:** FastAPI backend entry point
- **Relevance:** HIGH - All API routes registered here
- **Recent Changes:** [Date] - Added Telegram endpoints
- **Related Docs:** `03-ARCHITECTURE-DECISIONS.md#api-structure`
- **DO NOT:** Modify without checking route ordering

### `apps/desktop/src/App.tsx`
- **Purpose:** Desktop app navigation & routing
- **Relevance:** HIGH - All pages registered here
- **Recent Changes:** [Date] - Added Telegram page to nav
- **Related Docs:** `docs/frontend-architecture.md`

### `packages/memory/context_engine.py`
- **Purpose:** Adaptive context window management
- **Relevance:** MEDIUM - Token budget optimization
- **Recent Changes:** [Date] - Created for Phase 5
- **Related Docs:** `03-ARCHITECTURE-DECISIONS.md#context-engine`

## Configuration Files

### `infra/docker-compose.yml`
- **Purpose:** Docker services (Qdrant, Redis)
- **Relevance:** HIGH - Infrastructure definition
- **Recent Changes:** [Date] - Added Redis health check
- **DO NOT:** Change ports without updating all references

## Documentation Files

### `docs/agent-knowledge/00-AGENT-ONBOARDING.md`
- **Purpose:** Quick session onboarding
- **Relevance:** CRITICAL - Read this first in new sessions

[Continue for all critical files...]

## File Categories Summary

| Category | Count | Total Lines | Critical Files |
|----------|-------|-------------|----------------|
| Backend (Python) | 31 | ~10,500 | main.py, context_engine.py |
| Frontend (TS) | 5 | ~1,500 | App.tsx, HealthPage.tsx |
| Tests | 2 | ~1,650 | test_phase1_memory.py |
| Docs | 20+ | ~150,000 chars | 00-AGENT-ONBOARDING.md |

## Quick Lookup

**Looking for:**
- **API Routes** → `apps/api/main.py`, `apps/api/*_router.py`
- **UI Pages** → `apps/desktop/src/pages/*.tsx`
- **Memory System** → `packages/memory/*.py`
- **Background Jobs** → `packages/automation/arq_worker.py`
- **Tests** → `tests/test_phase*.py`
```

---

### **Template 3: Knowledge Graph (graph/knowledge-graph.json)**

```json
{
  "version": "1.0",
  "lastUpdated": "2026-03-27T00:00:00Z",
  "nodes": [
    {
      "id": "phase-1-memory",
      "type": "completed_phase",
      "title": "5-Layer Memory System",
      "summary": "Implemented bootstrap injection, JSONL transcripts, pruning, compaction, LTM search",
      "relevance": ["memory", "context", "rag"],
      "relatedFiles": ["packages/memory/*.py"],
      "relatedDocs": ["03-ARCHITECTURE-DECISIONS.md#memory-system"],
      "status": "complete",
      "testCoverage": "81%"
    },
    {
      "id": "phase-2-workspace",
      "type": "completed_phase",
      "title": "Workspace Isolation",
      "summary": "Path permissions, A2A registry, audit logging, 4 Tier 1 agents",
      "relevance": ["security", "agents", "permissions"],
      "relatedFiles": ["packages/agents/workspace.py", "packages/agents/a2a/*.py"],
      "status": "complete",
      "testCoverage": "75%"
    },
    {
      "id": "arq-redis-fix",
      "type": "critical_fix",
      "title": "ARQ/Redis Integration Fixes",
      "summary": "Fixed route ordering, RedisSettings parameters, ARQ pool usage",
      "relevance": ["redis", "arq", "background-tasks"],
      "relatedFiles": ["apps/api/job_router.py", "packages/automation/arq_worker.py"],
      "relatedDocs": ["HEALTH_DASHBOARD_CRITICAL_ANALYSIS.md"],
      "status": "resolved",
      "impact": "production-blocking"
    }
  ],
  "edges": [
    {
      "from": "phase-1-memory",
      "to": "phase-2-workspace",
      "type": "dependency",
      "description": "Workspace uses memory for context"
    },
    {
      "from": "arq-redis-fix",
      "to": "phase-3-background-tasks",
      "type": "enables",
      "description": "Fix enables background job monitoring"
    }
  ],
  "retrievalHints": {
    "whenWorkingOn": {
      "memory": ["phase-1-memory", "context-engine"],
      "agents": ["phase-2-workspace", "a2a-registry"],
      "redis": ["arq-redis-fix", "phase-3-background-tasks"]
    }
  }
}
```

---

### **Template 4: Context Retrieval Guide (08-CONTEXT-RETRIEVAL.md)**

```markdown
# Context Retrieval Guide

**Purpose:** How to quickly find relevant context without reading everything

## Retrieval Strategies

### 1. Keyword-Based (Fast)

**Use when:** You know what you're looking for

**Index:**
- `memory` → `01-PROJECT-STATE.md#memory-system`, `packages/memory/`
- `redis` → `HEALTH_DASHBOARD_CRITICAL_ANALYSIS.md`, `apps/api/job_router.py`
- `agents` → `03-ARCHITECTURE-DECISIONS.md#a2a`, `packages/agents/`

### 2. Graph-Based (Recommended)

**Use when:** You need related context

**Steps:**
1. Open `graph/knowledge-graph.json`
2. Find node matching your task
3. Follow `relatedFiles` and `relatedDocs` edges
4. Check `retrievalHints.whenWorkingOn` for common tasks

### 3. Temporal (For Recent Changes)

**Use when:** Understanding what changed recently

**Files to Check:**
1. `05-ACTIVE-TASKS.md` - Current work
2. `06-COMPLETED-PHASES.md` - Recent completions
3. `07-KNOWN-ISSUES.md` - New issues discovered

## Common Scenarios

### Starting New Session

**Read in Order:**
1. `00-AGENT-ONBOARDING.md` (5 min)
2. `05-ACTIVE-TASKS.md` (2 min)
3. `01-PROJECT-STATE.md` relevant section (5 min)

**Total Time:** 12 minutes to full context

### Continuing Work

**Read:**
1. `05-ACTIVE-TASKS.md` - What was in progress
2. Related files from manifest
3. Related ADRs if making architectural changes

### Answering User Questions

**Strategy:**
1. Check `02-USER-EXPECTATIONS.md` for preferences
2. Use graph retrieval for technical context
3. Reference `07-KNOWN-ISSUES.md` for limitations

## Token Optimization

**DO:**
- ✅ Read only relevant sections
- ✅ Use graph index for quick lookup
- ✅ Reference documents by ID, not content

**DON'T:**
- ❌ Read entire knowledge base
- ❌ Copy-paste code (reference file paths)
- ❌ Include outdated information

---

## Cognitive Load Principles

Based on research (arXiv:2603.14805v1):

1. **Atomicity** - Each document covers ONE concept
2. **Density** - Maximize information per token
3. **Trigger Precision** - Clear activation conditions
4. **Rot Prevention** - Pre-structured knowledge

**Target Knowledge Density (ρ):** >0.8 actionable info / tokens
```

---

## 🔄 **MAINTENANCE WORKFLOW**

### **After Each Conversation Session:**

1. **Update Active Tasks** (2 min)
   - What was completed
   - What's still in progress
   - Any blockers discovered

2. **Update File Manifest** (1 min)
   - New files created
   - Files significantly modified
   - Files deprecated

3. **Update Knowledge Graph** (3 min)
   - Add new nodes for completed work
   - Add edges showing relationships
   - Update retrieval hints

4. **Compress Old Context** (5 min)
   - Summarize conversation into `06-COMPLETED-PHASES.md`
   - Remove redundant information
   - Keep only decisions and outcomes

**Total Time:** 11 minutes per session

### **Every 5 Sessions:**

1. **Review and Prune** (15 min)
   - Remove outdated information
   - Merge related documents
   - Update cross-references

2. **Optimize Graph** (10 min)
   - Add missing relationships
   - Remove orphaned nodes
   - Update retrieval hints based on usage

**Total Time:** 25 minutes every 5 sessions

---

## 📊 **EFFICIENCY METRICS**

### **Context Retrieval Efficiency**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Onboarding Time** | <15 min | Time to read critical docs |
| **Retrieval Latency** | <2 min | Time to find relevant context |
| **Token Efficiency** | ρ > 0.8 | Actionable info / tokens |
| **Document Freshness** | <24h old | Time since last update |

### **Cognitive Load Reduction**

| Technique | Impact | Implementation |
|-----------|--------|----------------|
| **Atomic Documents** | High | One concept per file |
| **Graph Retrieval** | High | Structured relationships |
| **Temporal Indexing** | Medium | Recent changes highlighted |
| **Trigger Precision** | High | Clear activation conditions |

---

## 🎯 **IMPLEMENTATION CHECKLIST**

### **Phase 1: Create Structure (30 min)**

- [ ] Create `docs/agent-knowledge/` folder
- [ ] Create all template documents
- [ ] Populate `00-AGENT-ONBOARDING.md`
- [ ] Create initial `04-FILE-MANIFEST.md`

### **Phase 2: Populate Content (1 hour)**

- [ ] Summarize current project state → `01-PROJECT-STATE.md`
- [ ] Document user preferences → `02-USER-EXPECTATIONS.md`
- [ ] Extract architecture decisions → `03-ARCHITECTURE-DECISIONS.md`
- [ ] List completed phases → `06-COMPLETED-PHASES.md`
- [ ] Document known issues → `07-KNOWN-ISSUES.md`

### **Phase 3: Build Graph (30 min)**

- [ ] Create `graph/knowledge-graph.json`
- [ ] Add nodes for all phases
- [ ] Add edges showing relationships
- [ ] Add retrieval hints

### **Phase 4: Test & Iterate (Ongoing)**

- [ ] Use in next conversation session
- [ ] Measure onboarding time
- [ ] Refine based on what's actually useful
- [ ] Update maintenance workflow

---

## 📚 **REFERENCES**

1. **Knowledge Activation Framework** - arXiv:2603.14805v1 (March 2026)
   - Atomic Knowledge Units (AKUs)
   - Context Window Economy
   - Knowledge Density optimization

2. **Context Engineering Best Practices** - Towards AI (2026)
   - Compression strategies
   - Summarization with constraints
   - Information density optimization

3. **Graph-Based Retrieval for LLM Agents** - arXiv:2511.18194
   - Agent-as-a-Graph retrieval
   - Knowledge graph augmentation
   - Structured context representation

---

**This strategy is designed to be:**
- ✅ Research-backed (cognitive load optimization)
- ✅ Efficient (11 min maintenance per session)
- ✅ Scalable (works across multiple conversations)
- ✅ Agent-friendly (structured for quick retrieval)
- ✅ User-aligned (captures expectations and preferences)

**Next Step:** Execute Phase 1 - Create the folder structure and templates.
