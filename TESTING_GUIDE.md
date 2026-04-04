# Testing Guide: PersonalAssist Agent System

**Date:** March 29, 2026  
**Version:** 0.3.0  
**Scope:** Phase 1 (Telegram Bot) + Phase 2 (System Monitor)  

---

## Prerequisites

### 1. Install Dependencies

```bash
cd C:\Agents\PersonalAssist

# Install Python dependencies
pip install psutil pywin32

# Verify installation
python -c "import psutil; print('psutil:', psutil.__version__)"
python -c "import win32evtlog; print('pywin32: OK')"
```

### 2. Start Required Services

```bash
# Start Qdrant (if using Docker)
docker-compose -f infra/docker-compose.yml up -d

# Start Redis (for ARQ jobs)
docker run -d -p 6379:6379 --name personalassist-redis redis:latest

# Verify services
curl http://localhost:6333  # Qdrant
curl http://localhost:6379  # Redis (should return error - ping with redis-cli)
```

### 3. Configure Environment

Create or update `.env` file:

```ini
# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
API_ACCESS_TOKEN=test-token-123

# Telegram Bot (optional - for Phase 1 testing)
# Get token from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_DM_POLICY=pairing

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=personal_memories

# Models
DEFAULT_LOCAL_MODEL=ollama/llama3.2
DEFAULT_REMOTE_MODEL=gemini/gemini-2.5-flash-lite
```

---

## Phase 1: Telegram Bot Testing

### 1.1 Start the API

```bash
# Start API server
python -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

# Wait for startup message:
# "INFO:     Starting up PersonalAssist API..."
# "INFO:     Auto-starting Telegram bot from saved config" (if config exists)
```

### 1.2 Test Configuration Endpoints

**Get Current Config:**
```bash
curl http://localhost:8000/telegram/config ^
  -H "x-api-token: test-token-123" | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "bot_token_set": false,
  "dm_policy": "pairing",
  "token_display": "(not configured)"
}
```

**Save Configuration:**
```bash
$body = @{
  bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
  dm_policy = "pairing"
} | ConvertTo-Json

curl -X POST http://localhost:8000/telegram/config ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "status": "reloading",
  "message": "Bot is reloading with new token. Check /telegram/status for updates.",
  "dm_policy": "pairing"
}
```

### 1.3 Test Bot Status Endpoint

**Get Status:**
```bash
curl http://localhost:8000/telegram/status ^
  -H "x-api-token: test-token-123" | ConvertFrom-Json
```

**Expected Responses:**

**Starting:**
```json
{
  "state": "starting",
  "dm_policy": "pairing"
}
```

**Running:**
```json
{
  "state": "running",
  "dm_policy": "pairing",
  "started_at": "2026-03-29T10:00:00.000000",
  "uptime_seconds": 120
}
```

**Error (invalid token):**
```json
{
  "state": "error",
  "dm_policy": "pairing",
  "error_message": "Unauthorized"
}
```

### 1.4 Test Bot Lifecycle

**Start Bot:**
```bash
$body = @{
  bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
} | ConvertTo-Json

curl -X POST http://localhost:8000/telegram/start ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body | ConvertFrom-Json
```

**Stop Bot:**
```bash
curl -X POST http://localhost:8000/telegram/stop ^
  -H "x-api-token: test-token-123" | ConvertFrom-Json
```

**Reload Bot:**
```bash
$body = @{
  bot_token = "999999:XYZ-ABC123def456GHI789jkl012MNO"
  dm_policy = "open"
} | ConvertTo-Json

curl -X POST http://localhost:8000/telegram/reload ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body | ConvertFrom-Json
```

### 1.5 Test User Management

**List Users:**
```bash
curl http://localhost:8000/telegram/users ^
  -H "x-api-token: test-token-123" | ConvertFrom-Json
```

**List Pending:**
```bash
curl http://localhost:8000/telegram/users/pending ^
  -H "x-api-token: test-token-123" | ConvertFrom-Json
```

**Approve User:**
```bash
curl -X POST http://localhost:8000/telegram/users/123456789/approve ^
  -H "x-api-token: test-token-123" | ConvertFrom-Json
```

### 1.6 Test Message

**Send Test Message:**
```bash
curl -X POST http://localhost:8000/telegram/test ^
  -H "x-api-token: test-token-123" | ConvertFrom-Json
```

**Expected (bot running):**
```json
{
  "status": "sent",
  "message": "Test message sent to 0 user(s)"
}
```

**Expected (bot not running):**
```json
{
  "status": "error",
  "message": "Bot is not running. Start bot via /telegram/start"
}
```

### 1.7 Test Desktop UI

1. **Start Desktop App:**
```bash
cd apps/desktop
npm install  # First time only
npm run dev
```

2. **Open Browser:** `http://localhost:1420`

3. **Navigate to Telegram Page**

