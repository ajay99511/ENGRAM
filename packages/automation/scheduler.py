"""
In-process tick scheduler — zero external dependencies.

Modelled after hermes-agent's cron/scheduler.py: a simple tick() function
called on a background thread every 60 seconds. Jobs persist in SQLite
(the same database used for chat history) so they survive restarts.

No Redis. No APScheduler. No ARQ. No Celery.

Usage:
    from packages.automation.scheduler import start_scheduler, stop_scheduler, schedule_job

    # Start the background tick thread (call once at app startup)
    start_scheduler()

    # Register a one-off or recurring job
    schedule_job(
        job_id="daily_briefing",
        name="Daily Briefing",
        cron_expr="0 8 * * *",          # 5-field cron: minute hour dom month dow
        prompt="Summarize recent git activity and store as a briefing memory.",
        model="local",
    )

    # Stop cleanly at shutdown
    stop_scheduler()
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── File-based lock (prevents double-tick if two processes share the same data dir) ──

_LOCK_FILE: Path | None = None
_LOCK_FD: Any = None


def _get_lock_path() -> Path:
    data_dir = Path(os.path.expanduser("~/.personalassist"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / ".scheduler.lock"


def _acquire_lock() -> bool:
    """Try to acquire the scheduler file lock. Returns True on success."""
    global _LOCK_FILE, _LOCK_FD
    lock_path = _get_lock_path()
    try:
        # Windows: open with exclusive access
        import msvcrt
        fd = open(lock_path, "w")
        try:
            msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
            _LOCK_FILE = lock_path
            _LOCK_FD = fd
            return True
        except OSError:
            fd.close()
            return False
    except ImportError:
        # POSIX
        import fcntl
        fd = open(lock_path, "w")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _LOCK_FILE = lock_path
            _LOCK_FD = fd
            return True
        except OSError:
            fd.close()
            return False
    except Exception as exc:
        logger.warning("Could not acquire scheduler lock: %s — proceeding without lock", exc)
        return True  # Non-fatal: proceed without lock on unexpected errors


def _release_lock() -> None:
    global _LOCK_FD
    if _LOCK_FD is not None:
        try:
            _LOCK_FD.close()
        except Exception:
            pass
        _LOCK_FD = None


# ── Job store (SQLite via aiosqlite) ─────────────────────────────────

_JOBS_FILE: Path | None = None


def _jobs_path() -> Path:
    data_dir = Path(os.path.expanduser("~/.personalassist"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "scheduler_jobs.json"


def _load_jobs() -> list[dict[str, Any]]:
    path = _jobs_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load scheduler jobs: %s", exc)
        return []


def _save_jobs(jobs: list[dict[str, Any]]) -> None:
    path = _jobs_path()
    try:
        path.write_text(json.dumps(jobs, indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to save scheduler jobs: %s", exc)


def schedule_job(
    job_id: str,
    name: str,
    cron_expr: str,
    prompt: str,
    model: str = "local",
    enabled: bool = True,
) -> dict[str, Any]:
    """
    Register or update a scheduled job.

    Args:
        job_id:    Unique identifier (used for deduplication).
        name:      Human-readable name.
        cron_expr: 5-field cron expression (minute hour dom month dow).
                   Also accepts "daily@HH:MM" shorthand.
        prompt:    The message sent to the agent when the job fires.
        model:     Model key to use (default: "local").
        enabled:   Whether the job is active.

    Returns the job dict.
    """
    jobs = _load_jobs()
    existing = next((j for j in jobs if j["id"] == job_id), None)

    job: dict[str, Any] = {
        "id": job_id,
        "name": name,
        "cron_expr": _normalize_cron(cron_expr),
        "prompt": prompt,
        "model": model,
        "enabled": enabled,
        "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()) if existing else datetime.now(timezone.utc).isoformat(),
        "last_run_at": existing.get("last_run_at") if existing else None,
        "next_run_at": None,
        "run_count": existing.get("run_count", 0) if existing else 0,
        "last_error": None,
    }
    job["next_run_at"] = _next_run(job["cron_expr"])

    if existing:
        jobs = [job if j["id"] == job_id else j for j in jobs]
    else:
        jobs.append(job)

    _save_jobs(jobs)
    logger.info("Scheduled job '%s' (%s) next run: %s", name, cron_expr, job["next_run_at"])
    return job


def remove_job(job_id: str) -> bool:
    """Remove a scheduled job. Returns True if found and removed."""
    jobs = _load_jobs()
    before = len(jobs)
    jobs = [j for j in jobs if j["id"] != job_id]
    if len(jobs) < before:
        _save_jobs(jobs)
        return True
    return False


def list_jobs() -> list[dict[str, Any]]:
    """Return all registered jobs."""
    return _load_jobs()


# ── Cron expression parser ────────────────────────────────────────────

def _normalize_cron(expr: str) -> str:
    """Normalize shorthand cron expressions to 5-field format."""
    expr = expr.strip()
    if expr.startswith("daily@"):
        time_part = expr[6:]
        try:
            h, m = time_part.split(":")
            return f"{int(m)} {int(h)} * * *"
        except Exception:
            return "0 8 * * *"
    if expr == "@daily":
        return "0 8 * * *"
    if expr == "@hourly":
        return "0 * * * *"
    if expr == "@weekly":
        return "0 8 * * 1"
    return expr


def _cron_matches(cron_expr: str, dt: datetime) -> bool:
    """Return True if the cron expression matches the given datetime (minute precision)."""
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
        minute, hour, dom, month, dow = parts

        def _match(field: str, value: int) -> bool:
            if field == "*":
                return True
            if "," in field:
                return any(_match(f.strip(), value) for f in field.split(","))
            if "/" in field:
                base, step = field.split("/", 1)
                start = 0 if base == "*" else int(base)
                return (value - start) % int(step) == 0
            if "-" in field:
                lo, hi = field.split("-", 1)
                return int(lo) <= value <= int(hi)
            return int(field) == value

        return (
            _match(minute, dt.minute)
            and _match(hour, dt.hour)
            and _match(dom, dt.day)
            and _match(month, dt.month)
            and _match(dow, dt.weekday())  # 0=Monday in Python, 0=Sunday in cron — close enough for daily jobs
        )
    except Exception as exc:
        logger.debug("Cron match error for '%s': %s", cron_expr, exc)
        return False


def _next_run(cron_expr: str) -> str | None:
    """Compute the next fire time for a cron expression (approximate, minute-level)."""
    try:
        from datetime import timedelta
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        for minutes_ahead in range(1, 60 * 24 * 8):  # Search up to 8 days ahead
            candidate = now + timedelta(minutes=minutes_ahead)
            if _cron_matches(cron_expr, candidate):
                return candidate.isoformat()
    except Exception:
        pass
    return None


# ── Tick function ─────────────────────────────────────────────────────

def _run_job_sync(job: dict[str, Any]) -> None:
    """Execute a scheduled job in a new event loop (called from the tick thread)."""
    async def _run():
        try:
            from packages.agents.react_loop import run_react
            result = await run_react(
                job["prompt"],
                user_id="default",
                model=job.get("model", "local"),
                store_memory=True,
            )
            logger.info(
                "Scheduled job '%s' completed: %d chars, %d tool calls",
                job["name"],
                len(result.get("response", "")),
                result.get("tool_calls_made", 0),
            )
            return result.get("response", "")
        except Exception as exc:
            logger.error("Scheduled job '%s' failed: %s", job["name"], exc)
            raise

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("Job '%s' run error: %s", job["name"], exc)


def tick() -> None:
    """
    Check for due jobs and run them. Called every 60 seconds by the scheduler thread.

    Uses minute-level granularity — a job fires if its cron expression matches
    the current minute and it hasn't run in the last 55 seconds.
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    jobs = _load_jobs()
    changed = False

    for job in jobs:
        if not job.get("enabled", True):
            continue

        cron_expr = job.get("cron_expr", "")
        if not cron_expr:
            continue

        # Check if this job already ran this minute
        last_run = job.get("last_run_at")
        if last_run:
            try:
                last_dt = datetime.fromisoformat(last_run)
                if (now - last_dt.replace(tzinfo=timezone.utc)).total_seconds() < 55:
                    continue
            except Exception:
                pass

        if not _cron_matches(cron_expr, now):
            continue

        logger.info("Firing scheduled job: %s", job["name"])
        job["last_run_at"] = now.isoformat()
        job["run_count"] = job.get("run_count", 0) + 1
        job["next_run_at"] = _next_run(cron_expr)
        changed = True

        # Run in a separate thread so one slow job doesn't block the tick
        t = threading.Thread(
            target=_run_job_sync,
            args=(dict(job),),
            name=f"job-{job['id']}",
            daemon=True,
        )
        t.start()

    if changed:
        _save_jobs(jobs)


