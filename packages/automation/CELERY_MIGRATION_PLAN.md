# ARQ → Celery Migration Plan

**Document Purpose:** Fallback plan for migrating from ARQ to Celery if ARQ maintenance becomes a concern.

**Date:** March 27, 2026  
**Estimated Effort:** 2-3 days

---

## 📊 **MIGRATION TRIGGERS**

Consider migrating to Celery if:

1. **ARQ repo shows no activity for 6+ months**
2. **Critical bug in ARQ with no fix**
3. **Security vulnerability in ARQ dependencies**
4. **Better Celery features needed** (e.g., advanced routing, flower monitoring)

---

## 🏗️ **ARCHITECTURE COMPARISON**

| Feature | ARQ | Celery | Notes |
|---------|-----|--------|-------|
| **Async Support** | ✅ Native asyncio | ⚠️ Via gevent/eventlet | ARQ simpler for FastAPI |
| **Redis Integration** | ✅ Built-in | ✅ Built-in | Both excellent |
| **Job Persistence** | ✅ Redis | ✅ Redis/RabbitMQ | Both support |
| **Retry Logic** | ✅ Exponential backoff | ✅ Exponential backoff | Equivalent |
| **Cron Scheduling** | ✅ Built-in | ✅ Celery Beat | Equivalent |
| **Monitoring** | ⚠️ Basic | ✅ Flower (mature) | Celery advantage |
| **Complexity** | ✅ Simple | ⚠️ More boilerplate | ARQ simpler |
| **Maintenance** | ⚠️ Limited | ✅ Active | Celery more stable |

---

## 📋 **MIGRATION STEPS**

### **Step 1: Install Dependencies**

```bash
pip install celery[gevent]>=5.3.0
pip install flower  # Optional: monitoring UI
```

**Update requirements.txt:**
```txt
# Remove ARQ
# arq==0.25.0

# Add Celery
celery[gevent]>=5.3.0
flower>=2.0.0  # Optional
```

---

### **Step 2: Create Celery Configuration**

**File:** `packages/automation/celery_config.py`

```python
from celery import Celery
from celery.schedules import crontab

# Create Celery app
app = Celery(
    'personalassist',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
)

# Load config from Django/Flask style config file
app.config_from_object('packages.automation.celery_config', namespace='CELERY')

# Auto-discover tasks
app.autodiscover_tasks(['packages.automation'])

# Celery Beat schedule (cron jobs)
app.conf.beat_schedule = {
    'daily-briefing': {
        'task': 'packages.automation.tasks.run_daily_briefing',
        'schedule': crontab(hour=8, minute=0),
    },
    'hourly-snapshot': {
        'task': 'packages.automation.tasks.run_hourly_snapshot',
        'schedule': crontab(minute=0),
    },
    'weekly-audit': {
        'task': 'packages.automation.tasks.run_workspace_audit',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
}

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)
```

---

### **Step 3: Migrate Task Definitions**

**File:** `packages/automation/tasks.py`

```python
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=5)
def run_daily_briefing(self):
    """Daily briefing task."""
    job_id = self.request.id
    logger.info(f"Starting daily briefing (job_id={job_id})")
    
    try:
        import asyncio
        from packages.agents.crew import run_crew
        
        # Run async function in sync task
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(run_crew(
            user_message="Generate a morning briefing...",
            user_id="default",
            model="local",
            session_type="isolated",
        ))
        
        logger.info(f"Daily briefing completed: {result.get('response', '')[:100]}...")
        
        return {
            "status": "completed",
            "result": result.get("response", ""),
            "completed_at": datetime.now().isoformat(),
        }
    
    except Exception as exc:
        logger.error(f"Daily briefing failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(bind=True, max_retries=5)
def run_hourly_snapshot(self):
    """Hourly snapshot task."""
    job_id = self.request.id
    logger.info(f"Starting hourly snapshot (job_id={job_id})")
    
    try:
        import asyncio
        from packages.memory.qdrant_store import export_snapshot
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(export_snapshot())
        
        logger.info("Hourly snapshot completed")
        
        return {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
        }
    
    except Exception as exc:
        logger.error(f"Hourly snapshot failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(bind=True, max_retries=5)
def run_workspace_audit(self):
    """Weekly workspace audit task."""
    job_id = self.request.id
    logger.info(f"Starting workspace audit (job_id={job_id})")
    
    try:
        from packages.agents.workspace import list_workspace_configs
        
        configs = list_workspace_configs()
        
        summary = f"Audited {len(configs)} workspaces:\n"
        for config in configs:
            summary += f"- {config.project_id}: {config.root}\n"
        
        logger.info(f"Workspace audit completed: {summary[:200]}...")
        
        return {
            "status": "completed",
            "result": summary,
            "workspace_count": len(configs),
            "completed_at": datetime.now().isoformat(),
        }
    
    except Exception as exc:
        logger.error(f"Workspace audit failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

---

### **Step 4: Update API Endpoints**

**File:** `apps/api/job_router.py` (update imports)

```python
# Replace ARQ imports with Celery
# from arq import create_pool
# from arq.connections import RedisSettings

