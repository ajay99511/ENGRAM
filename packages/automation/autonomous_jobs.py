"""
ARQ Worker Tasks for Autonomous Agent

Provides background job tasks for:
- Watch mode execution
- Research task execution
- Gap analysis execution
- Event publishing

These tasks run in the ARQ worker pool and provide:
- Job persistence in Redis
- Automatic retries on failure
- Job status tracking
- Scheduled execution

Usage:
    # Jobs are automatically picked up by ARQ worker
    # Submit via API endpoints or directly via Redis
    
    from arq import create_pool
    from arq.connections import RedisSettings
    
    redis = await create_pool(RedisSettings())
    await redis.enqueue_job("autonomous_watch_execute", repo_path="/path/to/repo")
    await redis.enqueue_job("autonomous_research_execute", topics=["topic1", "topic2"])
    await redis.enqueue_job("autonomous_gap_analysis_execute", project_path="/path/to/project")

Worker Setup:
    # In packages/automation/arq_worker.py, add to WorkerSettings:
    functions = [
        # ... existing functions ...
        autonomous_watch_execute,
        autonomous_research_execute,
        autonomous_gap_analysis_execute,
    ]
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from arq.worker import Worker

logger = logging.getLogger(__name__)

# Job timeout settings
WATCH_MODE_TIMEOUT = 300  # 5 minutes
RESEARCH_TIMEOUT = 600    # 10 minutes
GAP_ANALYSIS_TIMEOUT = 900  # 15 minutes

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds


async def autonomous_watch_execute(
    ctx: Dict[str, Any],
    repo_path: str,
) -> Dict[str, Any]:
    """
    Execute watch mode check for a repository.
    
    This job checks a repository for changes and triggers callbacks.
    Runs periodically via ARQ scheduler.
    
    Args:
        ctx: Job context (includes job_id, retry, etc.)
        repo_path: Path to git repository to watch
        
    Returns:
        Job result dict with status and findings
        
    Example:
        await redis.enqueue_job("autonomous_watch_execute", repo_path="/path/to/repo")
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[{job_id}] Starting watch mode check for {repo_path}")
    
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        from packages.tools.repo import git_status
        
        # Get agent instance
        agent = get_autonomous_agent()
        
        # Get current git status
        status = await git_status(repo_path)
        
        # Compare with last known status
        changes_detected = status != agent.last_watch_status
        
        result = {
            "job_id": job_id,
            "status": "success",
            "repo_path": repo_path,
            "timestamp": datetime.now().isoformat(),
            "changes_detected": changes_detected,
            "files_changed": 0,
        }
        
        if changes_detected:
            # Analyze changes
            analysis = await agent._analyze_changes(
                repo_path,
                agent.last_watch_status,
                status,
            )
            
            result["files_changed"] = len(analysis.get("changed_files", []))
            result["risk_level"] = analysis.get("risk_level", "unknown")
            result["analysis"] = analysis
            
            # Trigger callbacks
            agent._trigger_callback("on_change", analysis)
            
            logger.info(f"[{job_id}] Changes detected: {result['files_changed']} files")
        else:
            logger.info(f"[{job_id}] No changes detected")
        
        # Update last status
        agent.last_watch_status = status
        
        return result
        
    except Exception as e:
        logger.error(f"[{job_id}] Watch mode error: {e}", exc_info=True)
        
        # Trigger error callback
        try:
            from packages.agents.autonomous_agent import get_autonomous_agent
            agent = get_autonomous_agent()
            agent._trigger_callback("on_error", {
                "error": str(e),
                "task": "watch_mode",
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
            })
        except:
            pass
        
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e),
            "repo_path": repo_path,
            "timestamp": datetime.now().isoformat(),
        }


