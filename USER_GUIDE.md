# PersonalAssist User Guide

**Version:** 0.3.0  
**Last Updated:** March 29, 2026  

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Desktop App](#desktop-app)
3. [Telegram Bot](#telegram-bot)
4. [System Monitoring](#system-monitoring)
5. [Autonomous Agent](#autonomous-agent)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### What is PersonalAssist?

PersonalAssist is a local-first AI assistant with:
- **Long-term memory** - Remembers your preferences and conversations
- **Multi-model support** - Use local (Ollama) or cloud (Gemini, Claude) models
- **Telegram integration** - Chat with your AI via Telegram
- **System monitoring** - Monitor CPU, memory, disk, battery in real-time
- **Autonomous agent** - Automated codebase monitoring and research

### Prerequisites

- Windows 10/11
- Python 3.13+
- Node.js 18+ (for desktop app)
- Docker (optional, for Qdrant)

### Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start services:**
```bash
# Start Qdrant (vector database)
docker-compose -f infra/docker-compose.yml up -d

# Start Redis (for background jobs)
docker run -d -p 6379:6379 --name personalassist-redis redis:latest
```

3. **Configure environment:**
Create `.env` file:
```ini
API_ACCESS_TOKEN=your-secret-token
DEFAULT_LOCAL_MODEL=ollama/llama3.2
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

4. **Start API:**
```bash
python -m uvicorn apps.api.main:app --reload
```

5. **Start Desktop App:**
```bash
cd apps/desktop
npm install
npm run dev
```

6. **Open Desktop:** http://localhost:1420

---

## Desktop App

### Pages Overview

| Page | Description |
|------|-------------|
| **Chat** | AI conversations with memory |
| **Memory** | View and manage memories |
| **Models** | Switch between AI models |
| **Agents** | Run AI agents and autonomous tasks |
| **Health** | System health and metrics |
| **Telegram** | Telegram bot configuration |
| **Ingestion** | Index documents into memory |
| **Podcast** | Generate audio podcasts |
| **Workspace** | Manage code workspaces |
| **Jobs** | Monitor background jobs |

### Chat Page

**Features:**
- Stream responses in real-time
- Smart mode with memory context
- Conversation threads
- Model selection

**Usage:**
1. Type your message
2. Toggle "Smart Mode" for memory-aware responses
3. Toggle "Stream" for real-time output
4. Select model from dropdown
5. Press Enter or click Send

### Health Page

**Features:**
- Service status (API, Qdrant, Redis, ARQ)
- System metrics (CPU, Memory, Disk, Battery)
- Auto-refresh every 10-30 seconds

**Metrics Displayed:**
- **CPU:** Usage %, core count, frequency
- **Memory:** Used/Total GB, usage %
- **Disk:** Per-drive usage with progress bars
- **Battery:** Percentage, status, time remaining

### Telegram Page

**Features:**
- Bot configuration
- Real-time status
- User management
- Test message

**Setup:**
1. Get bot token from @BotFather on Telegram
2. Enter token in "Bot Token" field
3. Select DM Policy:
   - **Pairing:** Users need approval code
   - **Allowlist:** Only pre-approved users
   - **Open:** Anyone can message
4. Click "Save Configuration"
5. Click "Start" to start bot

### Agents Page

**Tabs:**
1. **Agent Crew** - Run Planner → Researcher → Synthesizer
2. **A2A Agents** - Delegate to specialized agents
3. **Autonomous** - Autonomous agent controls
4. **Execution Trace** - View agent execution

#### Autonomous Tab

**Features:**
- Watch mode control
- Research scheduling
- Gap analysis
- Real-time event stream

**Watch Mode:**
1. Enter repository path
2. Set check interval (minutes)
3. Click "Start Watch"
4. Monitor event stream for changes

**Research:**
1. Enter topics (comma-separated)
2. Set research interval (hours)
3. Click "Start Research"
4. View findings in event stream

**Gap Analysis:**
1. Enter project path
2. Set analysis interval (hours)
3. Click "Start Analysis"
4. Review identified gaps

---

## Telegram Bot

### Setup

1. **Create Bot:**
   - Open Telegram
   - Search for @BotFather
   - Send `/newbot`
   - Follow instructions
   - Copy bot token

2. **Configure in Desktop:**
   - Open PersonalAssist Desktop
   - Navigate to "Telegram" page
   - Paste bot token
   - Select DM policy
   - Click "Save Configuration"
   - Click "Start"

3. **Start Chatting:**
   - Open Telegram
   - Search for your bot
   - Send `/start`
   - Ask questions!

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Help information |
| `/status` | Your account status |
| `/new` | Start new conversation |

### DM Policies

**Pairing (Recommended):**
- Users send `/start`
- Admin approves via Desktop
- User receives approval code
- User can then chat

**Allowlist:**
- Only pre-approved users
- Admin manages list manually

**Open:**
- Anyone can message
- No approval needed

---

## System Monitoring

### Available Metrics

**CPU:**
- Current usage percentage
- Physical and logical core count
- Current frequency
- Per-core usage

**Memory:**
- Total RAM (GB)
- Used/Available (GB)
- Usage percentage
- Swap space

**Disk:**
- All drives listed
- Capacity and usage
- Filesystem type
- Progress bars

**Battery (Laptops):**
- Percentage (0-100)
- Charging/discharging status
- Time remaining estimate
- Power plugged indicator

### API Access

```bash
# Get all metrics
curl http://localhost:8000/system/summary

# Get specific metric
curl http://localhost:8000/system/cpu
curl http://localhost:8000/system/memory
curl http://localhost:8000/system/disk
curl http://localhost:8000/system/battery
```

---

## Autonomous Agent

### Overview

The Autonomous Agent runs background tasks:
- **Watch Mode:** Monitors git repositories for changes
- **Research:** Internet research on scheduled topics
- **Gap Analysis:** Code quality and issue detection

### Starting Tasks

**Via Desktop:**
1. Open Agents → Autonomous tab
2. Configure task parameters
3. Click Start button

**Via API:**
```bash
# Start watch mode
curl -X POST http://localhost:8000/autonomous/watch/start \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/repo", "interval_minutes": 30}'

# Start research
curl -X POST http://localhost:8000/autonomous/research/start \
  -H "Content-Type: application/json" \
  -d '{"topics": ["Python async", "FastAPI security"], "interval_hours": 6}'

# Start gap analysis
curl -X POST http://localhost:8000/autonomous/gap-analysis/start \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/path/to/project", "interval_hours": 24}'
```

### Event Stream

**Desktop:**
- Real-time events in Autonomous tab
- Filter by event type
- Auto-scrolls to newest

**API (SSE):**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/autonomous/events?event_types=watch_change,gap_found'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.type}]`, data.data);
};
```

**Event Types:**
- `watch_change` - Repository changes detected
- `research_complete` - Research task completed
- `gap_found` - Gap analysis found issues
- `error` - Error occurred

### Stopping Tasks

**Desktop:**
- Click "Stop" button for individual tasks
- Click "Stop All Tasks" to stop everything

**API:**
```bash
# Stop specific task
curl -X POST http://localhost:8000/autonomous/watch/stop
curl -X POST http://localhost:8000/autonomous/research/stop
curl -X POST http://localhost:8000/autonomous/gap-analysis/stop

# Stop all
curl -X POST http://localhost:8000/autonomous/stop-all
```

---

## API Reference

### Authentication

Most endpoints require API token:
```bash
curl http://localhost:8000/endpoint \
  -H "x-api-token: your-token"
```

### Endpoints

#### Health
- `GET /health` - API health check

#### Telegram
- `GET /telegram/config` - Get bot configuration
- `POST /telegram/config` - Update configuration
- `GET /telegram/status` - Bot runtime status
- `POST /telegram/start` - Start bot
- `POST /telegram/stop` - Stop bot
- `POST /telegram/reload` - Reload bot
- `GET /telegram/users` - List users
- `POST /telegram/users/{id}/approve` - Approve user
- `POST /telegram/test` - Send test message

#### System Monitor
- `GET /system/cpu` - CPU metrics
- `GET /system/memory` - Memory metrics
- `GET /system/disk` - Disk metrics
- `GET /system/battery` - Battery status
- `GET /system/summary` - All metrics

#### Autonomous
- `GET /autonomous/status` - Agent status
- `POST /autonomous/watch/start` - Start watch mode
- `POST /autonomous/watch/stop` - Stop watch mode
- `POST /autonomous/research/start` - Start research
- `POST /autonomous/research/stop` - Stop research
- `POST /autonomous/gap-analysis/start` - Start gap analysis
- `POST /autonomous/gap-analysis/stop` - Stop gap analysis
- `POST /autonomous/stop-all` - Stop all tasks
- `GET /autonomous/events` - SSE event stream
- `GET /autonomous/events/history` - Event history
- `GET /autonomous/events/stats` - Event statistics

### Swagger Documentation

Interactive API documentation available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Troubleshooting

### API Won't Start

**Error: "Address already in use"**
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /F /PID <PID>
```

**Error: "Module not found"**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Desktop App Issues

**Blank screen:**
1. Check API is running
2. Check browser console (F12)
3. Rebuild desktop: `npm run build`

**Can't connect to API:**
1. Verify API running on http://localhost:8000
2. Check CORS settings in `.env`
3. Check API token if configured

### Telegram Bot Issues

**Bot won't start:**
1. Verify token is valid (from @BotFather)
2. Check "Bot Status" shows "running"
3. Check API logs for errors

**Users can't message:**
1. Check DM policy setting
2. Approve pending users (if pairing mode)
3. Verify bot token is saved

### System Monitor Issues

**Metrics show "Not available":**
```bash
# Install psutil
pip install psutil

# Windows Event Logs (optional)
pip install pywin32
```

**Battery not showing:**
- Desktop PCs don't have batteries
- Check if laptop battery is detected by Windows

### Autonomous Agent Issues

**Tasks won't start:**
1. Check API logs for errors
2. Verify paths are valid
3. Check ARQ worker is running

**No events in stream:**
1. Check event filters (may be filtering all)
2. Click "Refresh" to reload history
3. Verify tasks are actually running

### Common Error Messages

**"psutil not installed"**
```bash
pip install psutil
```

**"pywin32 not installed"**
```bash
pip install pywin32
```

**"Bot not running"**
- Start bot via Desktop or API `/telegram/start`

**"Repository not found"**
- Verify git repository exists at path
- Check path is absolute, not relative

---

## Support

### Logs

**API Logs:**
- Console output when running
- Check for errors and warnings

**Desktop Logs:**
- Browser console (F12 → Console tab)
- Check for JavaScript errors

### Getting Help

1. Check this user guide
2. Review API documentation (http://localhost:8000/docs)
3. Check GitHub issues
4. Contact support

---

## Appendix

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_ACCESS_TOKEN` | API authentication token | (none) |
| `API_HOST` | API bind host | `127.0.0.1` |
| `API_PORT` | API bind port | `8000` |
| `DEFAULT_LOCAL_MODEL` | Default local model | `ollama/llama3.2` |
| `DEFAULT_REMOTE_MODEL` | Default remote model | `gemini/gemini-2.5-flash-lite` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | (none) |
| `TELEGRAM_DM_POLICY` | Default DM policy | `pairing` |
| `QDRANT_HOST` | Qdrant host | `localhost` |
| `QDRANT_PORT` | Qdrant port | `6333` |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Space` | Toggle desktop window |
| `Ctrl+Enter` | Send message (Chat page) |
| `F5` | Refresh current page |

### File Locations

| File | Location |
|------|----------|
| Chat database | `~/.personalassist/chat.db` |
| Telegram config | `~/.personalassist/telegram_config.env` |
| Qdrant data | `storage/qdrant_data/` |
| Workflows | `~/.personalassist/workflows/` |

---

**End of User Guide**
