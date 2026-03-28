"""
Telegram Webhook Router

Provides webhook endpoint for Telegram bot updates.
Alternative to polling for production deployments.

Usage:
    Include router in FastAPI app:
    from packages.messaging.telegram_webhook import router
    app.include_router(router)
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint for bot updates.
    
    Telegram will POST updates to this endpoint.
    
    Returns:
        JSON response
    """
    try:
        from telegram import Update
        from packages.messaging.telegram_bot import TelegramBotService
        
        # Get bot instance
        bot_service = TelegramBotService()
        
        if not bot_service.application:
            raise HTTPException(status_code=503, detail="Bot not initialized")
        
        # Parse update
        data = await request.json()
        update = Update.de_json(data, bot_service.application.bot)
        
        # Process update
        await bot_service.application.process_update(update)
        
        return JSONResponse(content={"status": "ok"})
    
    except Exception as exc:
        logger.error(f"Telegram webhook error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/webhook")
async def telegram_webhook_info():
    """Get webhook information."""
    from packages.messaging.telegram_bot import TELEGRAM_BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        return {
            "enabled": False,
            "reason": "TELEGRAM_BOT_TOKEN not set",
        }
    
    return {
        "enabled": True,
        "webhook_url": "/telegram/webhook",
        "mode": "webhook",
    }