4. **Verify:**
   - [ ] Status card shows current bot state
   - [ ] Status icon changes (🟢 running, ⚫ stopped, 🔴 error)
   - [ ] Uptime displays when running
   - [ ] Start button enabled when stopped
   - [ ] Stop/Reload buttons enabled when running
   - [ ] Config form saves successfully
   - [ ] Status auto-refreshes (every 3 seconds when active)
   - [ ] Action messages display (success/error/info)

---

## Phase 2: System Monitor Testing

### 2.1 Test System Monitor Endpoints

**Test CPU Info:**
```bash
curl http://localhost:8000/system/cpu | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "usage_percent": 25.5,
  "cores_physical": 8,
  "cores_logical": 16,
  "frequency_mhz": 3200,
  "per_cpu_usage": [25.0, 26.0, 24.5, ...],
  "available": true,
  "timestamp": "2026-03-29T10:00:00"
}
```

**Test Memory Info:**
```bash
curl http://localhost:8000/system/memory | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "total_gb": 16.0,
  "available_gb": 8.5,
  "used_gb": 7.5,
  "usage_percent": 46.9,
  "swap_total_gb": 2.0,
  "swap_used_gb": 0.5,
  "available": true,
  "timestamp": "2026-03-29T10:00:00"
}
```

**Test Disk Info:**
```bash
curl http://localhost:8000/system/disk | ConvertFrom-Json
```

**Expected Response:**
```json
[
  {
    "device": "C:",
    "mountpoint": "C:\\",
    "total_gb": 512.0,
    "used_gb": 256.0,
    "free_gb": 256.0,
    "usage_percent": 50.0,
    "fstype": "NTFS"
  }
]
```

**Test Battery Info:**
```bash
curl http://localhost:8000/system/battery | ConvertFrom-Json
```

**Expected (laptop):**
```json
{
  "present": true,
  "percent": 85,
  "time_left_minutes": 120,
  "power_plugged": true,
  "status": "charging",
  "available": true,
  "timestamp": "2026-03-29T10:00:00"
}
```

**Expected (desktop):**
```json
{
  "present": false,
  "status": "no_battery",
  "available": true,
  "timestamp": "2026-03-29T10:00:00"
}
```

**Test System Summary:**
```bash
curl http://localhost:8000/system/summary | ConvertFrom-Json
```

**Expected:** Combined CPU, memory, disk, battery info

**Test Processes:**
```bash
curl "http://localhost:8000/system/processes?limit=10&sort_by=memory" | ConvertFrom-Json
```

**Expected:**
```json
[
  {
    "pid": 1234,
    "name": "chrome.exe",
    "cpu_percent": 5.2,
    "memory_percent": 8.5,
    "memory_mb": 1342,
    "status": "running"
  }
]
```

**Test Event Logs (Windows only):**
```bash
curl "http://localhost:8000/system/logs?log_name=System&max_entries=10&hours_back=24" | ConvertFrom-Json
```

**Expected:**
```json
[
  {
    "time_created": "2026-03-29T10:00:00",
    "source": "Service Control Manager",
    "event_id": 7036,
    "event_type": "Information",
    "message": "The Windows Update service entered the running state.",
    "computer": "DESKTOP-ABC123"
  }
]
```

### 2.2 Test Agent Tool Integration

**Test Tool Execution:**
```bash
# Via API (if /agents/run endpoint available)
$body = @{
  message = "What's my current CPU usage?"
  model = "local"
} | ConvertTo-Json

curl -X POST http://localhost:8000/agents/run ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body | ConvertFrom-Json
```

**Expected:** Agent should call `get_cpu_info` tool and respond with CPU usage

### 2.3 Test Without Dependencies

**Uninstall psutil:**
```bash
pip uninstall psutil -y
```

**Test Endpoints (should return errors):**
```bash
curl http://localhost:8000/system/cpu | ConvertFrom-Json
```

**Expected:**
```json
{
  "error": "psutil not installed. Run: pip install psutil",
  "available": false
}
```

**Reinstall psutil:**
```bash
pip install psutil
```

---

## Integration Testing

### 3.1 Test API Documentation (Swagger UI)

1. **Open:** `http://localhost:8000/docs`

2. **Verify:**
   - [ ] `/telegram/*` endpoints documented
   - [ ] `/system/*` endpoints documented
   - [ ] Request/response schemas visible
   - [ ] "Try it out" buttons work
   - [ ] Authentication field present

### 3.2 Test API Health

**Basic Health:**
```bash
curl http://localhost:8000/health | ConvertFrom-Json
```

**Expected:**
```json
{
  "status": "ok",
  "version": "0.2.0"
}
```

**Memory Health:**
```bash
curl http://localhost:8000/memory/health | ConvertFrom-Json
```

**Expected:**
```json
{
  "status": "ok",
  "qdrant": "connected"
}
```

