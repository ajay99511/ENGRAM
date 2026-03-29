"""
ARQ Job Monitoring API Endpoints - FIXED

Provides REST API for monitoring ARQ background jobs.

FIXES APPLIED:
1. Route ordering - /stats before /{job_id} to prevent route conflicts
2. Proper async Redis connection pooling with arq
3. Better error handling and status detection
4. Industry-standard response formats
5. Health check endpoint for Redis connectivity

Based on ARQ Official Documentation:
- https://arq-docs.helpmanual.io/
- https://github.com/samuelcolvin/arq
"""

import logging
from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ── Request/Response Models ──────────────────────────────────────────


class JobEnqueueRequest(BaseModel):
    """Request model for enqueuing a job."""

    job_name: str = Field(..., description="Name of job function")
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Job arguments")


class JobResponse(BaseModel):
    """Response model for job information."""

    job_id: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class JobListResponse(BaseModel):
    """Response model for job list."""

    jobs: list[JobResponse]
    total: int
    limit: int


class JobStatsResponse(BaseModel):
    """Response model for job statistics."""

    total_jobs: int
    status_counts: dict[str, int]
    redis_connected: bool
    error: Optional[str] = None


class RedisHealthResponse(BaseModel):
    """Response model for Redis health check."""

    connected: bool
    host: str
    port: int
    db: int
    keys_count: int
    memory_used: Optional[str] = None
    error: Optional[str] = None


# ── Redis Connection Helper ─────────────────────────────────────────

async def get_arq_redis():
    """
    Get ARQ Redis pool with proper connection handling.
    
    Based on ARQ best practices:
    - Use create_pool for async Redis connections
    - Handle connection errors gracefully
    - Close connections properly
    
    Official ARQ Docs: https://arq-docs.helpmanual.io/
    """
    from arq import create_pool
    from arq.connections import RedisSettings
    
    try:
        # Note: RedisSettings doesn't accept 'db' parameter
        # Use Redis URL format for non-default databases: redis://localhost:6379/1
        redis = await create_pool(RedisSettings(
            host="localhost",
            port=6379,
        ))
        return redis
    except Exception as exc:
        logger.error(f"Failed to connect to Redis: {exc}")
        return None


# ── API Endpoints ────────────────────────────────────────────────────
# NOTE: Order matters! More specific routes must come before parameterized routes.


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats():
    """
    Get job statistics.
    
    Returns aggregate statistics about background jobs.
    """
    redis = await get_arq_redis()
    
    if not redis:
        return JobStatsResponse(
            total_jobs=0,
            status_counts={},
            redis_connected=False,
            error="Failed to connect to Redis",
        )
    
    try:
        # Get all job keys
        keys = await redis.keys("arq:job:*")
        
        # Count by status (check each job)
        status_counts = {
            "completed": 0,
            "failed": 0,
            "running": 0,
            "queued": 0,
        }
        
        for key in keys:
            job_id = key.decode().replace("arq:job:", "")
            try:
                result = await redis.read_job_result(job_id, timeout=0)
                if result:
                    status_counts["completed"] += 1
                else:
                    status_counts["running"] += 1
            except Exception:
                status_counts["running"] += 1
        
        return JobStatsResponse(
            total_jobs=len(keys),
            status_counts=status_counts,
            redis_connected=True,
        )
    
    except Exception as exc:
        logger.error(f"Failed to get job stats: {exc}")
        return JobStatsResponse(
            total_jobs=0,
            status_counts={},
            redis_connected=False,
            error=str(exc),
        )


@router.get("/health", response_model=RedisHealthResponse)
async def redis_health():
    """
    Check Redis connectivity and health.
    
    Returns detailed Redis connection status.
    
    Based on ARQ Official Documentation:
    - https://arq-docs.helpmanual.io/#redis-pool
    - The pool object itself is used for Redis operations
    """
    from arq import create_pool
    from arq.connections import RedisSettings
    
    try:
        redis = await create_pool(RedisSettings(
            host="localhost",
            port=6379,
        ))
        
        # Ping Redis (the pool itself is used for operations)
        ping_result = await redis.ping()
        
        # Get key count
        keys = await redis.keys("*")
        
        # Get memory info (INFO memory)
        memory_info = await redis.info("memory")
        memory_used = memory_info.get("used_memory_human", "unknown")
        
        return RedisHealthResponse(
            connected=bool(ping_result),
            host="localhost",
            port=6379,
            db=0,
            keys_count=len(keys),
            memory_used=memory_used,
        )
    
    except Exception as exc:
        logger.error(f"Redis health check failed: {exc}")
        return RedisHealthResponse(
            connected=False,
            host="localhost",
            port=6379,
            db=0,
            keys_count=0,
            error=str(exc),
        )


@router.get("/list", response_model=JobListResponse)
async def list_jobs(limit: int = 50):
    """
    List all recent jobs.
    
    Args:
        limit: Maximum number of jobs to return
    
    Returns:
        List of job information
    """
    redis = await get_arq_redis()
    
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        # Get all job keys
        keys = await redis.keys("arq:job:*")
        job_ids = [key.decode().replace("arq:job:", "") for key in keys[:limit]]
        
        # Get status for each job
        jobs = []
        for job_id in job_ids:
            try:
                result = await redis.read_job_result(job_id, timeout=0)
                jobs.append(JobResponse(
                    job_id=job_id,
                    status="completed",
                    result=result,
                ))
            except Exception:
                jobs.append(JobResponse(
                    job_id=job_id,
                    status="running",
                ))
        
        return JobListResponse(
            jobs=jobs,
            total=len(job_ids),
            limit=limit,
        )
    
    except Exception as exc:
        logger.error(f"Failed to list jobs: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get status of a specific job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Job information
    """
    redis = await get_arq_redis()
    
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        result = await redis.read_job_result(job_id, timeout=0)
        
        if result:
            return JobResponse(
                job_id=job_id,
                status="completed",
                result=result,
            )
        else:
            return JobResponse(
                job_id=job_id,
                status="running",
            )
    
    except Exception as exc:
        logger.error(f"Failed to get job status: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/enqueue", response_model=JobResponse)
async def enqueue_job(req: JobEnqueueRequest):
    """
    Enqueue a job manually.
    
    Args:
        req: Job enqueue request
    
    Returns:
        Enqueued job information
    """
    redis = await get_arq_redis()
    
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        # Enqueue job
        job = await redis.enqueue_job(req.job_name, **req.kwargs)
        
        logger.info(f"Enqueued job: {req.job_name} (job_id={job.job_id})")
        
        return JobResponse(
            job_id=job.job_id,
            status="queued",
            created_at=datetime.now().isoformat(),
        )
    
    except Exception as exc:
        logger.error(f"Failed to enqueue job: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running job.
    
    Note: ARQ doesn't have built-in job cancellation.
    This marks the job as cancelled in Redis, which the worker can check.
    
    Args:
        job_id: Job identifier
    """
    redis = await get_arq_redis()
    
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        # Mark as cancelled (worker can check this flag)
        await redis.set(f"arq:job:{job_id}:cancelled", "1", ex=3600)
        
        logger.info(f"Cancelled job: {job_id}")
        
        return {"status": "cancelled", "job_id": job_id}
    
    except Exception as exc:
        logger.error(f"Failed to cancel job: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
