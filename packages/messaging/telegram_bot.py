"""
Telegram Bot Service

Provides Telegram messaging integration for PersonalAssist.
Features:
- Message handling (text, files, voice)
- User authentication (Telegram ID → user_id mapping)
- DM policy enforcement (pairing/allowlist/open)
- Rate limiting
- Chunked responses for long messages

Usage:
    python -m packages.messaging.telegram_bot
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from packages.shared.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL = getattr(settings, "api_host", "127.0.0.1")
API_PORT = getattr(settings, "api_port", 8000)

# Rate limiting
RATE_LIMIT_MESSAGES = 10  # Max messages per window
RATE_LIMIT_WINDOW = timedelta(minutes=1)  # Window size

# DM Policy
DM_POLICY = os.getenv("TELEGRAM_DM_POLICY", "pairing")  # pairing | allowlist | open

# ─────────────────────────────────────────────────────────────────────
# User Authentication Store
# ─────────────────────────────────────────────────────────────────────

class UserAuthStore:
    """Manages Telegram ID to user_id mapping."""
    
    def __init__(self):
        self.auth_file = Path.home() / ".personalassist" / "telegram_auth.json"
        self.auth_data: dict[str, dict[str, Any]] = {}
        self.load()
    
    def load(self) -> None:
        """Load auth data from file."""
        if self.auth_file.exists():
            import json
            try:
                with open(self.auth_file, 'r', encoding='utf-8') as f:
                    self.auth_data = json.load(f)
                logger.info(f"Loaded {len(self.auth_data)} Telegram auth entries")
            except Exception as exc:
                logger.error(f"Failed to load auth file: {exc}")
                self.auth_data = {}
    
    def save(self) -> None:
        """Save auth data to file."""
        import json
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.auth_file, 'w', encoding='utf-8') as f:
                json.dump(self.auth_data, f, indent=2)
            logger.debug("Saved Telegram auth data")
        except Exception as exc:
            logger.error(f"Failed to save auth file: {exc}")
    
    def get_user_id(self, telegram_id: str) -> str | None:
        """Get user_id for a Telegram ID."""
        if telegram_id in self.auth_data:
            entry = self.auth_data[telegram_id]
            if entry.get("approved", False):
                return entry.get("user_id", "default")
        return None
    
    def add_user(self, telegram_id: str, user_id: str = "default") -> None:
        """Add a new Telegram user."""
        self.auth_data[telegram_id] = {
            "telegram_id": telegram_id,
            "user_id": user_id,
            "approved": DM_POLICY == "open",  # Auto-approve if open policy
            "created_at": datetime.now().isoformat(),
            "last_message_at": None,
        }
        self.save()
        logger.info(f"Added Telegram user: {telegram_id} (approved={self.auth_data[telegram_id]['approved']})")
    
    def approve_user(self, telegram_id: str) -> bool:
        """Approve a pending Telegram user."""
        if telegram_id in self.auth_data:
            self.auth_data[telegram_id]["approved"] = True
            self.save()
            logger.info(f"Approved Telegram user: {telegram_id}")
            return True
        return False
    
    def is_approved(self, telegram_id: str) -> bool:
        """Check if a Telegram user is approved."""
        if telegram_id not in self.auth_data:
            return False
        return self.auth_data[telegram_id].get("approved", False)
    
    def list_users(self) -> list[dict[str, Any]]:
        """List all Telegram users."""
        return list(self.auth_data.values())


# Global auth store instance
_auth_store: UserAuthStore | None = None


def get_auth_store() -> UserAuthStore:
    """Get or create the global auth store."""
    global _auth_store
    if _auth_store is None:
        _auth_store = UserAuthStore()
    return _auth_store


# ─────────────────────────────────────────────────────────────────────
# Rate Limiter
# ─────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Simple rate limiter for Telegram messages."""
    
    def __init__(self, max_messages: int = 10, window: timedelta = timedelta(minutes=1)):
        self.max_messages = max_messages
        self.window = window
        self.message_times: dict[str, list[datetime]] = {}
    
    def is_rate_limited(self, user_id: str) -> bool:
        """Check if user is rate limited."""
        now = datetime.now()
        
        if user_id not in self.message_times:
            self.message_times[user_id] = []
        
        # Remove old messages outside window
        cutoff = now - self.window
        self.message_times[user_id] = [
            t for t in self.message_times[user_id] if t > cutoff
        ]
        
        # Check if over limit
        if len(self.message_times[user_id]) >= self.max_messages:
            return True
        
        # Record this message
        self.message_times[user_id].append(now)
        return False


# Global rate limiter
_rate_limiter = RateLimiter(
    max_messages=RATE_LIMIT_MESSAGES,
    window=RATE_LIMIT_WINDOW,
)


# ─────────────────────────────────────────────────────────────────────
# Telegram Bot Service
# ─────────────────────────────────────────────────────────────────────

