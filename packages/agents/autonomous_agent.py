"""
Autonomous Agent Core

Provides autonomous agents for:
- Continuous codebase monitoring (watch mode)
- Scheduled internet research
- Gap analysis
- Code quality evaluation

Features:
- Watch mode: Monitor repositories for changes
- Research: Scheduled internet research on topics
- Gap analysis: Identify missing features/issues
- Code quality: Evaluate code against best practices
- Event callbacks for real-time notifications

Usage:
    from packages.agents.autonomous_agent import AutonomousAgent, get_autonomous_agent
    
    agent = get_autonomous_agent()
    
    # Start watching a repository
    await agent.start_watch_mode("/path/to/repo", interval=timedelta(minutes=30))
    
    # Start scheduled research
    await agent.start_scheduled_research(
        topics=["Python async best practices", "FastAPI security"],
        interval=timedelta(hours=6)
    )
    
    # Start gap analysis
    await agent.start_gap_analysis("/path/to/project", interval=timedelta(days=1))
    
    # Register callbacks for events
    agent.register_callback("on_change", my_callback_function)
    agent.register_callback("on_research_complete", my_research_callback)
    agent.register_callback("on_gap_found", my_gap_callback)
    
    # Stop all tasks
    agent.stop_all()
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from packages.agents.crew import run_crew
from packages.agents.trace import TraceEvent, trace_manager
from packages.agents.event_bus import publish_event, Event
from packages.tools.web_search import search_and_scrape

logger = logging.getLogger(__name__)

# Default intervals
DEFAULT_WATCH_INTERVAL = timedelta(minutes=30)
DEFAULT_RESEARCH_INTERVAL = timedelta(hours=6)
DEFAULT_GAP_ANALYSIS_INTERVAL = timedelta(days=1)


class AutonomousAgent:
    """
    Autonomous agent for continuous monitoring and research.
    
    Capabilities:
    - Watch mode: Monitor codebase for changes
    - Research: Scheduled internet research on topics
    - Gap analysis: Identify missing features/issues
    - Code quality: Evaluate code against best practices
    
    Event Types:
    - watch_change: Detected changes in watched repository
    - research_complete: Research task completed
    - gap_found: Gap or issue identified
    - error: Error occurred during autonomous operation
    """
    
    def __init__(self, workspace_id: str = "default"):
        """
        Initialize autonomous agent.
        
        Args:
            workspace_id: Workspace identifier for memory and context
        """
        self.workspace_id = workspace_id
        
        # Task handles
        self.watch_task: Optional[asyncio.Task] = None
        self.research_task: Optional[asyncio.Task] = None
        self.gap_analysis_task: Optional[asyncio.Task] = None
        
        # State
        self.running = False
        self.watch_config: Optional[Dict[str, Any]] = None
        self.research_config: Optional[Dict[str, Any]] = None
        self.gap_analysis_config: Optional[Dict[str, Any]] = None
        
        # Callbacks
        self.callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {
            "on_change": [],
            "on_research_complete": [],
            "on_gap_found": [],
            "on_error": [],
        }
        
        # State tracking
        self.last_watch_status: Optional[Dict[str, Any]] = None
        self.last_research_results: List[Dict[str, Any]] = []
        self.last_gap_analysis: Optional[Dict[str, Any]] = None
        
        logger.info(f"AutonomousAgent initialized for workspace: {workspace_id}")
    
    def register_callback(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register callback for autonomous agent events.
        
        Args:
            event_type: One of "on_change", "on_research_complete", "on_gap_found", "on_error"
            callback: Function to call with event data
            
        Example:
            def on_change_handler(event_data):
                print(f"Changes detected: {event_data['changed_files']}")
            
            agent.register_callback("on_change", on_change_handler)
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"Registered callback for {event_type}")
        else:
            logger.warning(f"Unknown event type: {event_type}")
    
    def unregister_callback(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Unregister a callback.
        
        Args:
            event_type: Event type to unregister from
            callback: Callback function to remove
        """
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            logger.info(f"Unregistered callback from {event_type}")
    
    def _trigger_callback(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Trigger all callbacks for an event type.
        
        Args:
            event_type: Type of event
            data: Event data to pass to callbacks
        """
        # Trigger callbacks
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event_type}: {e}")
        
        # Publish to event bus
        asyncio.create_task(
            publish_event(event_type, data, source="autonomous"),
            name=f"event-bus-{event_type}"
        )
    
    # ─────────────────────────────────────────────────────────────────────
    # Watch Mode
    # ─────────────────────────────────────────────────────────────────────
    
    async def start_watch_mode(
        self,
        repo_path: str,
        interval: timedelta = DEFAULT_WATCH_INTERVAL,
    ) -> bool:
        """
        Start watching a repository for changes.
        
        When changes are detected, analyzes them and triggers callbacks.
        
        Args:
            repo_path: Path to git repository to watch
            interval: How often to check for changes
            
        Returns:
            True if started successfully, False if already running
            
        Example:
            await agent.start_watch_mode(
                "/path/to/repo",
                interval=timedelta(minutes=30)
            )
        """
        if self.watch_task and not self.watch_task.done():
            logger.warning("Watch mode already running")
            return False
        
        logger.info(f"Starting watch mode for {repo_path} (interval: {interval})")
        self.running = True
        self.watch_config = {
            "repo_path": repo_path,
            "interval": interval,
            "started_at": datetime.now().isoformat(),
        }
        
        self.watch_task = asyncio.create_task(
            self._watch_loop(repo_path, interval),
            name=f"autonomous-watch-{Path(repo_path).name}"
        )
        
        return True
    
    async def _watch_loop(
        self,
        repo_path: str,
        interval: timedelta,
    ) -> None:
        """
        Watch loop: check for changes periodically.
        
        Args:
            repo_path: Path to repository
            interval: Check interval
        """
        while self.running:
            try:
                # Get current git status
                from packages.tools.repo import git_status, git_diff
                
                status = await git_status(repo_path)
                
                # Check if anything changed
                if status != self.last_watch_status:
                    logger.info(f"Changes detected in {repo_path}")
                    
                    # Analyze changes
                    analysis = await self._analyze_changes(
                        repo_path,
                        self.last_watch_status,
                        status,
                    )
                    
                    # Update last status
                    self.last_watch_status = status
                    
                    # Trigger callbacks
                    self._trigger_callback("on_change", analysis)
                    
                    # Create trace event
                    await self._create_trace_event(
                        "watch_change",
                        f"Changes detected in {Path(repo_path).name}",
                        analysis,
                    )
                
                # Wait for next check
                await asyncio.sleep(interval.total_seconds())
                
            except asyncio.CancelledError:
                logger.info("Watch mode cancelled")
                break
            except Exception as e:
                logger.error(f"Watch loop error: {e}", exc_info=True)
                self._trigger_callback("on_error", {
                    "error": str(e),
                    "task": "watch_mode",
                    "timestamp": datetime.now().isoformat(),
                })
                await asyncio.sleep(interval.total_seconds())
    
    async def _analyze_changes(
        self,
        repo_path: str,
        old_status: Optional[Dict],
        new_status: Dict,
    ) -> Dict[str, Any]:
        """
        Analyze what changed in the repository.
        
        Args:
            repo_path: Path to repository
            old_status: Previous git status
            new_status: Current git status
            
        Returns:
            Analysis dict with changed files, risk level, etc.
        """
        from packages.tools.repo import git_diff, repo_summary
        
        # Get detailed diff
        diff = await git_diff(repo_path, staged=False)
        
        # Get repo summary
        summary = await repo_summary(repo_path)
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "repo_path": str(repo_path),
            "status": new_status,
            "diff_summary": diff.get("output", "")[:1000] if diff else "",
            "summary": summary,
            "changed_files": [],
            "risk_level": "low",
        }
        
        # Extract changed files from diff
        if diff and "output" in diff:
            diff_text = diff["output"]
            for line in diff_text.split("\n"):
                if line.startswith("diff --git"):
                    parts = line.split()
                    if len(parts) >= 3:
                        file_path = parts[2][2:]  # Remove "a/" prefix
                        analysis["changed_files"].append(file_path)
        
        # Determine risk level
        risky_patterns = [
            ".env", "credentials", "config", "requirements",
            "package.json", "Cargo.toml", "pyproject.toml",
        ]
        for file in analysis["changed_files"]:
            if any(p in file.lower() for p in risky_patterns):
                analysis["risk_level"] = "medium"
                break
        
        logger.info(
            f"Analyzed changes: {len(analysis['changed_files'])} files, "
            f"risk: {analysis['risk_level']}"
        )
        
        return analysis
    
    async def stop_watch_mode(self) -> None:
        """
        Stop watch mode.
        
        Cancels the watch task and clears configuration.
        """
        if self.watch_task and not self.watch_task.done():
            logger.info("Stopping watch mode...")
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        
        self.watch_task = None
        self.watch_config = None
        self.last_watch_status = None
        logger.info("Watch mode stopped")
    
    # ─────────────────────────────────────────────────────────────────────
    # Scheduled Research
    # ─────────────────────────────────────────────────────────────────────
    
    async def start_scheduled_research(
        self,
        topics: List[str],
        interval: timedelta = DEFAULT_RESEARCH_INTERVAL,
    ) -> bool:
        """
        Start scheduled research on topics.
        
        Runs internet research periodically and stores findings.
        
        Args:
            topics: List of topics to research
            interval: How often to research each topic
            
        Returns:
            True if started successfully, False if already running
            
        Example:
            await agent.start_scheduled_research(
                topics=[
                    "Python async best practices 2026",
                    "FastAPI security guidelines",
                ],
                interval=timedelta(hours=6)
            )
        """
        if self.research_task and not self.research_task.done():
            logger.warning("Research task already running")
            return False
        
        logger.info(f"Starting scheduled research on: {topics} (interval: {interval})")
        self.running = True
        self.research_config = {
            "topics": topics,
            "interval": interval,
            "started_at": datetime.now().isoformat(),
        }
        
        self.research_task = asyncio.create_task(
            self._research_loop(topics, interval),
            name="autonomous-research"
        )
        
        return True
    
    async def _research_loop(
        self,
        topics: List[str],
        interval: timedelta,
    ) -> None:
        """
        Research loop: research topics periodically.
        
        Args:
            topics: Topics to research
            interval: Research interval
        """
        while self.running:
            try:
                for topic in topics:
                    if not self.running:
                        break
                    
                    logger.info(f"Researching topic: {topic}")
                    
                    # Run research
                    findings = await self._research_topic(topic)
                    
                    # Store findings
                    self.last_research_results.append(findings)
                    
                    # Keep only last 10 results
                    if len(self.last_research_results) > 10:
                        self.last_research_results = self.last_research_results[-10:]
                    
                    # Trigger callbacks
                    self._trigger_callback("on_research_complete", findings)
                    
                    # Create trace event
                    await self._create_trace_event(
                        "research_complete",
                        f"Research completed: {topic[:50]}...",
                        findings,
                    )
                    
                    # Wait between topics
                    await asyncio.sleep(60)
                
                # Wait for next cycle
                await asyncio.sleep(interval.total_seconds())
                
            except asyncio.CancelledError:
                logger.info("Research task cancelled")
                break
            except Exception as e:
                logger.error(f"Research loop error: {e}", exc_info=True)
                self._trigger_callback("on_error", {
                    "error": str(e),
                    "task": "research",
                    "timestamp": datetime.now().isoformat(),
                })
                await asyncio.sleep(interval.total_seconds())
    
    async def _research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Research a single topic using web search and agent analysis.
        
        Args:
            topic: Topic to research
            
        Returns:
            Research findings dict
        """
        # Search web
        search_results = await search_and_scrape(topic, max_urls=3)
        
        # Run agent analysis
        research_prompt = (
            f"Research the following topic and provide a comprehensive summary:\n\n"
            f"Topic: {topic}\n\n"
            f"Web search results:\n"
            f"{json.dumps(search_results, indent=2)}\n\n"
            f"Provide:\n"
            f"1. Key findings and developments\n"
            f"2. Best practices and recommendations\n"
            f"3. Common pitfalls to avoid\n"
            f"4. Relevant sources and references\n\n"
            f"Focus on recent information (last 6 months)."
        )
        
        # Execute research via agent crew
        result = await run_crew(
            user_message=research_prompt,
            user_id=self.workspace_id,
            model="local",
            enable_tools=True,
        )
        
        findings = {
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "search_results": search_results,
            "analysis": result.get("response", "")[:5000],
            "sources": [r.get("url") for r in search_results if r.get("url")],
        }
        
        logger.info(f"Researched topic '{topic}': {len(findings['analysis'])} chars")
        return findings
    
    async def stop_research(self) -> None:
        """
        Stop scheduled research.
        
        Cancels the research task and clears configuration.
        """
        if self.research_task and not self.research_task.done():
            logger.info("Stopping research task...")
            self.research_task.cancel()
            try:
                await self.research_task
            except asyncio.CancelledError:
                pass
        
        self.research_task = None
        self.research_config = None
        logger.info("Research task stopped")
    
    # ─────────────────────────────────────────────────────────────────────
    # Gap Analysis
    # ─────────────────────────────────────────────────────────────────────
    
    async def start_gap_analysis(
        self,
        project_path: str,
        interval: timedelta = DEFAULT_GAP_ANALYSIS_INTERVAL,
    ) -> bool:
        """
        Start periodic gap analysis for a project.
        
        Analyzes codebase for:
        - Missing documentation
        - TODO/FIXME comments
        - Potential bugs
        - Architecture inconsistencies
        - Missing tests
        - Dependency updates
        
        Args:
            project_path: Path to project root
            interval: How often to run analysis
            
        Returns:
            True if started successfully, False if already running
            
        Example:
            await agent.start_gap_analysis(
                "/path/to/project",
                interval=timedelta(days=1)
            )
        """
        if self.gap_analysis_task and not self.gap_analysis_task.done():
            logger.warning("Gap analysis already running")
            return False
        
        logger.info(f"Starting gap analysis for {project_path} (interval: {interval})")
        self.running = True
        self.gap_analysis_config = {
            "project_path": project_path,
            "interval": interval,
            "started_at": datetime.now().isoformat(),
        }
        
        self.gap_analysis_task = asyncio.create_task(
            self._gap_analysis_loop(project_path, interval),
            name="autonomous-gap-analysis"
        )
        
        return True
    
    async def _gap_analysis_loop(
        self,
        project_path: str,
        interval: timedelta,
    ) -> None:
        """
        Gap analysis loop: analyze project periodically.
        
        Args:
            project_path: Path to project
            interval: Analysis interval
        """
        while self.running:
            try:
                logger.info(f"Running gap analysis for {project_path}")
                
                # Run gap analysis agent
                analysis = await self._run_gap_analysis(project_path)
                
                # Store analysis
                self.last_gap_analysis = analysis
                
                # Trigger callbacks
                self._trigger_callback("on_gap_found", analysis)
                
                # Create trace event
                await self._create_trace_event(
                    "gap_found",
                    f"Gap analysis completed: {len(analysis.get('gaps', []))} gaps found",
                    analysis,
                )
                
                # Wait for next cycle
                await asyncio.sleep(interval.total_seconds())
                
            except asyncio.CancelledError:
                logger.info("Gap analysis cancelled")
                break
            except Exception as e:
                logger.error(f"Gap analysis error: {e}", exc_info=True)
                self._trigger_callback("on_error", {
                    "error": str(e),
                    "task": "gap_analysis",
                    "timestamp": datetime.now().isoformat(),
                })
                await asyncio.sleep(interval.total_seconds())
    
    async def _run_gap_analysis(self, project_path: str) -> Dict[str, Any]:
        """
        Run gap analysis on a project.
        
        Args:
            project_path: Path to project
            
        Returns:
            Analysis dict with gaps and recommendations
        """
        from packages.tools.fs import list_directory
        
        # Analyze project structure
        structure = await list_directory(project_path)
        
        # Run gap analysis agent
        analysis_prompt = (
            f"Analyze this project for gaps and improvements:\n\n"
            f"Project path: {project_path}\n\n"
            f"Project structure:\n"
            f"{json.dumps(structure, indent=2)}\n\n"
            f"Look for:\n"
            f"1. Missing documentation (README, docstrings, API docs)\n"
            f"2. TODO/FIXME comments that need attention\n"
            f"3. Code quality issues (complexity, duplication, smells)\n"
            f"4. Missing tests or low test coverage\n"
            f"5. Architecture inconsistencies\n"
            f"6. Dependency updates needed\n"
            f"7. Security vulnerabilities\n"
            f"8. Performance optimization opportunities\n\n"
            f"Provide a prioritized list of gaps with:\n"
            f"- Description of the gap\n"
            f"- Severity (critical/high/medium/low)\n"
            f"- Recommended fix\n"
            f"- Estimated effort (small/medium/large)"
        )
        
        # Execute analysis agent
        result = await run_crew(
            user_message=analysis_prompt,
            user_id=self.workspace_id,
            model="local",
            enable_tools=True,
        )
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(project_path),
            "structure": structure,
            "analysis": result.get("response", ""),
            "gaps": self._parse_gaps_from_analysis(result.get("response", "")),
        }
        
        logger.info(f"Gap analysis: {len(analysis['gaps'])} gaps found")
        return analysis
    
    def _parse_gaps_from_analysis(self, analysis_text: str) -> List[Dict[str, Any]]:
        """
        Parse gaps from analysis text.
        
        Simple parser that extracts gap items from structured text.
        
        Args:
            analysis_text: Analysis text from agent
            
        Returns:
            List of gap dicts
        """
        gaps = []
        
        # Simple line-by-line parsing
        lines = analysis_text.split("\n")
        current_gap = None
        
        for line in lines:
            line = line.strip()
            
            # Look for gap markers
            if any(marker in line.lower() for marker in ["- [", "1.", "2.", "3.", "•"]):
                if current_gap:
                    gaps.append(current_gap)
                
                current_gap = {
                    "description": line,
                    "severity": "medium",
                    "recommendation": "",
                    "effort": "medium",
                }
                
                # Extract severity
                if "critical" in line.lower():
                    current_gap["severity"] = "critical"
                elif "high" in line.lower():
                    current_gap["severity"] = "high"
                elif "low" in line.lower():
                    current_gap["severity"] = "low"
            
            elif current_gap:
                current_gap["recommendation"] += line + " "
        
        if current_gap:
            gaps.append(current_gap)
        
        return gaps
    
    async def stop_gap_analysis(self) -> None:
        """
        Stop gap analysis.
        
        Cancels the gap analysis task and clears configuration.
        """
        if self.gap_analysis_task and not self.gap_analysis_task.done():
            logger.info("Stopping gap analysis...")
            self.gap_analysis_task.cancel()
            try:
                await self.gap_analysis_task
            except asyncio.CancelledError:
                pass
        
        self.gap_analysis_task = None
        self.gap_analysis_config = None
        logger.info("Gap analysis stopped")
    
    # ─────────────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────────────
    
    async def _create_trace_event(
        self,
        event_type: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Create a trace event for autonomous agent actions.
        
        Args:
            event_type: Type of event
            content: Event content/description
            metadata: Additional metadata
        """
        try:
            await trace_manager.emit_event(
                TraceEvent(
                    run_id=f"autonomous-{self.workspace_id}",
                    agent_name="autonomous",
                    event_type=event_type,
                    content=content[:500],  # Truncate long content
                    timestamp=datetime.now().isoformat(),
                    metadata=metadata,
                )
            )
        except Exception as e:
            logger.error(f"Failed to create trace event: {e}")
    
    def stop_all(self) -> None:
        """
        Stop all autonomous tasks.
        
        Stops watch mode, research, and gap analysis.
        """
        logger.info("Stopping all autonomous tasks")
        self.running = False
        
        # Cancel all tasks
        for task in [self.watch_task, self.research_task, self.gap_analysis_task]:
            if task and not task.done():
                task.cancel()
        
        # Clear configs
        self.watch_config = None
        self.research_config = None
        self.gap_analysis_config = None
        
        logger.info("All autonomous tasks stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current autonomous agent status.
        
        Returns:
            Status dict with task states and configs
        """
        return {
            "workspace_id": self.workspace_id,
            "running": self.running,
            "watch_mode": {
                "active": self.watch_task is not None and not self.watch_task.done(),
                "config": self.watch_config,
                "last_status": self.last_watch_status,
            },
            "research": {
                "active": self.research_task is not None and not self.research_task.done(),
                "config": self.research_config,
                "last_results_count": len(self.last_research_results),
            },
            "gap_analysis": {
                "active": self.gap_analysis_task is not None and not self.gap_analysis_task.done(),
                "config": self.gap_analysis_config,
                "last_analysis": self.last_gap_analysis,
            },
            "callbacks_registered": {
                event_type: len(callbacks)
                for event_type, callbacks in self.callbacks.items()
            },
        }


# Global autonomous agent instance (singleton pattern)
_autonomous_agent: Optional[AutonomousAgent] = None


def get_autonomous_agent(workspace_id: str = "default") -> AutonomousAgent:
    """
    Get or create the global autonomous agent.
    
    Args:
        workspace_id: Workspace identifier
        
    Returns:
        Global AutonomousAgent instance
    """
    global _autonomous_agent
    if _autonomous_agent is None:
        _autonomous_agent = AutonomousAgent(workspace_id)
    return _autonomous_agent


def reset_autonomous_agent() -> None:
    """
    Reset the global autonomous agent (for testing).
    
    Clears the singleton instance.
    """
    global _autonomous_agent
    if _autonomous_agent:
        _autonomous_agent.stop_all()
    _autonomous_agent = None


# Convenience functions

async def start_autonomous_watch(
    repo_path: str,
    interval: timedelta = DEFAULT_WATCH_INTERVAL,
) -> bool:
    """
    Start autonomous watch mode (convenience function).
    
    Args:
        repo_path: Path to repository
        interval: Check interval
        
    Returns:
        True if started successfully
    """
    agent = get_autonomous_agent()
    return await agent.start_watch_mode(repo_path, interval)


async def start_autonomous_research(
    topics: List[str],
    interval: timedelta = DEFAULT_RESEARCH_INTERVAL,
) -> bool:
    """
    Start autonomous research (convenience function).
    
    Args:
        topics: Topics to research
        interval: Research interval
        
    Returns:
        True if started successfully
    """
    agent = get_autonomous_agent()
    return await agent.start_scheduled_research(topics, interval)


async def start_autonomous_gap_analysis(
    project_path: str,
    interval: timedelta = DEFAULT_GAP_ANALYSIS_INTERVAL,
) -> bool:
    """
    Start autonomous gap analysis (convenience function).
    
    Args:
        project_path: Path to project
        interval: Analysis interval
        
    Returns:
        True if started successfully
    """
    agent = get_autonomous_agent()
    return await agent.start_gap_analysis(project_path, interval)


def stop_autonomous_all() -> None:
    """
    Stop all autonomous tasks (convenience function).
    """
    agent = get_autonomous_agent()
    agent.stop_all()


def get_autonomous_status() -> Dict[str, Any]:
    """
    Get autonomous agent status (convenience function).
    
    Returns:
        Status dict
    """
    agent = get_autonomous_agent()
    return agent.get_status()
