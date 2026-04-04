"""
Telegram Router

FastAPI router for Telegram bot management endpoints.
Provides REST API for bot configuration, lifecycle management, and status.

Endpoints:
- GET /telegram/config - Get current configuration
- POST /telegram/config - Update configuration (persists to file)
- GET /telegram/status - Get bot runtime status
- POST /telegram/reload - Reload bot with new configuration
- POST /telegram/start - Start bot if stopped
- POST /telegram/stop - Stop bot if running
- GET /telegram/users - List all Telegram users
- GET /telegram/users/pending - List pending approval users
- POST /telegram/users/{telegram_id}/approve - Approve user
- POST /telegram/test - Send test message

Usage:
    from apps.api.telegram_router import router
    
    app.include_router(router)
"""

import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from packages.messaging.config_store import ConfigStore, get_config_store
from packages.messaging.bot_manager import get_bot_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


# ── Request/Response Models ─────────────────────────────────────────


class TelegramConfigInput(BaseModel):
    """Input model for updating Telegram configuration."""
    bot_token: str = Field(
        default="",
        description="Telegram bot token (empty to keep existing)",
        examples=["123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"]
    )
    dm_policy: str = Field(
        default="pairing",
        description="DM policy: pairing, allowlist, or open",
        examples=["pairing"]
    )
    
    @field_validator("dm_policy")
    @classmethod
    def validate_dm_policy(cls, v: str) -> str:
        if v not in ("pairing", "allowlist", "open"):
            raise ValueError("DM policy must be one of: pairing, allowlist, open")
        return v
    
    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        if v and v.strip():
            # Basic format validation
            import re
            pattern = re.compile(r'^\d{6,10}:[A-Za-z0-9_-]{34,50}$')
            if not pattern.match(v.strip()):
                raise ValueError(
                    "Invalid bot token format. "
                    "Expected: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                )
        return v.strip() if v else ""


class TelegramConfigResponse(BaseModel):
    """Response model for Telegram configuration."""
    bot_token_set: bool = Field(description="Whether a bot token is configured")
    dm_policy: str = Field(description="Current DM policy")
    token_display: str = Field(description="Redacted token for display")


class TelegramStatusResponse(BaseModel):
    """Response model for Telegram bot status."""
    state: str = Field(
        description="Bot state: stopped, starting, running, error, reloading, stopping",
        examples=["running"]
    )
    dm_policy: str = Field(description="Current DM policy")
    started_at: str | None = Field(
        default=None,
        description="ISO format timestamp when bot started (if running)",
        examples=["2026-03-29T10:00:00.000000"]
    )
    uptime_seconds: int | None = Field(
        default=None,
        description="Seconds since bot started (if running)",
        examples=[3600]
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if in error state",
        examples=["Connection timeout"]
    )


class TelegramActionResponse(BaseModel):
    """Response model for Telegram bot actions."""
    status: str = Field(description="Action status")
    message: str = Field(description="Human-readable message")
    dm_policy: str | None = Field(default=None, description="Current DM policy")


# ── Configuration Endpoints ──────────────────────────────────────────


@router.get("/config", response_model=TelegramConfigResponse)
async def get_telegram_config():
    """
    Get Telegram configuration.
    
    Returns configuration from file with redacted token for security.
    
    **Response Fields:**
    - `bot_token_set`: Whether a token is configured
    - `dm_policy`: Current DM policy (pairing/allowlist/open)
    - `token_display`: Redacted token (e.g., "123...w11")
    
    **Example Response:**
    ```json
    {
        "bot_token_set": true,
        "dm_policy": "pairing",
        "token_display": "123...w11"
    }
    ```
    """
    try:
        store = get_config_store()
        config = store.get_config_display()
        
        return TelegramConfigResponse(
            bot_token_set=config["bot_token_set"],
            dm_policy=config["dm_policy"],
            token_display=config["token_display"],
        )
        
    except Exception as e:
        logger.error(f"Get Telegram config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=TelegramActionResponse)
async def update_telegram_config(config: TelegramConfigInput):
    """
    Update Telegram configuration with persistence.
    
    **Request Fields:**
    - `bot_token`: New bot token (empty to keep existing)
    - `dm_policy`: New DM policy (pairing/allowlist/open)
    
    **Behavior:**
    1. Validates token format
    2. Persists configuration to file
    3. Reloads bot if token changed
    4. Updates DM policy immediately
    
    **Response Status:**
    - `reloading`: Bot is reloading with new token
    - `saved`: Configuration saved (DM policy only)
    - `unchanged`: No changes made
    
    **Example Request:**
    ```json
    {
        "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        "dm_policy": "pairing"
    }
    ```
    """
    store = get_config_store()
    manager = get_bot_manager()
    
    try:
        # Get current config to handle empty token
        current_config = store.load()
        
        # Use existing token if empty provided
        bot_token = config.bot_token
        if not bot_token and current_config:
            bot_token = current_config.get("bot_token", "")
        
        # If still no token, return error
        if not bot_token:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "no_token",
                    "message": "Bot token is required. Provide a token or keep existing."
                }
            )
        
        # Validate token format
        if not store.validate_token(bot_token):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "invalid_token_format",
                    "message": "Invalid bot token format. Expected: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                }
            )
        
        # Save configuration to file
        store.save(bot_token, config.dm_policy)
        logger.info("Saved Telegram configuration to file")
        
        # Check if token changed
        token_changed = current_config is None or current_config.get("bot_token") != bot_token
        
        if token_changed:
            # Full reload with new token
            logger.info("Token changed, triggering bot reload")
            
            # Start reload in background (don't wait)
            asyncio.create_task(
                manager.reload(bot_token, config.dm_policy),
                name="telegram-reload-task"
            )
            
            return TelegramActionResponse(
                status="reloading",
                message="Bot is reloading with new token. Check /telegram/status for updates.",
                dm_policy=config.dm_policy,
            )
        else:
            # DM policy only - no restart needed
            logger.info("DM policy only update, no reload needed")
            manager.update_dm_policy(config.dm_policy)
            
            return TelegramActionResponse(
                status="saved",
                message="Configuration saved successfully",
                dm_policy=config.dm_policy,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update Telegram config error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "save_failed",
                "message": f"Failed to save configuration: {e}"
            }
        )