**Jobs Health:**
```bash
curl http://localhost:8000/jobs/health | ConvertFrom-Json
```

**Expected:**
```json
{
  "redis_connected": true,
  "arq_worker": "connected"
}
```

### 3.3 Test Chat Functionality

**Plain Chat:**
```bash
$body = @{
  message = "Hello"
  model = "local"
} | ConvertTo-Json

curl -X POST http://localhost:8000/chat ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body | ConvertFrom-Json
```

**Smart Chat:**
```bash
curl -X POST http://localhost:8000/chat/smart ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body | ConvertFrom-Json
```

---

## Performance Testing

### 4.1 Response Time

**Test with Measure-Command:**
```powershell
# Telegram status
Measure-Command { curl http://localhost:8000/telegram/status -H "x-api-token: test-token-123" }

# System summary
Measure-Command { curl http://localhost:8000/system/summary }

# CPU info (includes 1-second sampling)
Measure-Command { curl http://localhost:8000/system/cpu }
```

**Expected:**
- `/telegram/status`: <200ms
- `/system/memory`: <100ms
- `/system/cpu`: ~1100ms (1-second sampling)
- `/system/summary`: ~1200ms (parallel calls)

### 4.2 Concurrent Requests

**Test with concurrent requests:**
```powershell
# Start 10 concurrent requests
1..10 | ForEach-Object {
  Start-Job -ScriptBlock {
    curl http://localhost:8000/system/summary
  }
}

# Wait for all to complete
Get-Job | Wait-Job | Receive-Job
```

**Expected:** All complete without errors

---

## Error Handling Testing

### 5.1 Invalid Token Format

```bash
$body = @{
  bot_token = "invalid-token"
  dm_policy = "pairing"
} | ConvertTo-Json

curl -X POST http://localhost:8000/telegram/config ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body
```

**Expected:** HTTP 422 with validation error

### 5.2 Invalid DM Policy

```bash
$body = @{
  bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
  dm_policy = "invalid"
} | ConvertTo-Json

curl -X POST http://localhost:8000/telegram/config ^
  -H "x-api-token: test-token-123" ^
  -H "Content-Type: application/json" ^
  -d $body
```

**Expected:** HTTP 422 with validation error

### 5.3 Missing Authentication

```bash
curl http://localhost:8000/telegram/status
```

**Expected:** HTTP 401 or allowed (if API token not set)

### 5.4 Invalid Query Parameters

```bash
curl "http://localhost:8000/system/processes?limit=1000&sort_by=invalid"
```

**Expected:** HTTP 422 with validation error

---

## Checklist Summary

### Phase 1: Telegram Bot

- [ ] Config endpoint returns current config
- [ ] Config save persists to file
- [ ] Config save triggers reload
- [ ] Status endpoint returns accurate state
- [ ] Status includes uptime when running
- [ ] Start bot works
- [ ] Stop bot works
- [ ] Reload bot works
- [ ] User list endpoint works
- [ ] Approve user works
- [ ] Test message works
- [ ] Desktop UI shows real-time status
- [ ] Desktop UI auto-polls when active
- [ ] Desktop UI lifecycle controls work
- [ ] Desktop UI action messages display

### Phase 2: System Monitor

- [ ] CPU endpoint returns metrics
- [ ] Memory endpoint returns metrics
- [ ] Disk endpoint returns metrics
- [ ] Battery endpoint returns metrics
- [ ] Network endpoint returns metrics
- [ ] Processes endpoint returns metrics
- [ ] Event logs endpoint returns entries (Windows)
- [ ] Summary endpoint combines all metrics
- [ ] Tools registered in TOOL_REGISTRY
- [ ] Agent can call system tools
- [ ] Graceful degradation without psutil

### Integration

- [ ] Swagger UI shows all endpoints
- [ ] API health endpoints work
- [ ] Chat endpoints work
- [ ] No breaking changes to existing functionality
- [ ] API starts without errors
- [ ] API shuts down gracefully
- [ ] Bot auto-starts on API restart (if config exists)

---

## Troubleshooting

### Common Issues

**1. "psutil not installed"**
```bash
pip install psutil
```

**2. "pywin32 not installed"**
```bash
pip install pywin32
```

**3. "API_ACCESS_TOKEN not set"**
```ini
# Add to .env
API_ACCESS_TOKEN=test-token-123
```

**4. "Qdrant not connected"**
```bash
docker-compose -f infra/docker-compose.yml up -d
```

**5. "Bot token invalid"**
- Get new token from @BotFather on Telegram
- Ensure format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

**6. "Port 8000 already in use"**
```bash
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## Next Steps After Testing

1. **Fix any failing tests**
2. **Document any issues found**
3. **Proceed to Phase 2E** (Desktop UI for system monitor)
4. **Proceed to Phase 3** (Autonomous Agent)

---

**Testing Status:** ⏳ Ready for Testing  
**Last Updated:** 2026-03-29