async def autonomous_research_execute(
    ctx: Dict[str, Any],
    topics: List[str],
) -> Dict[str, Any]:
    """
    Execute research on specified topics.
    
    This job researches topics using web search and agent analysis.
    Runs periodically via ARQ scheduler.
    
    Args:
        ctx: Job context
        topics: List of topics to research
        
    Returns:
        Job result dict with research findings
        
    Example:
        await redis.enqueue_job("autonomous_research_execute", 
                               topics=["Python async", "FastAPI security"])
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[{job_id}] Starting research on {len(topics)} topics")
    
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        # Get agent instance
        agent = get_autonomous_agent()
        
        results = []
        for topic in topics:
            logger.info(f"[{job_id}] Researching: {topic}")
            
            # Research topic
            findings = await agent._research_topic(topic)
            results.append(findings)
            
            # Store findings
            agent.last_research_results.append(findings)
            
            # Keep only last 10
            if len(agent.last_research_results) > 10:
                agent.last_research_results = agent.last_research_results[-10:]
            
            # Trigger callbacks
            agent._trigger_callback("on_research_complete", findings)
        
        return {
            "job_id": job_id,
            "status": "success",
            "topics": topics,
            "timestamp": datetime.now().isoformat(),
            "results_count": len(results),
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Research error: {e}", exc_info=True)
        
        # Trigger error callback
        try:
            from packages.agents.autonomous_agent import get_autonomous_agent
            agent = get_autonomous_agent()
            agent._trigger_callback("on_error", {
                "error": str(e),
                "task": "research",
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
            })
        except:
            pass
        
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e),
            "topics": topics,
            "timestamp": datetime.now().isoformat(),
        }


async def autonomous_gap_analysis_execute(
    ctx: Dict[str, Any],
    project_path: str,
) -> Dict[str, Any]:
    """
    Execute gap analysis on a project.
    
    This job analyzes a project for gaps and improvements.
    Runs periodically via ARQ scheduler.
    
    Args:
        ctx: Job context
        project_path: Path to project root
        
    Returns:
        Job result dict with analysis findings
        
    Example:
        await redis.enqueue_job("autonomous_gap_analysis_execute", 
                               project_path="/path/to/project")
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[{job_id}] Starting gap analysis for {project_path}")
    
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        
        # Get agent instance
        agent = get_autonomous_agent()
        
        # Run gap analysis
        analysis = await agent._run_gap_analysis(project_path)
        
        # Store analysis
        agent.last_gap_analysis = analysis
        
        # Trigger callbacks
        agent._trigger_callback("on_gap_found", analysis)
        
        return {
            "job_id": job_id,
            "status": "success",
            "project_path": project_path,
            "timestamp": datetime.now().isoformat(),
            "gaps_found": len(analysis.get("gaps", [])),
            "analysis": analysis,
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Gap analysis error: {e}", exc_info=True)
        
        # Trigger error callback
        try:
            from packages.agents.autonomous_agent import get_autonomous_agent
            agent = get_autonomous_agent()
            agent._trigger_callback("on_error", {
                "error": str(e),
                "task": "gap_analysis",
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
            })
        except:
            pass
        
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e),
            "project_path": project_path,
            "timestamp": datetime.now().isoformat(),
        }


async def autonomous_cleanup_old_results(
    ctx: Dict[str, Any],
    max_age_days: int = 7,
) -> Dict[str, Any]:
    """
    Clean up old autonomous agent results.
    
    This job removes old research results and gap analyses
    to prevent memory growth.
    
    Args:
        ctx: Job context
        max_age_days: Maximum age of results to keep
        
    Returns:
        Job result dict with cleanup statistics
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[{job_id}] Starting cleanup of old results (max age: {max_age_days} days)")
    
    try:
        from packages.agents.autonomous_agent import get_autonomous_agent
        from datetime import timedelta
        
        # Get agent instance
        agent = get_autonomous_agent()
        
        # Calculate cutoff
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        # Clean up old research results
        old_count = len(agent.last_research_results)
        agent.last_research_results = [
            r for r in agent.last_research_results
            if datetime.fromisoformat(r.get("timestamp", "1970-01-01")) > cutoff
        ]
        cleaned_research = old_count - len(agent.last_research_results)
        
        # Clean up old gap analysis
        if agent.last_gap_analysis:
            analysis_time = datetime.fromisoformat(
                agent.last_gap_analysis.get("timestamp", "1970-01-01")
            )
            if analysis_time <= cutoff:
                agent.last_gap_analysis = None
                cleaned_gap = 1
            else:
                cleaned_gap = 0
        else:
            cleaned_gap = 0
        
        return {
            "job_id": job_id,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "research_results_cleaned": cleaned_research,
            "gap_analyses_cleaned": cleaned_gap,
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Cleanup error: {e}", exc_info=True)
        return {
            "job_id": job_id,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# Job configuration for ARQ
# Add these to your WorkerSettings in packages/automation/arq_worker.py

AUTONOMOUS_JOB_FUNCTIONS = [
    autonomous_watch_execute,
    autonomous_research_execute,
    autonomous_gap_analysis_execute,
    autonomous_cleanup_old_results,
]

# Job timeout configuration
AUTONOMOUS_JOB_TIMEOUTS = {
    "autonomous_watch_execute": WATCH_MODE_TIMEOUT,
    "autonomous_research_execute": RESEARCH_TIMEOUT,
    "autonomous_gap_analysis_execute": GAP_ANALYSIS_TIMEOUT,
    "autonomous_cleanup_old_results": 60,
}

# Retry configuration
AUTONOMOUS_JOB_RETRIES = {
    "autonomous_watch_execute": MAX_RETRIES,
    "autonomous_research_execute": MAX_RETRIES,
    "autonomous_gap_analysis_execute": MAX_RETRIES,
    "autonomous_cleanup_old_results": 1,
}
