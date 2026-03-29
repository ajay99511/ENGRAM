# File Manifest & Relevance Map

**Purpose:** Quick reference for what files exist and why they matter  
**Last Updated:** March 27, 2026  
**Total Files:** 31 Python, 5 TypeScript, 20+ Documentation

---

## 📁 Core Application Files

### Backend (Python)

#### `apps/api/main.py`
- **Purpose:** FastAPI backend entry point, all API routes registered here
- **Relevance:** CRITICAL - Modified in every backend phase
- **Recent Changes:** Mar 27 - Added Telegram endpoints, fixed route ordering
- **Related Docs:** `03-ARCHITECTURE-DECISIONS.md#api-structure`
- **DO NOT:** Modify route order (specific before parameterized)

#### `apps/api/job_router.py`
- **Purpose:** ARQ job monitoring API endpoints
- **Relevance:** HIGH - Fixed critical Redis integration issues
- **Recent Changes:** Mar 27 - Complete rewrite with ARQ best practices
- **Related Docs:** `../../HEALTH_DASHBOARD_CRITICAL_ANALYSIS.md`
- **Key Fixes:** Route ordering, RedisSettings params, ARQ pool usage

#### `apps/api/workspace_router.py`
- **Purpose:** Workspace management API endpoints
- **Relevance:** HIGH - Workspace CRUD, audit logs, permission testing
- **Recent Changes:** Mar 27 - Added for Phase 7.5

#### `packages/automation/arq_worker.py`
- **Purpose:** ARQ worker configuration, job definitions, cron schedules
- **Relevance:** HIGH - Background task system
- **Recent Changes:** Mar 27 - Added job definitions, cron schedules
- **Related Docs:** `03-ARCHITECTURE-DECISIONS.md#background-tasks`

#### `packages/memory/context_engine.py`
- **Purpose:** Adaptive context window management, token budget
- **Relevance:** MEDIUM - Phase 5 implementation
- **Recent Changes:** Mar 27 - Created for context engine
- **Related Docs:** `03-ARCHITECTURE-DECISIONS.md#context-engine`

#### `packages/memory/bootstrap.py`
- **Purpose:** Bootstrap file injection (Layer 1)
- **Relevance:** HIGH - Memory system foundation
- **Recent Changes:** Mar 27 - Part of Phase 7.1 expansion

#### `packages/memory/jsonl_store.py`
- **Purpose:** JSONL transcript storage (Layer 2)
- **Relevance:** HIGH - Session history with secret redaction
- **Recent Changes:** Mar 27 - Part of Phase 7.1 expansion

#### `packages/memory/pruning.py`
- **Purpose:** Session pruning (Layer 3)
- **Relevance:** MEDIUM - TTL-based in-memory pruning
- **Recent Changes:** Mar 27 - Part of Phase 7.1 expansion

#### `packages/memory/compaction.py`
- **Purpose:** Adaptive compaction (Layer 4)
- **Relevance:** MEDIUM - Summarization with fallback
- **Recent Changes:** Mar 27 - Part of Phase 7.1 expansion

#### `packages/agents/workspace.py`
- **Purpose:** Workspace configuration manager
- **Relevance:** HIGH - Path permissions, audit logging
- **Recent Changes:** Mar 27 - Phase 7.5 permission tester support

#### `packages/agents/a2a/registry.py`
- **Purpose:** A2A agent registry
- **Relevance:** HIGH - Agent discovery and delegation
- **Recent Changes:** Mar 27 - Phase 7.2 implementation

#### `packages/agents/a2a/agents.py`
- **Purpose:** Tier 1 agent card definitions
- **Relevance:** MEDIUM - 4 pre-defined agents
- **Recent Changes:** Mar 27 - Phase 7.2 implementation

#### `packages/shared/redaction.py`
- **Purpose:** Secret redaction middleware
- **Relevance:** CRITICAL - Security feature (10+ patterns)
- **Recent Changes:** Mar 27 - Used in all phases

### Frontend (TypeScript)

#### `apps/desktop/src/App.tsx`
- **Purpose:** Desktop app navigation and routing
- **Relevance:** CRITICAL - All pages registered here
- **Recent Changes:** Mar 27 - Added Telegram page, Health page
- **Related Docs:** `docs/frontend-architecture.md`

#### `apps/desktop/src/pages/HealthPage.tsx`
- **Purpose:** System health dashboard
- **Relevance:** HIGH - Fixed Redis/ARQ status detection
- **Recent Changes:** Mar 27 - Complete rewrite with proper endpoints
- **Related Docs:** `../../HEALTH_DASHBOARD_CRITICAL_ANALYSIS.md`

#### `apps/desktop/src/pages/MemoryPage.tsx`
- **Purpose:** Memory system UI (5 tabs)
- **Relevance:** HIGH - All 5 memory layers visible
- **Recent Changes:** Mar 27 - Expanded for Phase 7.1

#### `apps/desktop/src/pages/AgentsPage.tsx`
- **Purpose:** Agent UI (3 tabs: Crew, A2A, Trace)
- **Relevance:** HIGH - A2A agent discovery
- **Recent Changes:** Mar 27 - Expanded for Phase 7.2

#### `apps/desktop/src/pages/TelegramPage.tsx`
- **Purpose:** Telegram configuration UI
- **Relevance:** MEDIUM - Bot token, DM policy, user management
- **Recent Changes:** Mar 27 - Created for Phase 7.4

