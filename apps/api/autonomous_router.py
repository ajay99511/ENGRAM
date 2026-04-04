"""
Autonomous Agent Router

FastAPI router for autonomous agent management.
Provides REST API and SSE streaming for:
- Watch mode control
- Research scheduling
- Gap analysis
- Real-time event streaming

Endpoints:
- GET /autonomous/status - Get autonomous agent status
- POST /autonomous/watch/start - Start watch mode
- POST /autonomous/watch/stop - Stop watch mode
- POST /autonomous/research/start - Start research
- POST /autonomous/research/stop - Stop research
- POST /autonomous/gap-analysis/start - Start gap analysis
- POST /autonomous/gap-analysis/stop - Stop gap analysis
- GET /autonomous/events - SSE stream of events
- POST /autonomous/stop-all - Stop all autonomous tasks

Usage:
    from apps.api.autonomous_router import router
    
    app.include_router(router)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autonomous", tags=["autonomous"])


# ── Request/Response Models ───────────────────────────────────────────


class WatchModeRequest(BaseModel):
    """Request model for starting watch mode."""
    repo_path: str = Field(..., description="Path to git repository")
    interval_minutes: int = Field(default=30, ge=1, le=1440, description="Check interval in minutes")


class ResearchRequest(BaseModel):
    """Request model for starting research."""
    topics: List[str] = Field(..., description="Topics to research")
    interval_hours: int = Field(default=6, ge=1, le=168, description="Research interval in hours")


class GapAnalysisRequest(BaseModel):
    """Request model for starting gap analysis."""
    project_path: str = Field(..., description="Path to project root")
    interval_hours: int = Field(default=24, ge=1, le=168, description="Analysis interval in hours")


class AutonomousStatusResponse(BaseModel):
    """Response model for autonomous agent status."""
    workspace_id: str
    running: bool
    watch_mode: Dict[str, Any]
    research: Dict[str, Any]
    gap_analysis: Dict[str, Any]
    callbacks_registered: Dict[str, int]


class EventStreamResponse(BaseModel):
    """Response model for SSE events."""
    id: str
    type: str
    data: Dict[str, Any]
    timestamp: str
    source: str
    workspace_id: str


# ── Status Endpoints ──────────────────────────────────────────────────


@router.get("/status", response_model=AutonomousStatusResponse)
async def get_autonomous_status():
    """
    Get current autonomous agent status.
    
    **Response Fields:**
    - `workspace_id`: Workspace identifier
    - `running`: Whether agent is running
    - `watch_mode`: Watch mode status and config
    - `research`: Research status and config
    - `gap_analysis`: Gap analysis status and config
    - `callbacks_registered`: Number of registered callbacks per event type
    
    **Example Response:**
    ```json
    {
        "workspace_id": "default",
        "running": true,
        "watch_mode": {
            "active": true,
            "config": {
                "repo_path": "/path/to/repo",
                "interval": "0:30:00",
                "started_at": "2026-03-29T10:00:00"
            }
        },
        "research": {
            "active": true,
            "config": {
                "topics": ["Python async", "FastAPI security"],
                "interval": "6:00:00",
                "started_at": "2026-03-29T10:00:00"
            }
        },
        "gap_analysis": {
            "active": false,
            "config": null
        },
        "callbacks_registered": {
            "on_change": 2,
            "on_research_complete": 1,
            "on_gap_found": 0,
            "on_error": 1
        }
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        status = agent.get_status()
        
        return AutonomousStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Get autonomous status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Watch Mode Endpoints ──────────────────────────────────────────────


@router.post("/watch/start")
async def start_watch_mode(request: WatchModeRequest):
    """
    Start watch mode for a repository.
    
    **Request Fields:**
    - `repo_path`: Path to git repository to watch
    - `interval_minutes`: How often to check for changes (1-1440 minutes)
    
    **Response:**
    ```json
    {
        "status": "started",
        "message": "Watch mode started for /path/to/repo",
        "interval_minutes": 30
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        interval = timedelta(minutes=request.interval_minutes)
        
        success = await agent.start_watch_mode(request.repo_path, interval)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Watch mode already running. Stop it first."
            )
        
        return {
            "status": "started",
            "message": f"Watch mode started for {request.repo_path}",
            "interval_minutes": request.interval_minutes,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start watch mode error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watch/stop")
async def stop_watch_mode():
    """
    Stop watch mode.
    
    **Response:**
    ```json
    {
        "status": "stopped",
        "message": "Watch mode stopped"
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        await agent.stop_watch_mode()
        
        return {
            "status": "stopped",
            "message": "Watch mode stopped",
        }
        
    except Exception as e:
        logger.error(f"Stop watch mode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Research Endpoints ────────────────────────────────────────────────


@router.post("/research/start")
async def start_research(request: ResearchRequest):
    """
    Start scheduled research on topics.
    
    **Request Fields:**
    - `topics`: List of topics to research
    - `interval_hours`: Research interval in hours (1-168)
    
    **Response:**
    ```json
    {
        "status": "started",
        "message": "Research started on 2 topics",
        "topics": ["Python async", "FastAPI security"],
        "interval_hours": 6
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        interval = timedelta(hours=request.interval_hours)
        
        success = await agent.start_scheduled_research(request.topics, interval)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Research already running. Stop it first."
            )
        
        return {
            "status": "started",
            "message": f"Research started on {len(request.topics)} topics",
            "topics": request.topics,
            "interval_hours": request.interval_hours,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start research error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research/stop")
async def stop_research():
    """
    Stop scheduled research.
    
    **Response:**
    ```json
    {
        "status": "stopped",
        "message": "Research stopped"
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        await agent.stop_research()
        
        return {
            "status": "stopped",
            "message": "Research stopped",
        }
        
    except Exception as e:
        logger.error(f"Stop research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Gap Analysis Endpoints ────────────────────────────────────────────


@router.post("/gap-analysis/start")
async def start_gap_analysis(request: GapAnalysisRequest):
    """
    Start periodic gap analysis.
    
    **Request Fields:**
    - `project_path`: Path to project root
    - `interval_hours`: Analysis interval in hours (1-168)
    
    **Response:**
    ```json
    {
        "status": "started",
        "message": "Gap analysis started for /path/to/project",
        "interval_hours": 24
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        interval = timedelta(hours=request.interval_hours)
        
        success = await agent.start_gap_analysis(request.project_path, interval)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Gap analysis already running. Stop it first."
            )
        
        return {
            "status": "started",
            "message": f"Gap analysis started for {request.project_path}",
            "interval_hours": request.interval_hours,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start gap analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gap-analysis/stop")
async def stop_gap_analysis():
    """
    Stop gap analysis.
    
    **Response:**
    ```json
    {
        "status": "stopped",
        "message": "Gap analysis stopped"
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        await agent.stop_gap_analysis()
        
        return {
            "status": "stopped",
            "message": "Gap analysis stopped",
        }
        
    except Exception as e:
        logger.error(f"Stop gap analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Control Endpoints ─────────────────────────────────────────────────


@router.post("/stop-all")
async def stop_all():
    """
    Stop all autonomous tasks.
    
    **Response:**
    ```json
    {
        "status": "stopped",
        "message": "All autonomous tasks stopped"
    }
    ```
    """
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        agent = get_autonomous_agent()
        agent.stop_all()
        
        return {
            "status": "stopped",
            "message": "All autonomous tasks stopped",
        }
        
    except Exception as e:
        logger.error(f"Stop all error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Event Streaming Endpoints ─────────────────────────────────────────


@router.get("/events")
async def stream_events(
    event_types: str = Query(
        default="",
        description="Comma-separated event types to filter (empty for all)"
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Number of historical events to include"
    ),
) -> StreamingResponse:
    """
    Stream autonomous agent events via SSE.
    
    **Query Parameters:**
    - `event_types`: Comma-separated list of event types to filter
      (watch_change, research_complete, gap_found, error)
    - `limit`: Number of historical events to include (1-500)
    
    **Event Types:**
    - `watch_change`: Repository changes detected
    - `research_complete`: Research task completed
    - `gap_found`: Gap analysis found issues
    - `error`: Error occurred
    
    **SSE Event Format:**
    ```
    data: {"id":"uuid","type":"watch_change","data":{...},"timestamp":"..."}
    
    ```
    
    **Usage:**
    ```javascript
    const eventSource = new EventSource('/autonomous/events?event_types=watch_change,gap_found');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Event:', data.type, data.data);
    };
    ```
    """
    # Parse event types
    types = [t.strip() for t in event_types.split(",") if t.strip()] if event_types else None
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        try:
            from packages.agents.event_bus import get_event_bus
            
            bus = get_event_bus()
            
            # Send historical events first
            if limit > 0:
                history = await bus.get_history(limit=limit, event_type=types[0] if len(types) == 1 else None)
                for event in history:
                    yield event.to_sse_data()
                # Send a marker to indicate end of history
                yield f"data: {__import__('json').dumps({'type': 'history_end', 'count': len(history)})}\n\n"
            
            # Stream new events
            async for event in bus.subscribe(event_types=types):
                yield event.to_sse_data()
                
        except asyncio.CancelledError:
            logger.info("Event stream cancelled")
        except Exception as e:
            logger.error(f"Event stream error: {e}")
            yield f"data: {__import__('json').dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/events/history")
async def get_event_history(
    limit: int = Query(default=50, ge=1, le=500),
    event_type: str = Query(default="", description="Filter by event type"),
):
    """
    Get event history (non-streaming).
    
    **Query Parameters:**
    - `limit`: Number of events to return (1-500)
    - `event_type`: Filter by event type (optional)
    
    **Response:**
    ```json
    {
        "events": [
            {
                "id": "uuid",
                "type": "watch_change",
                "data": {...},
                "timestamp": "2026-03-29T10:00:00",
                "source": "autonomous",
                "workspace_id": "default"
            }
        ],
        "count": 50
    }
    ```
    """
    try:
        from packages.agents.event_bus import get_event_bus
        
        bus = get_event_bus()
        events = await bus.get_history(
            limit=limit,
            event_type=event_type if event_type else None,
        )
        
        return {
            "events": [e.to_dict() for e in events],
            "count": len(events),
        }
        
    except Exception as e:
        logger.error(f"Get event history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/stats")
async def get_event_stats():
    """
    Get event bus statistics.
    
    **Response:**
    ```json
    {
        "workspace_id": "default",
        "history_size": 150,
        "queue_sizes": {
            "watch_change": 25,
            "research_complete": 50,
            "gap_found": 30,
            "error": 5
        },
        "subscriber_counts": {
            "watch_change": 2,
            "*": 1
        },
        "history_limit": 500,
        "history_ttl_hours": 24
    }
    ```
    """
    try:
        from packages.agents.event_bus import get_event_bus
        
        bus = get_event_bus()
        return bus.get_stats()
        
    except Exception as e:
        logger.error(f"Get event stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
