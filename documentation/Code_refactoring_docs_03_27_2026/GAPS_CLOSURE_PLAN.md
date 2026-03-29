# PersonalAssist 2026: Critical Gaps Closure Plan

**Report Date:** March 27, 2026  
**Status:** Infrastructure ✅ Complete | Features ⏳ Pending  
**Priority:** Feature-Level Integration Required

---

## 🔍 **CURRENT STATE ASSESSMENT**

### **✅ What's Working (Infrastructure Layer)**

| Component | Status | Quality |
|-----------|--------|---------|
| QueryProvider wired up | ✅ Complete | Production-ready |
| Jobs Page | ✅ Complete | Production-ready |
| Health Dashboard | ✅ Complete | Production-ready |
| TanStack Query hooks | ✅ Available | Ready for use |

### **⏳ What's Pending (Feature Layer)**

| Gap | Component | Status | Impact |
|-----|-----------|--------|--------|
| **Gap 1 (partial)** | Hooks migration | ⏳ Pending | Medium (tech debt) |
| **Gap 2** | AgentTrace component | ⏳ Pending | Medium (visibility) |
| **Gap 4** | Telegram UI | ⏳ Pending | High (feature invisible) |
| **Gap 5** | Context Engine visibility | ⏳ Pending | Medium (observability) |
| **Gap 6** | Memory page expansion | ⏳ Pending | **Critical** (80% invisible) |
| **Gap 7** | Workspace permission tester | ⏳ Pending | Medium (security validation) |
| **Gap 8** | A2A agent UI | ⏳ Pending | High (agents invisible) |

---

## 🎯 **PRIORITIZATION FRAMEWORK**

Using **RICE scoring** (Reach, Impact, Confidence, Effort):

| Gap | Reach | Impact | Confidence | Effort | RICE Score | Priority |
|-----|-------|--------|------------|--------|------------|----------|
| **Gap 6** (Memory expansion) | 100% | High | 100% | Medium | **33.3** | **P0** |
| **Gap 8** (A2A agent UI) | 50% | High | 100% | Medium | **25** | **P0** |
| **Gap 4** (Telegram UI) | 30% | Medium | 100% | Medium | **15** | **P1** |
| **Gap 2** (AgentTrace) | 50% | Medium | 100% | Low | **20** | **P1** |
| **Gap 7** (Permission tester) | 20% | Medium | 100% | Low | **13.3** | **P2** |
| **Gap 5** (Context visibility) | 30% | Low | 100% | Medium | **10** | **P2** |
| **Gap 1** (Hooks migration) | 100% | Low | 100% | High | **12.5** | **P3** |

---

## 📋 **IMPLEMENTATION PLAN (Prioritized)**

### **Phase 7.1: Memory Page Expansion (P0 - Critical)** ⏱️ **6-8 hours**

**Problem:** Memory page shows only Mem0 facts (20% of system). Users can't see:
- JSONL session transcripts
- Bootstrap files
- Compaction history
- LTM search across all layers

**Solution:** Expand Memory page with tabs for all 5 layers

**Implementation:**

```typescript
// apps/desktop/src/pages/MemoryPage.tsx

type MemoryTab = 'facts' | 'sessions' | 'bootstrap' | 'compaction' | 'search';

function MemoryPage() {
  const [activeTab, setActiveTab] = useState<MemoryTab>('facts');
  
  return (
    <div>
      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tab value="facts" label="Facts (Mem0)" />
        <Tab value="sessions" label="Sessions" />
        <Tab value="bootstrap" label="Bootstrap Files" />
        <Tab value="compaction" label="Compaction" />
        <Tab value="search" label="Search" />
      </Tabs>
      
      {activeTab === 'facts' && <Mem0FactsTab />}
      {activeTab === 'sessions' && <SessionTranscriptsTab />}
      {activeTab === 'bootstrap' && <BootstrapFilesTab />}
      {activeTab === 'compaction' && <CompactionHistoryTab />}
      {activeTab === 'search' && <LTMSearchTab />}
    </div>
  );
}
```