from packages.automation.tasks import (
    run_daily_briefing,
    run_hourly_snapshot,
    run_workspace_audit,
)
from celery.result import AsyncResult

@router.post("/enqueue", response_model=JobResponse)
async def enqueue_job(req: JobEnqueueRequest):
    """Enqueue a job manually."""
    
    # Map job names to Celery tasks
    task_map = {
        "run_daily_briefing": run_daily_briefing,
        "run_hourly_snapshot": run_hourly_snapshot,
        "run_workspace_audit": run_workspace_audit,
    }
    
    if req.job_name not in task_map:
        raise HTTPException(status_code=400, detail=f"Unknown job: {req.job_name}")
    
    task = task_map[req.job_name].delay(**req.kwargs)
    
    return JobResponse(
        job_id=task.id,
        status="queued",
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get status of a specific job."""
    result = AsyncResult(job_id, app=celery_app)
    
    if result.ready():
        return JobResponse(
            job_id=job_id,
            status="completed",
            result=result.result,
        )
    elif result.failed():
        return JobResponse(
            job_id=job_id,
            status="failed",
            error=str(result.result),
        )
    else:
        return JobResponse(
            job_id=job_id,
            status="running",
        )
```

---

### **Step 5: Update Main.py**

**File:** `apps/api/main.py` (remove APScheduler, add Celery)

```python
# Remove APScheduler
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# scheduler = AsyncIOScheduler()

# Add Celery (optional, for monitoring)
from packages.automation.celery_config import app as celery_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up PersonalAssist API...")
    
    # Celery runs independently, no need to start here
    # Celery Beat handles scheduling
    
    yield
    
    # Shutdown
    logger.info("Shutting down PersonalAssist API...")
```

---

### **Step 6: Start Workers**

**ARQ (Old):**
```bash
arq packages.automation.arq_worker.WorkerSettings
```

**Celery (New):**
```bash
# Worker
celery -A packages.automation.celery_config worker --loglevel=info --pool=gevent

# Celery Beat (scheduler)
celery -A packages.automation.celery_config beat --loglevel=info

# Flower (monitoring UI, optional)
celery -A packages.automation.celery_config flower --port=5555
```

---

### **Step 7: Test Migration**

**Test Checklist:**

1. ✅ Workers start successfully
2. ✅ Scheduled jobs run at correct times
3. ✅ Manual job enqueueing works
4. ✅ Job status monitoring works
5. ✅ Retry logic works (test with failing job)
6. ✅ API endpoints return correct data

**Test Commands:**
```bash
# Test worker
celery -A packages.automation.celery_config inspect ping

# Test scheduled jobs
celery -A packages.automation.celery_config inspect scheduled

# Test manual enqueue
curl -X POST http://localhost:8000/jobs/enqueue \
  -H "Content-Type: application/json" \
  -d '{"job_name": "run_daily_briefing"}'
```

---

## 📊 **MIGRATION EFFORT ESTIMATE**

| Task | Estimated Time |
|------|---------------|
| Install dependencies | 0.5 hours |
| Create Celery config | 1 hour |
| Migrate task definitions | 2 hours |
| Update API endpoints | 1 hour |
| Update main.py | 0.5 hours |
| Testing | 2 hours |
| **Total** | **7 hours (~1 day)** |

**Buffer for issues:** +1-2 days  
**Total Estimated:** 2-3 days

---

## ✅ **MIGRATION CHECKLIST**

- [ ] Install Celery dependencies
- [ ] Create Celery configuration file
- [ ] Migrate task definitions
- [ ] Update API endpoints
- [ ] Update main.py
- [ ] Test workers start successfully
- [ ] Test scheduled jobs
- [ ] Test manual job enqueueing
- [ ] Test job monitoring
- [ ] Test retry logic
- [ ] Update documentation
- [ ] Deploy to production
- [ ] Monitor for 1 week
- [ ] Remove ARQ dependencies

---

## 🎯 **DECISION CRITERIA**

**Stay with ARQ if:**
- ARQ repo shows activity (commits, releases)
- No critical bugs affecting production
- Simple use case (ARQ is simpler)
- Don't need Flower monitoring

**Migrate to Celery if:**
- ARQ repo abandoned (6+ months no activity)
- Critical bug with no fix
- Need advanced features (routing, Flower)
- Production stability is paramount

---

**This migration plan ensures we can switch to Celery if needed, while enjoying ARQ's simplicity as long as it's maintained.**
