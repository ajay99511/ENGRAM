"""
Messaging Package

Provides messaging integrations for PersonalAssist.
Currently supports:
- Telegram (python-telegram-bot)

Future:
- Discord
- Slack
- WhatsApp
"""

from packages.messaging.telegram_bot import TelegramBotService, get_auth_store
from packages.messaging.telegram_webhook import router as telegram_webhook_router

__all__ = [
    "TelegramBotService",
    "get_auth_store",
    "telegram_webhook_router",
]