class TelegramBotService:
    """Telegram bot service for PersonalAssist."""
    
    def __init__(self):
        self.application: Application | None = None
        self.auth_store = get_auth_store()
        self.api_base = f"http://{API_BASE_URL}:{API_PORT}"
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        telegram_id = str(update.effective_user.id)
        
        # Add user if not exists
        if not self.auth_store.is_approved(telegram_id):
            self.auth_store.add_user(telegram_id)
        
        if self.auth_store.is_approved(telegram_id):
            await update.message.reply_text(
                "🤖 **Welcome to PersonalAssist!**\n\n"
                "I'm your AI assistant. You can ask me anything!\n\n"
                "Commands:\n"
                "/start - Show this message\n"
                "/help - Show help\n"
                "/status - Show your status\n"
                "/new - Start a new conversation\n"
            )
        else:
            await update.message.reply_text(
                "🔐 **Approval Required**\n\n"
                "Your account is pending approval. "
                "Please contact the administrator with this code:\n\n"
                f"`{telegram_id}`\n\n"
                "Once approved, you can start chatting!"
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "📚 **PersonalAssist Help**\n\n"
            "**Basic Usage:**\n"
            "Just send me a message and I'll respond!\n\n"
            "**Features:**\n"
            "• Smart conversations with memory\n"
            "• Document and code analysis\n"
            "• Multi-turn conversations\n\n"
            "**Commands:**\n"
            "/start - Welcome message\n"
            "/help - This help\n"
            "/status - Your account status\n"
            "/new - Start new conversation\n\n"
            "**Tips:**\n"
            "• Be specific in your questions\n"
            "• Reference previous messages\n"
            "• Use /new to clear context\n"
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        telegram_id = str(update.effective_user.id)
        user_info = self.auth_store.auth_data.get(telegram_id, {})
        
        status_text = (
            "📊 **Your Status**\n\n"
            f"Telegram ID: `{telegram_id}`\n"
            f"User ID: `{user_info.get('user_id', 'unknown')}`\n"
            f"Approved: {'✅ Yes' if user_info.get('approved') else '❌ No'}\n"
            f"Created: {user_info.get('created_at', 'unknown')}\n"
            f"Last Message: {user_info.get('last_message_at', 'Never')}\n"
        )
        
        await update.message.reply_text(status_text)
    
    async def new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /new command."""
        await update.message.reply_text(
            "🆕 **New Conversation Started**\n\n"
            "Previous context has been cleared. "
            "What would you like to discuss?"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return
        
        telegram_id = str(update.effective_user.id)
        user_message = update.message.text
        
        logger.info(f"Received message from {telegram_id}: {user_message[:100]}...")
        
        # Check authentication
        if not self.auth_store.is_approved(telegram_id):
            await update.message.reply_text(
                "🔐 Your account is pending approval. "
                f"Please contact the administrator with code: `{telegram_id}`"
            )
            return
        
        # Check rate limit
        if _rate_limiter.is_rate_limited(telegram_id):
            await update.message.reply_text(
                "⏳ Rate limit exceeded. Please wait a moment before sending more messages."
            )
            return
        
        # Update last message time
        if telegram_id in self.auth_store.auth_data:
            self.auth_store.auth_data[telegram_id]["last_message_at"] = datetime.now().isoformat()
            self.auth_store.save()
        
        # Get user_id
        user_id = self.auth_store.get_user_id(telegram_id) or "default"
        
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        try:
            # Call PersonalAssist API
            response = await self.call_agent_api(user_id, user_message)
            
            # Send response (chunk if long)
            await self.send_chunked_response(update, response)
        
        except Exception as exc:
            logger.error(f"Failed to process message: {exc}")
            await update.message.reply_text(
                "⚠️ Sorry, I encountered an error processing your message. "
                "Please try again in a moment."
            )
    
    async def call_agent_api(self, user_id: str, message: str) -> str:
        """
        Call PersonalAssist API to get agent response.
        
        Args:
            user_id: User identifier
            message: User message
        
        Returns:
            Agent response text
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base}/chat/smart",
                    json={
                        "message": message,
                        "model": "local",
                        "thread_id": None,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "I don't have a response for that.")
            
            except httpx.TimeoutException:
                logger.error("API timeout")
                return "⏱️ The request timed out. Please try again."
            
            except httpx.HTTPError as exc:
                logger.error(f"API error: {exc}")
                return f"⚠️ API error: {str(exc)[:200]}"
    
    async def send_chunked_response(self, update: Update, text: str) -> None:
        """
        Send long responses as multiple messages.
        
        Args:
            update: Telegram update
            text: Response text
        """
        max_length = 4096  # Telegram message limit
        
        if len(text) <= max_length:
            await update.message.reply_text(text)
            return
        
        # Split into chunks
        chunks = []
        while len(text) > max_length:
            # Find last newline or space within limit
            split_pos = text.rfind('\n', 0, max_length)
            if split_pos == -1:
                split_pos = text.rfind(' ', 0, max_length)
            if split_pos == -1:
                split_pos = max_length
            
            chunks.append(text[:split_pos].strip())
            text = text[split_pos:].strip()
        
        if text:
            chunks.append(text)
        
        # Send chunks with delay to avoid rate limiting
        for i, chunk in enumerate(chunks):
            if i > 0:
                await asyncio.sleep(0.5)
            await update.message.reply_text(f"(Part {i+1}/{len(chunks)})\n\n{chunk}")
    
    async def run(self) -> None:
        """Start the Telegram bot."""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set. Telegram bot disabled.")
            return
        
        # Build application
        self.application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("new", self.new_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Start bot
        logger.info("Starting Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Telegram bot is running!")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Telegram bot stopping...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


# ─────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────

async def main():
    """Main entry point."""
    bot = TelegramBotService()
    await bot.run()


if __name__ == "__main__":
    print("PersonalAssist Telegram Bot")
    print("===========================")
    print()
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        print()
        print("To get a bot token:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot and follow the instructions")
        print("3. Copy the token and set TELEGRAM_BOT_TOKEN environment variable")
        print()
        print("Example:")
        print("  export TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    else:
        print("Starting Telegram bot...")
        print("Press Ctrl+C to stop")
        print()
        
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nTelegram bot stopped")