# ── Status Endpoints ────────────────────────────────────────────────


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status():
    """
    Get current Telegram bot runtime status.
    
    **Response Fields:**
    - `state`: Bot state (stopped/starting/running/error/reloading/stopping)
    - `dm_policy`: Current DM policy
    - `started_at`: ISO timestamp when bot started (if running)
    - `uptime_seconds`: Seconds since bot started (if running)
    - `error_message`: Error details (if in error state)
    
    **Example Response (Running):**
    ```json
    {
        "state": "running",
        "dm_policy": "pairing",
        "started_at": "2026-03-29T10:00:00.000000",
        "uptime_seconds": 3600
    }
    ```
    
    **Example Response (Error):**
    ```json
    {
        "state": "error",
        "dm_policy": "pairing",
        "error_message": "Connection timeout"
    }
    ```
    """
    try:
        manager = get_bot_manager()
        status = manager.get_status()
        
        return TelegramStatusResponse(
            state=status["state"],
            dm_policy=status["dm_policy"],
            started_at=status.get("started_at"),
            uptime_seconds=status.get("uptime_seconds"),
            error_message=status.get("error_message"),
        )
        
    except Exception as e:
        logger.error(f"Get Telegram status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Lifecycle Control Endpoints ─────────────────────────────────────


@router.post("/reload", response_model=TelegramActionResponse)
async def reload_telegram_bot_endpoint(config: TelegramConfigInput):
    """
    Reload Telegram bot with new configuration.
    
    **Request Fields:**
    - `bot_token`: New bot token (required)
    - `dm_policy`: New DM policy (required)
    
    **Behavior:**
    1. Stops current bot (if running)
    2. Starts new bot with new configuration
    3. Returns immediately (reload happens in background)
    
    **Example Request:**
    ```json
    {
        "bot_token": "999999:XYZ-ABC123def456GHI789jkl012MNO",
        "dm_policy": "open"
    }
    ```
    """
    if not config.bot_token:
        raise HTTPException(
            status_code=400,
            detail={"code": "no_token", "message": "Bot token is required for reload"}
        )
    
    manager = get_bot_manager()
    
    try:
        # Start reload in background
        asyncio.create_task(
            manager.reload(config.bot_token, config.dm_policy),
            name="telegram-reload-task-explicit"
        )
        
        return TelegramActionResponse(
            status="reloading",
            message="Bot reload initiated. Check /telegram/status for updates.",
            dm_policy=config.dm_policy,
        )
        
    except Exception as e:
        logger.error(f"Reload Telegram bot error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=TelegramActionResponse)
async def start_telegram_bot_endpoint(config: TelegramConfigInput):
    """
    Start Telegram bot if stopped.
    
    **Request Fields:**
    - `bot_token`: Bot token (required)
    - `dm_policy`: DM policy (optional, default: pairing)
    
    **Behavior:**
    1. Validates token
    2. Starts bot if stopped
    3. Returns immediately (start happens in background)
    
    **Note:** Use /telegram/config to save configuration permanently.
    """
    if not config.bot_token:
        raise HTTPException(
            status_code=400,
            detail={"code": "no_token", "message": "Bot token is required to start"}
        )
    
    manager = get_bot_manager()
    
    if manager.is_running():
        return TelegramActionResponse(
            status="already_running",
            message="Bot is already running",
            dm_policy=manager.config.get("dm_policy"),
        )
    
    try:
        # Start in background
        asyncio.create_task(
            manager.start(config.bot_token, config.dm_policy),
            name="telegram-start-task"
        )
        
        return TelegramActionResponse(
            status="starting",
            message="Bot is starting. Check /telegram/status for updates.",
            dm_policy=config.dm_policy,
        )
        
    except Exception as e:
        logger.error(f"Start Telegram bot error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=TelegramActionResponse)
async def stop_telegram_bot_endpoint():
    """
    Stop Telegram bot if running.
    
    **Behavior:**
    1. Stops bot gracefully
    2. Waits for current message processing to complete
    3. Returns when stopped
    
    **Note:** Bot will remain stopped until manually started or API restarts.
    """
    manager = get_bot_manager()
    
    if not manager.is_running():
        return TelegramActionResponse(
            status="already_stopped",
            message="Bot is already stopped",
        )
    
    try:
        # Stop bot (wait for completion)
        await manager.stop()
        
        return TelegramActionResponse(
            status="stopped",
            message="Bot stopped successfully",
        )
        
    except Exception as e:
        logger.error(f"Stop Telegram bot error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── User Management Endpoints ───────────────────────────────────────


@router.get("/users")
async def list_telegram_users():
    """
    List all Telegram users.
    
    **Response Fields:**
    - `users`: List of user objects
    - `count`: Total number of users
    
    **User Object:**
    - `telegram_id`: Telegram user ID
    - `user_id`: Internal user ID
    - `approved`: Whether user is approved
    - `created_at`: When user was added
    - `last_message_at`: Last message timestamp
    """
    try:
        from packages.messaging.telegram_bot import get_auth_store
        
        auth_store = get_auth_store()
        users = auth_store.list_users()
        
        return {
            "users": users,
            "count": len(users),
        }
        
    except Exception as e:
        logger.error(f"List Telegram users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/pending")
async def list_pending_approvals():
    """
    List pending approval requests.
    
    **Response Fields:**
    - `pending_users`: List of pending user objects
    - `count`: Number of pending users
    
    **Use Case:**
    Use this endpoint when DM policy is "pairing" to see users
    waiting for approval.
    """
    try:
        from packages.messaging.telegram_bot import get_auth_store
        
        auth_store = get_auth_store()
        users = auth_store.list_users()
        pending = [u for u in users if not u.get("approved", False)]
        
        return {
            "pending_users": pending,
            "count": len(pending),
        }
        
    except Exception as e:
        logger.error(f"List pending approvals error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{telegram_id}/approve")
async def approve_telegram_user(telegram_id: str):
    """
    Approve Telegram user.
    
    **Path Parameters:**
    - `telegram_id`: Telegram user ID to approve
    
    **Response Fields:**
    - `status`: "approved"
    - `telegram_id`: The approved user ID
    
    **Use Case:**
    Use this endpoint to approve users when DM policy is "pairing".
    """
    try:
        from packages.messaging.telegram_bot import get_auth_store
        
        auth_store = get_auth_store()
        success = auth_store.approve_user(telegram_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "User not found"}
            )
        
        return {
            "status": "approved",
            "telegram_id": telegram_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve Telegram user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Testing Endpoints ───────────────────────────────────────────────


@router.post("/test", response_model=TelegramActionResponse)
async def send_telegram_test_message():
    """
    Send test message to connected Telegram users.
    
    **Behavior:**
    1. Checks if bot is running
    2. Sends test message to all approved users
    3. Returns success/failure status
    
    **Use Case:**
    Use this endpoint to verify bot connectivity after configuration.
    """
    manager = get_bot_manager()
    
    if not manager.is_running():
        raise HTTPException(
            status_code=400,
            detail={
                "code": "bot_not_running",
                "message": "Bot is not running. Start bot first."
            }
        )
    
    try:
        # Get auth store and send message to all users
        from packages.messaging.telegram_bot import get_auth_store
        from telegram import Bot
        
        token = manager.config.get("bot_token", "")
        if not token:
            raise HTTPException(
                status_code=400,
                detail={"code": "no_token", "message": "No bot token configured"}
            )
        
        auth_store = get_auth_store()
        users = [u for u in auth_store.list_users() if u.get("approved", False)]
        
        if not users:
            return TelegramActionResponse(
                status="no_users",
                message="No approved users to send test message to",
            )
        
        # Send test message to each user
        bot = Bot(token=token)
        sent_count = 0
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text="🧪 **Test Message**\n\nThis is a test message from PersonalAssist. If you received this, the bot is working correctly!"
                )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send test message to {user['telegram_id']}: {e}")
        
        return TelegramActionResponse(
            status="sent",
            message=f"Test message sent to {sent_count} user(s)",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Send test message error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "send_failed",
                "message": f"Failed to send test message: {e}"
            }
        )
