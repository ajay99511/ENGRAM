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

# Lazy imports to avoid requiring telegram package for all operations
def __getattr__(name: str):
    if name == "TelegramBotService":
        from packages.messaging.telegram_bot import TelegramBotService
        return TelegramBotService
    elif name == "get_auth_store":
        from packages.messaging.telegram_bot import get_auth_store
        return get_auth_store
    elif name == "telegram_webhook_router":
        from packages.messaging.telegram_webhook import router as telegram_webhook_router
        return telegram_webhook_router
    elif name == "config_store":
        from packages.messaging import config_store
        return config_store
    elif name == "ConfigStore":
        from packages.messaging.config_store import ConfigStore
        return ConfigStore
    elif name == "save_telegram_config":
        from packages.messaging.config_store import save_telegram_config
        return save_telegram_config
    elif name == "load_telegram_config":
        from packages.messaging.config_store import load_telegram_config
        return load_telegram_config
    elif name == "get_telegram_token":
        from packages.messaging.config_store import get_telegram_token
        return get_telegram_token
    elif name == "get_telegram_dm_policy":
        from packages.messaging.config_store import get_telegram_dm_policy
        return get_telegram_dm_policy
    elif name == "bot_manager":
        from packages.messaging import bot_manager
        return bot_manager
    elif name == "BotManager":
        from packages.messaging.bot_manager import BotManager
        return BotManager
    elif name == "get_bot_manager":
        from packages.messaging.bot_manager import get_bot_manager
        return get_bot_manager
    elif name == "start_telegram_bot":
        from packages.messaging.bot_manager import start_telegram_bot
        return start_telegram_bot
    elif name == "stop_telegram_bot":
        from packages.messaging.bot_manager import stop_telegram_bot
        return stop_telegram_bot
    elif name == "reload_telegram_bot":
        from packages.messaging.bot_manager import reload_telegram_bot
        return reload_telegram_bot
    elif name == "get_telegram_bot_status":
        from packages.messaging.bot_manager import get_telegram_bot_status
        return get_telegram_bot_status
    elif name == "is_telegram_bot_running":
        from packages.messaging.bot_manager import is_telegram_bot_running
        return is_telegram_bot_running
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Telegram Bot Service
    "TelegramBotService",
    "get_auth_store",
    "telegram_webhook_router",
    
    # Configuration Store
    "config_store",
    "ConfigStore",
    "save_telegram_config",
    "load_telegram_config",
    "get_telegram_token",
    "get_telegram_dm_policy",
    
    # Bot Manager
    "bot_manager",
    "BotManager",
    "get_bot_manager",
    "start_telegram_bot",
    "stop_telegram_bot",
    "reload_telegram_bot",
    "get_telegram_bot_status",
    "is_telegram_bot_running",
]