**API Endpoints Needed:**
```python
# apps/api/main.py

@app.get("/memory/sessions/{session_id}")
async def get_session_transcript(session_id: str):
    """Get JSONL session transcript"""
    pass

@app.get("/memory/bootstrap")
async def get_bootstrap_files():
    """Get bootstrap file contents"""
    pass

@app.get("/memory/compaction/history")
async def get_compaction_history():
    """Get compaction history"""
    pass

@app.post("/memory/search")
async def search_ltm(query: str, k: int = 10):
    """Search across all memory layers"""
    pass
```

**Files to Create:**
- `apps/desktop/src/pages/MemoryPage.tsx` (rewrite with tabs)
- `apps/desktop/src/components/memory/Mem0FactsTab.tsx`
- `apps/desktop/src/components/memory/SessionTranscriptsTab.tsx`
- `apps/desktop/src/components/memory/BootstrapFilesTab.tsx`
- `apps/desktop/src/components/memory/CompactionHistoryTab.tsx`
- `apps/desktop/src/components/memory/LTMSearchTab.tsx`

**Files to Update:**
- `apps/api/main.py` (add 4 new endpoints)

**Testing:**
- Manual testing of each tab
- API endpoint validation
- Search functionality across layers

---

### **Phase 7.2: A2A Agent UI (P0 - Critical)** ⏱️ **4-6 hours**

**Problem:** A2A registry with 4 Tier 1 agents exists but has no UI. Users can't:
- Discover registered agents
- Delegate tasks to specific agents
- See agent capabilities
- Attach workspaces to agent runs

**Solution:** Add A2A tab to Agents page with agent discovery and task delegation

**Implementation:**

```typescript
// apps/desktop/src/pages/AgentsPage.tsx

type AgentsTab = 'crew' | 'a2a' | 'trace';

function AgentsPage() {
  const [activeTab, setActiveTab] = useState<AgentsTab>('crew');
  
  return (
    <div>
      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tab value="crew" label="Agent Crew" />
        <Tab value="a2a" label="A2A Agents" />
        <Tab value="trace" label="Execution Trace" />
      </Tabs>
      
      {activeTab === 'crew' && <AgentCrewTab />}
      {activeTab === 'a2a' && <A2AAgentsTab />}
      {activeTab === 'trace' && <AgentTraceViewer />}
    </div>
  );
}
```

**A2A Agents Tab Features:**
- List registered Tier 1 agents (Code Reviewer, Workspace Analyzer, etc.)
- Show agent cards with capabilities
- Task delegation form
- Workspace selector
- Execution results viewer

**API Endpoints Needed:**
```python
# apps/api/main.py

@app.get("/agents/a2a/list")
async def list_a2a_agents():
    """List registered A2A agents"""
    pass

@app.get("/agents/a2a/{agent_id}")
async def get_agent_card(agent_id: str):
    """Get agent card details"""
    pass

@app.post("/agents/a2a/{agent_id}/delegate")
async def delegate_task(agent_id: str, task: dict):
    """Delegate task to agent"""
    pass

@app.get("/agents/a2a/task/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    pass
```

**Files to Create:**
- `apps/desktop/src/components/agents/A2AAgentsTab.tsx`
- `apps/desktop/src/components/agents/AgentCard.tsx`
- `apps/desktop/src/components/agents/TaskDelegationForm.tsx`
- `apps/desktop/src/components/agents/AgentTraceViewer.tsx` (wrap AgentTrace.tsx)

**Files to Update:**
- `apps/desktop/src/pages/AgentsPage.tsx` (add tabs)
- `apps/api/main.py` (add 4 new endpoints)

---

### **Phase 7.3: AgentTrace Component Hookup (P1 - High)** ⏱️ **1-2 hours**

**Problem:** AgentTrace.tsx component built but not used anywhere

**Solution:** Wire up AgentTrace in AgentsPage trace tab

**Implementation:**

