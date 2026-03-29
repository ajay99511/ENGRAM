"""
ARQ Job Monitoring API Endpoints

Provides REST API for monitoring ARQ background jobs:
- List jobs
- Get job status
- Enqueue jobs manually
- Cancel jobs

Usage:
    from apps.api.job_router import router
    
    app.include_router(router)
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
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


# ── Helper Functions ─────────────────────────────────────────────────


async def _get_job_status(job_id: str) -> JobResponse:
    """Get status of a job."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis = await create_pool(RedisSettings(host="localhost", port=6379))
        
        # Try to get job result
        try:
            result = await redis.read_job_result(job_id, timeout=0)
            
            return JobResponse(
                job_id=job_id,
                status="completed",
                result=result,
            )
        except Exception:
            # Job might still be running or not found
            return JobResponse(
                job_id=job_id,
                status="running",
            )
    
    except Exception as exc:
        logger.error(f"Failed to get job status: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── API Endpoints ────────────────────────────────────────────────────


@router.get("/list", response_model=JobListResponse)
async def list_jobs(limit: int = 50):
    """
    List all recent jobs.
    
    Args:
        limit: Maximum number of jobs to return
    
    Returns:
        List of job information
    """
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis = await create_pool(RedisSettings(host="localhost", port=6379))
        
        # Get all job keys
        keys = await redis.redis.keys("arq:job:*")
        job_ids = [key.decode().replace("arq:job:", "") for key in keys[:limit]]
        
        # Get status for each job
        jobs = []
        for job_id in job_ids:
            try:
                job_info = await _get_job_status(job_id)
                jobs.append(job_info)
            except Exception:
                continue
        
        return JobListResponse(
            jobs=jobs,
            total=len(jobs),
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
    return await _get_job_status(job_id)


@router.post("/enqueue", response_model=JobResponse)
async def enqueue_job(req: JobEnqueueRequest, background_tasks: BackgroundTasks):
    """
    Enqueue a job manually.
    
    Args:
        req: Job enqueue request
    
    Returns:
        Enqueued job information
    """
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis = await create_pool(RedisSettings(host="localhost", port=6379))
        
        # Enqueue job
        job = await redis.enqueue_job(req.job_name, **req.kwargs)
        
        logger.info(f"Enqueued job: {req.job_name} (job_id={job.job_id})")
        
        return JobResponse(
            job_id=job.job_id,
            status="queued",
        )
    
    except Exception as exc:
        logger.error(f"Failed to enqueue job: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running job.
    
    Args:
        job_id: Job identifier
    """
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis = await create_pool(RedisSettings(host="localhost", port=6379))
        
        # Note: ARQ doesn't have built-in cancel, we just mark it as cancelled
        await redis.redis.set(f"arq:job:{job_id}:cancelled", "1", ex=3600)
        
        logger.info(f"Cancelled job: {job_id}")
        
        return {"status": "cancelled", "job_id": job_id}
    
    except Exception as exc:
        logger.error(f"Failed to cancel job: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stats")
async def get_job_stats():
    """
    Get job statistics.
    
    Returns:
        Job statistics
    """
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis = await create_pool(RedisSettings(host="localhost", port=6379))
        
        # Get all job keys
        keys = await redis.redis.keys("arq:job:*")
        
        # Count by status
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
            except Exception:
                status_counts["running"] += 1
        
        return {
            "total_jobs": len(keys),
            "status_counts": status_counts,
            "redis_connected": True,
        }
    
    except Exception as exc:
        logger.error(f"Failed to get job stats: {exc}")
        return {
            "total_jobs": 0,
            "status_counts": {},
            "redis_connected": False,
            "error": str(exc),
        }
