"""
Telegram Bot Manager

Manages the Telegram bot lifecycle with start/stop/reload capabilities.
Provides status tracking and coordinates with the ConfigStore for persistence.

Features:
- Lifecycle management (start, stop, reload)
- Status tracking (state, started_at, error_message, uptime)
- Async lock for thread safety
- Integration with ConfigStore for persistent configuration
- Graceful shutdown with cleanup
- Error handling and recovery

Usage:
    from packages.messaging.bot_manager import BotManager, get_bot_manager
    
    # Get singleton instance
    manager = get_bot_manager()
    
    # Start bot with configuration
    await manager.start(
        token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        dm_policy="pairing"
    )
    
    # Get status
    status = manager.get_status()
    # {
    #     "state": "running",
    #     "dm_policy": "pairing",
    #     "started_at": "2026-03-29T10:00:00",
    #     "uptime_seconds": 3600
    # }
    
    # Reload with new configuration
    await manager.reload(new_token, "open")
    
    # Stop bot
    await manager.stop()
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

# Avoid circular import
if TYPE_CHECKING:
    from packages.messaging.telegram_bot import TelegramBotService

logger = logging.getLogger(__name__)


class BotManager:
    """
    Manages Telegram bot lifecycle.
    
    Responsibilities:
    - Start/stop bot instances
    - Handle hot-reload on config changes
    - Track status (state, started_at, errors)
    - Coordinate with API via events
    - Provide thread-safe access to bot state
    
    State Machine:
        stopped → starting → running → stopping → stopped
                          ↓
                        error
    
    Usage:
        manager = BotManager()
        await manager.start(token, dm_policy)
        status = manager.get_status()
        await manager.reload(new_token, new_policy)
        await manager.stop()
    """
    
    def __init__(self):
        """Initialize bot manager."""
        self.bot_service: Optional["TelegramBotService"] = None
        self.bot_task: Optional[asyncio.Task] = None
        self.config: Dict[str, str] = {
            "bot_token": "",
            "dm_policy": "pairing"
        }
        
        # State tracking
        self.state = "stopped"  # stopped | starting | running | error | reloading | stopping
        self.started_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        
        # Thread safety
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
    
    async def start(self, token: str, dm_policy: str = "pairing") -> bool:
        """
        Start bot with configuration.
        
        Args:
            token: Telegram bot token
            dm_policy: DM policy ("pairing", "allowlist", or "open")
        
        Returns:
            True if started successfully, False otherwise
        
        Raises:
            ValueError: If token is empty or dm_policy is invalid
        
        Example:
            >>> manager = BotManager()
            >>> success = await manager.start("123456:...", "pairing")
            >>> if success:
            ...     print("Bot started successfully")
        """
        async with self._lock:
            # Validate inputs
            if not token or not token.strip():
                logger.warning("Cannot start bot: empty token provided")
                return False
            
            if dm_policy not in ("pairing", "allowlist", "open"):
                logger.error(f"Invalid DM policy: {dm_policy}")
                return False
            
            # Check if already running
            if self.state == "running":
                logger.warning("Bot already running, ignoring start request")
                return True
            
            # Check if in transitional state
            if self.state in ("starting", "reloading", "stopping"):
                logger.warning(f"Bot in {self.state} state, ignoring start request")
                return False
            
            try:
                logger.info(f"Starting Telegram bot with DM policy: {dm_policy}")
                self.state = "starting"
                self.config = {
                    "bot_token": token,
                    "dm_policy": dm_policy
                }
                
                # Create new bot service instance
                from packages.messaging.telegram_bot import TelegramBotService
                self.bot_service = TelegramBotService()
                
                # Clear stop event
                self._stop_event.clear()
                
                # Start bot in background task
                self.bot_task = asyncio.create_task(
                    self._run_bot_loop(token, dm_policy),
                    name="telegram-bot-poll"
                )
                
                logger.info("Bot manager started bot instance")
                return True
                
            except Exception as e:
                self.state = "error"
                self.error_message = str(e)
                logger.error(f"Failed to start bot: {e}", exc_info=True)
                return False
    
    async def _run_bot_loop(self, token: str, dm_policy: str) -> None:
        """
        Run bot polling loop with error handling.
        
        This method:
        1. Sets environment variables for bot service
        2. Starts the bot polling
        3. Monitors for stop event
        4. Cleans up on exit
        
        Args:
            token: Bot token for this session
            dm_policy: DM policy for this session
        """
        # Save old env vars for restoration
        old_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        old_policy = os.environ.get("TELEGRAM_DM_POLICY", "pairing")
        
        try:
            # Set environment variables for bot service
            os.environ["TELEGRAM_BOT_TOKEN"] = token
            os.environ["TELEGRAM_DM_POLICY"] = dm_policy
            
            logger.info("Bot polling loop starting...")
            
            # Import here to avoid circular dependency
            from packages.messaging.telegram_bot import TelegramBotService
            
            # Create and run bot
            bot_service = TelegramBotService()
            
            # Mark as running
            self.state = "running"
            self.started_at = datetime.now()
            self.error_message = None
            
            logger.info(f"Telegram bot is running! (policy: {dm_policy})")
            
            # Run bot until stop event is set
            while not self._stop_event.is_set():
                try:
                    # Process updates
                    if bot_service.application:
                        await bot_service.application.updater.start_polling()
                        
                        # Keep running until cancelled or stop event
                        while not self._stop_event.is_set():
                            await asyncio.sleep(1)
                            
                            # Check if updater is still running
                            if not bot_service.application.updater.running:
                                logger.warning("Bot updater stopped unexpectedly")
                                break
                    else:
                        logger.error("Bot application not initialized")
                        break
                        
                except asyncio.CancelledError:
                    logger.info("Bot polling loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Bot polling error: {e}", exc_info=True)
                    
                    # Wait before retry
                    await asyncio.sleep(5)
            
        except Exception as e:
            self.state = "error"
            self.error_message = str(e)
            logger.error(f"Bot error: {e}", exc_info=True)
            
        finally:
            # Restore old env vars
            if old_token:
                os.environ["TELEGRAM_BOT_TOKEN"] = old_token
            else:
                os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            
            if old_policy:
                os.environ["TELEGRAM_DM_POLICY"] = old_policy
            else:
                os.environ.pop("TELEGRAM_DM_POLICY", None)
            
            # Update state
            if self.state not in ("error", "reloading"):
                self.state = "stopped"
            
            logger.info("Bot polling loop exited")
    
    async def stop(self) -> None:
        """
        Stop the bot gracefully.
        
        This method:
        1. Sets stop event
        2. Cancels background task
        3. Cleans up bot service
        4. Resets state
        
        Example:
            >>> await manager.stop()
            >>> print(manager.state)
            'stopped'
        """
        async with self._lock:
            if self.state not in ("running", "starting", "error"):
                logger.debug(f"Bot in {self.state} state, ignoring stop request")
                return
            
            logger.info("Stopping bot manager...")
            self.state = "stopping"
            
            # Signal bot loop to stop
            self._stop_event.set()
            
            # Cancel background task
            if self.bot_task and not self.bot_task.done():
                self.bot_task.cancel()
                try:
                    await self.bot_task
                except asyncio.CancelledError:
                    logger.info("Bot task cancelled successfully")
                except Exception as e:
                    logger.error(f"Error cancelling bot task: {e}")
            
            # Cleanup bot service
            if self.bot_service and self.bot_service.application:
                try:
                    await self.bot_service.application.updater.stop()
                    await self.bot_service.application.stop()
                    await self.bot_service.application.shutdown()
                    logger.info("Bot application shutdown complete")
                except Exception as e:
                    logger.error(f"Error shutting down bot application: {e}")
            
            # Reset state
            self.bot_service = None
            self.bot_task = None
            self.started_at = None
            self.state = "stopped"
            
            logger.info("Bot manager stopped")
    
    async def reload(self, token: str, dm_policy: str = "pairing") -> bool:
        """
        Reload bot with new configuration.
        
        This stops the current bot and starts a new one with the new configuration.
        
        Args:
            token: New bot token
            dm_policy: New DM policy
        
        Returns:
            True if reload successful, False otherwise
        
        Example:
            >>> success = await manager.reload("999999:...", "open")
            >>> if success:
            ...     print("Bot reloaded with new config")
        """
        async with self._lock:
            if self.state == "reloading":
                logger.warning("Bot already reloading, ignoring request")
                return False
            
            logger.info(f"Reloading bot with new configuration (policy: {dm_policy})")
            old_state = self.state
            self.state = "reloading"
            
            try:
                # Stop existing bot
                if self.bot_task and not self.bot_task.done():
                    logger.info("Stopping existing bot for reload...")
                    self.bot_task.cancel()
                    try:
                        await self.bot_task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error stopping bot for reload: {e}")
                
                # Clear stop event for new bot
                self._stop_event.clear()
                
                # Start new bot
                logger.info("Starting new bot instance...")
                self.config = {
                    "bot_token": token,
                    "dm_policy": dm_policy
                }
                
                from packages.messaging.telegram_bot import TelegramBotService
                self.bot_service = TelegramBotService()
                
                # Start bot in background task
                self.bot_task = asyncio.create_task(
                    self._run_bot_loop(token, dm_policy),
                    name="telegram-bot-poll-reload"
                )
                
                logger.info("Bot reload complete")
                return True
                
            except Exception as e:
                self.state = old_state  # Restore old state on error
                self.error_message = str(e)
                logger.error(f"Failed to reload bot: {e}", exc_info=True)
                return False
    
    def update_dm_policy(self, dm_policy: str) -> None:
        """
        Update DM policy without restart.
        
        Note: This only updates the stored config. The running bot
        will pick up the change on its next message handling cycle.
        
        Args:
            dm_policy: New DM policy ("pairing", "allowlist", or "open")
        
        Example:
            >>> manager.update_dm_policy("open")
            >>> print(manager.config["dm_policy"])
            'open'
        """
        if dm_policy not in ("pairing", "allowlist", "open"):
            logger.error(f"Invalid DM policy: {dm_policy}")
            return
        
        old_policy = self.config.get("dm_policy", "pairing")
        self.config["dm_policy"] = dm_policy
        logger.info(f"Updated DM policy from '{old_policy}' to '{dm_policy}'")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current bot status.
        
        Returns:
            Dict with state, dm_policy, and optional fields:
            - started_at: ISO format timestamp (if running)
            - uptime_seconds: Seconds since start (if running)
            - error_message: Error details (if error state)
        
        Example:
            >>> status = manager.get_status()
            >>> print(status)
            {
                "state": "running",
                "dm_policy": "pairing",
                "started_at": "2026-03-29T10:00:00.000000",
                "uptime_seconds": 3600
            }
        """
        status: Dict[str, Any] = {
            "state": self.state,
            "dm_policy": self.config.get("dm_policy", "pairing"),
        }
        
        if self.state == "error" and self.error_message:
            status["error_message"] = self.error_message
        
        if self.state == "running" and self.started_at:
            status["started_at"] = self.started_at.isoformat()
            status["uptime_seconds"] = int(
                (datetime.now() - self.started_at).total_seconds()
            )
        
        return status
    
    def is_running(self) -> bool:
        """
        Check if bot is currently running.
        
        Returns:
            True if bot is running, False otherwise
        
        Example:
            >>> if manager.is_running():
            ...     print("Bot is online")
        """
        return self.state == "running"
    
    def get_uptime(self) -> Optional[int]:
        """
        Get bot uptime in seconds.
        
        Returns:
            Uptime in seconds, or None if not running
        
        Example:
            >>> uptime = manager.get_uptime()
            >>> if uptime:
            ...     print(f"Bot running for {uptime} seconds")
        """
        if self.state != "running" or not self.started_at:
            return None
        
        return int((datetime.now() - self.started_at).total_seconds())