#### `apps/desktop/src/pages/JobsPage.tsx`
- **Purpose:** Background job monitoring
- **Relevance:** MEDIUM - Job stats, manual enqueue
- **Recent Changes:** Mar 27 - Created for Phase 7.3

#### `apps/desktop/src/lib/hooks.ts`
- **Purpose:** TanStack Query custom hooks
- **Relevance:** MEDIUM - Data fetching abstraction
- **Recent Changes:** Mar 27 - 10+ hooks defined

#### `apps/desktop/src/lib/QueryProvider.tsx`
- **Purpose:** TanStack Query provider
- **Relevance:** HIGH - Wired up in main.tsx
- **Recent Changes:** Mar 27 - Phase 7 integration

### Infrastructure

#### `infra/docker-compose.yml`
- **Purpose:** Docker services (Qdrant, Redis)
- **Relevance:** CRITICAL - Infrastructure definition
- **Recent Changes:** Mar 27 - Added Redis health check
- **DO NOT:** Change ports without updating all references

#### `requirements.txt`
- **Purpose:** Python dependencies
- **Relevance:** HIGH - All Python packages
- **Recent Changes:** Mar 27 - Added arq, redis, python-telegram-bot

### Tests

#### `tests/test_phase1_memory.py`
- **Purpose:** Phase 1 memory system tests
- **Relevance:** HIGH - 27 tests (22 passing, 81%)
- **Recent Changes:** Mar 27 - All tests passing

#### `tests/test_phase2_workspace.py`
- **Purpose:** Phase 2 workspace tests
- **Relevance:** MEDIUM - 16 tests (12 passing, 75%)
- **Recent Changes:** Mar 27 - All tests passing

### Documentation

#### `docs/agent-knowledge/00-AGENT-ONBOARDING.md`
- **Purpose:** Quick session onboarding
- **Relevance:** CRITICAL - Read this first in new sessions
- **Recent Changes:** Mar 27 - Created

#### `docs/agent-knowledge/01-PROJECT-STATE.md`
- **Purpose:** Current project state
- **Relevance:** CRITICAL - What's done, what's next
- **Recent Changes:** Mar 27 - Created

#### `docs/agent-knowledge/02-USER-EXPECTATIONS.md`
- **Purpose:** User preferences and working style
- **Relevance:** HIGH - How to work with user
- **Recent Changes:** Mar 27 - Created

#### `HEALTH_DASHBOARD_CRITICAL_ANALYSIS.md`
- **Purpose:** Critical analysis of Redis/ARQ fixes
- **Relevance:** HIGH - Production-blocking issues fixed
- **Recent Changes:** Mar 27 - Created

#### `FINAL_INTEGRATION_SPRINT_REPORT.md`
- **Purpose:** Complete integration sprint summary
- **Relevance:** HIGH - Phases 7.1-7.5 completion
- **Recent Changes:** Mar 27 - Created

---

## 📊 File Categories Summary

| Category | Count | Total Lines | Critical Files |
|----------|-------|-------------|----------------|
| Backend (Python) | 31 | ~10,500 | main.py, job_router.py, context_engine.py |
| Frontend (TS) | 5 | ~1,500 | App.tsx, HealthPage.tsx, hooks.ts |
| Tests | 2 | ~1,650 | test_phase1_memory.py, test_phase2_workspace.py |
| Infrastructure | 2 | ~200 | docker-compose.yml, requirements.txt |
| Documentation | 20+ | ~150,000 chars | 00-AGENT-ONBOARDING.md, 01-PROJECT-STATE.md |

---

## 🔍 Quick Lookup by Task

### Working On: Memory System
- `packages/memory/*.py` - All memory components
- `apps/desktop/src/pages/MemoryPage.tsx` - UI
- `docs/agent-knowledge/03-ARCHITECTURE-DECISIONS.md#memory-system` - ADR

### Working On: Background Tasks
- `packages/automation/arq_worker.py` - Worker config
- `apps/api/job_router.py` - API endpoints
- `apps/desktop/src/pages/JobsPage.tsx` - UI
- `HEALTH_DASHBOARD_CRITICAL_ANALYSIS.md` - Fixes

### Working On: Telegram
- `packages/messaging/telegram_bot.py` - Bot service
- `apps/desktop/src/pages/TelegramPage.tsx` - UI
- `apps/api/main.py` - Webhook endpoint

### Working On: Health Dashboard
- `apps/desktop/src/pages/HealthPage.tsx` - UI
- `apps/api/job_router.py` - `/jobs/health`, `/jobs/stats`
- `HEALTH_DASHBOARD_CRITICAL_ANALYSIS.md` - Analysis

---

## 📍 File Location Quick Reference

**Backend:**
- API Routes: `apps/api/*_router.py`
- Core Logic: `packages/*/`
- Tests: `tests/test_phase*.py`

**Frontend:**
- Pages: `apps/desktop/src/pages/*.tsx`
- Components: `apps/desktop/src/components/`
- Utils: `apps/desktop/src/lib/`

**Infrastructure:**
- Docker: `infra/docker-compose.yml`
- Dependencies: `requirements.txt`, `package.json`

**Documentation:**
- Agent Knowledge: `docs/agent-knowledge/`
- Analysis Reports: `*_CRITICAL_ANALYSIS.md`, `*_REPORT.md`

---

**Status:** ✅ CURRENT AND MAINTAINED