```typescript
// apps/desktop/src/components/agents/AgentTraceViewer.tsx

import AgentTrace from '../AgentTrace';

interface AgentTraceViewerProps {
  runId: string | null;
}

export default function AgentTraceViewer({ runId }: AgentTraceViewerProps) {
  if (!runId) {
    return (
      <div className="empty-state">
        <div>No active trace</div>
        <div>Run an agent to see execution trace</div>
      </div>
    );
  }
  
  return <AgentTrace runId={runId} />;
}
```

**Files to Update:**
- `apps/desktop/src/pages/AgentsPage.tsx` (pass runId to AgentTraceViewer)

---

### **Phase 7.4: Telegram Settings UI (P1 - High)** ⏱️ **4-6 hours**

**Problem:** Telegram gateway complete but no UI for configuration

**Solution:** Add Telegram tab to Settings page (or create new Telegram page)

**Implementation:**

```typescript
// apps/desktop/src/pages/TelegramPage.tsx

function TelegramPage() {
  const [botToken, setBotToken] = useState("");
  const [dmPolicy, setDmPolicy] = useState("pairing");
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [connectedUsers, setConnectedUsers] = useState([]);
  
  return (
    <div>
      <h1>Telegram Integration</h1>
      
      {/* Bot Configuration */}
      <section>
        <h2>Bot Configuration</h2>
        <input
          type="password"
          value={botToken}
          onChange={(e) => setBotToken(e.target.value)}
          placeholder="Enter bot token from @BotFather"
        />
        <button onClick={handleSaveToken}>Save Token</button>
      </section>
      
      {/* DM Policy */}
      <section>
        <h2>DM Policy</h2>
        <select value={dmPolicy} onChange={(e) => setDmPolicy(e.target.value)}>
          <option value="pairing">Pairing (require approval)</option>
          <option value="allowlist">Allowlist only</option>
          <option value="open">Open (anyone can message)</option>
        </select>
      </section>
      
      {/* Pending Approvals */}
      {dmPolicy === 'pairing' && (
        <section>
          <h2>Pending Approvals</h2>
          {pendingApprovals.map(user => (
            <div key={user.telegram_id}>
              <div>{user.telegram_name} (@{user.username})</div>
              <button onClick={() => handleApprove(user.telegram_id)}>
                Approve
              </button>
            </div>
          ))}
        </section>
      )}
      
      {/* Connected Users */}
      <section>
        <h2>Connected Users</h2>
        {connectedUsers.map(user => (
          <div key={user.telegram_id}>
            <div>{user.telegram_name}</div>
            <div>Last active: {user.last_message_at}</div>
          </div>
        ))}
      </section>
      
      {/* Test Message */}
      <section>
        <h2>Test Connection</h2>
        <button onClick={handleTestMessage}>Send Test Message</button>
      </section>
    </div>
  );
}
```

**API Endpoints Needed:**
```python
# apps/api/main.py

@app.get("/telegram/config")
async def get_telegram_config():
    """Get Telegram configuration"""
    pass

@app.post("/telegram/config")
async def update_telegram_config(config: dict):
    """Update Telegram configuration"""
    pass

@app.get("/telegram/users")
async def list_telegram_users():
    """List all Telegram users"""
    pass

@app.get("/telegram/users/pending")
async def list_pending_approvals():
    """List pending approval requests"""
    pass

@app.post("/telegram/users/{telegram_id}/approve")
async def approve_telegram_user(telegram_id: str):
    """Approve Telegram user"""
    pass

@app.post("/telegram/test")
async def send_test_message():
    """Send test message to verify bot"""
    pass
```

**Files to Create:**
- `apps/desktop/src/pages/TelegramPage.tsx`
- `apps/desktop/src/components/telegram/BotConfigForm.tsx`
- `apps/desktop/src/components/telegram/UserApprovalList.tsx`
- `apps/desktop/src/components/telegram/ConnectedUsersList.tsx`

**Files to Update:**
- `apps/api/main.py` (add 6 new endpoints)
- `apps/desktop/src/App.tsx` (add Telegram to nav)

---

### **Phase 7.5: Workspace Permission Tester (P2 - Medium)** ⏱️ **2-3 hours**