# Global bot manager instance (singleton pattern)
_bot_manager: Optional[BotManager] = None


def get_bot_manager() -> BotManager:
    """
    Get or create the global bot manager.
    
    Returns:
        Global BotManager instance
    
    Usage:
        manager = get_bot_manager()
        status = manager.get_status()
    """
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManager()
    return _bot_manager


def reset_bot_manager() -> None:
    """
    Reset the global bot manager (for testing).
    
    This clears the singleton instance, allowing a new one to be created.
    Only use in test code!
    
    Usage:
        reset_bot_manager()
        # Now get_bot_manager() will create a new instance
    """
    global _bot_manager
    _bot_manager = None


# Convenience functions for common operations

async def start_telegram_bot(token: str, dm_policy: str = "pairing") -> bool:
    """
    Start Telegram bot (convenience function).
    
    Args:
        token: Telegram bot token
        dm_policy: DM policy ("pairing", "allowlist", or "open")
    
    Returns:
        True if started successfully, False otherwise
    
    Usage:
        success = await start_telegram_bot("123456:...", "pairing")
    """
    manager = get_bot_manager()
    return await manager.start(token, dm_policy)


async def stop_telegram_bot() -> None:
    """
    Stop Telegram bot (convenience function).
    
    Usage:
        await stop_telegram_bot()
    """
    manager = get_bot_manager()
    await manager.stop()


async def reload_telegram_bot(token: str, dm_policy: str = "pairing") -> bool:
    """
    Reload Telegram bot with new configuration (convenience function).
    
    Args:
        token: New bot token
        dm_policy: New DM policy
    
    Returns:
        True if reload successful, False otherwise
    
    Usage:
        success = await reload_telegram_bot("999999:...", "open")
    """
    manager = get_bot_manager()
    return await manager.reload(token, dm_policy)


def get_telegram_bot_status() -> Dict[str, Any]:
    """
    Get Telegram bot status (convenience function).
    
    Returns:
        Status dict with state, dm_policy, and optional fields
    
    Usage:
        status = get_telegram_bot_status()
        if status["state"] == "running":
            print(f"Bot running for {status['uptime_seconds']} seconds")
    """
    manager = get_bot_manager()
    return manager.get_status()


def is_telegram_bot_running() -> bool:
    """
    Check if Telegram bot is running (convenience function).
    
    Returns:
        True if bot is running, False otherwise
    
    Usage:
        if is_telegram_bot_running():
            print("Bot is online")
    """
    manager = get_bot_manager()
    return manager.is_running()
