import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from packages.agents.crew import run_crew
from packages.automation.sync import create_qdrant_snapshot

logger = logging.getLogger(__name__)

async def run_daily_briefing():
    """
    Proactive agent that runs in the background.
    Generates a summary of recent local activity and stores it in memory.
    """
    logger.info("Running Daily Briefing Background Job")
    try:
        # Prompt the agent to generate a briefing based on recent commit activity
        # and store it in Memory for the user to read later.
        message = (
            "You are the Daily Briefing Agent running proactively in the background. "
            "Please use the repo.py tool (toolRepoSummary) or fs.py to summarize recent project updates. "
            "Then, store your summary as a 'BACKGROUND_BRIEFING' memory so the user can read it later."
        )
        
        # Fire and forget the crew
        result = await run_crew(
            user_message=message,
            user_id="default",
            model="local"
        )
        resp = result.get("response", "")
        logger.info("Daily Briefing Completed: %s", resp[:100] + "...")
    except Exception as exc:
        logger.error("Daily Briefing failed: %s", exc)

def setup_jobs(scheduler: AsyncIOScheduler):
    """Register all scheduled tasks."""
    # Run the daily briefing every morning at 8:00 AM
    scheduler.add_job(
        run_daily_briefing,
        'cron',
        hour=8,
        minute=0,
        id='daily_briefing',
        replace_existing=True
    )
    
    # Run the Qdrant Snapshot Sync every hour
    scheduler.add_job(
        create_qdrant_snapshot,
        'interval',
        hours=1,
        id='qdrant_sync_snapshot',
        replace_existing=True
    )
    
    logger.info("Registered Background Jobs (Daily Briefing at 8:00 AM, Hourly Sync Snapshots)")