**Problem:** API endpoint exists but no UI to test permissions

**Solution:** Add permission tester modal to Workspace page

**Implementation:**

```typescript
// apps/desktop/src/pages/WorkspacePage.tsx

function WorkspacePage() {
  const [showPermissionTester, setShowPermissionTester] = useState(false);
  const [testPath, setTestPath] = useState("");
  const [testAction, setTestAction] = useState("read");
  const [testResult, setTestResult] = useState(null);
  
  const handleTestPermission = async () => {
    const response = await fetch(`http://127.0.0.1:8000/workspaces/${projectId}/check-permission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: testPath,
        action: testAction,
      }),
    });
    const result = await response.json();
    setTestResult(result);
  };
  
  return (
    <div>
      {/* ... existing workspace content ... */}
      
      <button onClick={() => setShowPermissionTester(true)}>
        🔒 Test Permissions
      </button>
      
      {showPermissionTester && (
        <Modal onClose={() => setShowPermissionTester(false)}>
          <h2>Permission Tester</h2>
          
          <input
            type="text"
            value={testPath}
            onChange={(e) => setTestPath(e.target.value)}
            placeholder="Path to test (e.g., src/main.py)"
          />
          
          <select value={testAction} onChange={(e) => setTestAction(e.target.value)}>
            <option value="read">Read</option>
            <option value="write">Write</option>
            <option value="execute">Execute</option>
          </select>
          
          <button onClick={handleTestPermission}>Test</button>
          
          {testResult && (
            <div className={`result ${testResult.allowed ? 'success' : 'error'}`}>
              <div>Allowed: {testResult.allowed ? '✅ Yes' : '❌ No'}</div>
              <div>Reason: {testResult.reason}</div>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}
```

**Files to Update:**
- `apps/desktop/src/pages/WorkspacePage.tsx` (add permission tester modal)

---

### **Phase 7.6: Context Engine Visibility (P2 - Medium)** ⏱️ **3-4 hours**

**Problem:** Context engine working but no visibility into token usage, active layers, compaction status

**Solution:** Add context stats to Health page or create dedicated Context tab

**Implementation:**

```typescript
// apps/desktop/src/pages/HealthPage.tsx (add section)

function HealthPage() {
  const [contextStats, setContextStats] = useState(null);
  
  useEffect(() => {
    const fetchContextStats = async () => {
      const response = await fetch('http://127.0.0.1:8000/context/stats');
      const stats = await response.json();
      setContextStats(stats);
    };
    fetchContextStats();
  }, []);
  
  return (
    <div>
      {/* ... existing health content ... */}
      
      {contextStats && (
        <section>
          <h2>Context Engine Stats</h2>
          
          <div>
            <div>Current Tokens: {contextStats.current_tokens}</div>
            <div>Available Tokens: {contextStats.available_tokens}</div>
            <div>Usage: {contextStats.usage_percent}%</div>
            <ProgressBar value={contextStats.usage_percent} />
          </div>
          
          <div>
            <div>Active Layers:</div>
            {contextStats.active_layers.map(layer => (
              <div key={layer}>
                <Badge>{layer}</Badge>
              </div>
            ))}
          </div>
          
          <div>
            <div>Compaction Status:</div>
            <div>
              {contextStats.should_compact ? (
                <Badge color="warning">Compaction Recommended</Badge>
              ) : (
                <Badge color="success">Healthy</Badge>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
```

**API Endpoint Needed:**
```python
# apps/api/main.py

@app.get("/context/stats")
async def get_context_stats():
    """Get context engine statistics"""
    from packages.memory.context_engine import ContextEngine
    
    # Get current session context
    engine = ContextEngine(session_id="current", model="local")
    
    # Return stats
    return {
        "current_tokens": 0,
        "available_tokens": 8000,
        "usage_percent": 0,
        "active_layers": ["bootstrap", "mem0", "qdrant"],
        "should_compact": False,
    }
```

**Files to Update:**
- `apps/desktop/src/pages/HealthPage.tsx` (add context stats section)
- `apps/api/main.py` (add 1 new endpoint)

---

### **Phase 7.7: Hooks Migration (P3 - Low)** ⏱️ **4-6 hours**

**Problem:** Existing pages use direct API calls instead of TanStack Query hooks

**Solution:** Migrate remaining pages to use hooks (technical debt cleanup)

**Pages to Migrate:**
1. MemoryPage.tsx → use `useMemories()`, `useMemoryHealth()`
2. ModelsPage.tsx → use `useModels()`, `useActiveModel()`
3. WorkspacePage.tsx → use `useWorkspaces()`, `useWorkspaceAuditLog()`

**Implementation:**
```typescript
// Before
function MemoryPage() {
  const [memories, setMemories] = useState([]);
  
  useEffect(() => {
    getAllMemories().then(setMemories);
  }, []);
}

// After
function MemoryPage() {
  const { data: memoriesData } = useMemories();
  const memories = memoriesData?.memories || [];
}
```

**Files to Update:**
- `apps/desktop/src/pages/MemoryPage.tsx`
- `apps/desktop/src/pages/ModelsPage.tsx`
- `apps/desktop/src/pages/WorkspacePage.tsx`

---

## 📊 **EFFORT ESTIMATION**

| Phase | Priority | Estimated Hours | Dependencies |
|-------|----------|----------------|--------------|
| **7.1** Memory Expansion | P0 | 6-8h | Backend API endpoints |
| **7.2** A2A Agent UI | P0 | 4-6h | Backend API endpoints |
| **7.3** AgentTrace Hookup | P1 | 1-2h | None |
| **7.4** Telegram UI | P1 | 4-6h | Backend API endpoints |
| **7.5** Permission Tester | P2 | 2-3h | None |
| **7.6** Context Visibility | P2 | 3-4h | Backend API endpoint |
| **7.7** Hooks Migration | P3 | 4-6h | None |
| **Total** | | **24-35 hours** | |

**Timeline:** 4-6 working days (with focused effort)

---

## 🎯 **RECOMMENDED EXECUTION ORDER**

### **Day 1-2: Critical Features (P0)**
- Memory page expansion (7.1)
- A2A agent UI (7.2)

### **Day 3: High Priority (P1)**
- AgentTrace hookup (7.3) - 1-2h
- Telegram UI (7.4) - 4-6h

### **Day 4: Medium Priority (P2)**
- Permission tester (7.5) - 2-3h
- Context visibility (7.6) - 3-4h

### **Day 5: Polish (P3)**
- Hooks migration (7.7) - 4-6h
- Testing and bug fixes

---

## ✅ **SUCCESS CRITERIA**

### **After Phase 7.1-7.2 (Day 1-2):**
- ✅ Memory page shows all 5 layers
- ✅ Users can view session transcripts
- ✅ Users can see bootstrap files
- ✅ A2A agents discoverable
- ✅ Task delegation working

### **After Phase 7.3-7.4 (Day 3):**
- ✅ AgentTrace visible during runs
- ✅ Telegram configurable via UI
- ✅ Pairing flow complete

### **After Phase 7.5-7.6 (Day 4):**
- ✅ Permission tester available
- ✅ Context stats visible
- ✅ Token budget monitoring

### **After Phase 7.7 (Day 5):**
- ✅ All pages use TanStack Query
- ✅ No duplicate fetch logic
- ✅ Codebase consistent

---

## 📝 **CONCLUSION**

**Current State:**
- ✅ Infrastructure complete (QueryProvider, Jobs, Health)
- ⏳ Feature gaps identified and prioritized
- ⏳ Implementation plan created

**Recommended Approach:**
1. **Day 1-2:** P0 features (Memory expansion, A2A UI)
2. **Day 3:** P1 features (AgentTrace, Telegram)
3. **Day 4:** P2 features (Permission tester, Context visibility)
4. **Day 5:** P3 cleanup (Hooks migration) + testing

**This is a 4-6 day sprint to close all remaining gaps and achieve 100% feature completeness.**

---

**Plan End | March 27, 2026 | Ready for Implementation**