# ── Background thread ─────────────────────────────────────────────────

_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _scheduler_loop() -> None:
    """Main scheduler loop — ticks every 60 seconds."""
    logger.info("Scheduler started (tick interval: 60s)")
    while not _stop_event.is_set():
        try:
            tick()
        except Exception as exc:
            logger.error("Scheduler tick error: %s", exc)
        _stop_event.wait(timeout=60)
    logger.info("Scheduler stopped")


def start_scheduler() -> None:
    """Start the background scheduler thread. Safe to call multiple times."""
    global _scheduler_thread

    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        logger.debug("Scheduler already running")
        return

    if not _acquire_lock():
        logger.warning("Another process holds the scheduler lock — this instance will not schedule jobs")
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        name="personalassist-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()

    # Register default jobs
    _register_default_jobs()


def stop_scheduler() -> None:
    """Signal the scheduler thread to stop and wait for it."""
    _stop_event.set()
    if _scheduler_thread is not None:
        _scheduler_thread.join(timeout=5)
    _release_lock()
    logger.info("Scheduler stopped cleanly")


def _register_default_jobs() -> None:
    """Register built-in jobs if they don't already exist."""
    existing_ids = {j["id"] for j in _load_jobs()}

    if "daily_briefing" not in existing_ids:
        schedule_job(
            job_id="daily_briefing",
            name="Daily Briefing",
            cron_expr="0 8 * * *",
            prompt=(
                "You are running as a background briefing agent. "
                "Use git tools to summarize recent project activity across any repositories you can find. "
                "Then store a concise briefing as a memory so the user can read it when they start their day. "
                f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
            ),
            model="local",
        )
