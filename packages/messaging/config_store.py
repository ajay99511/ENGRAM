"""
Telegram Configuration Store

Persists bot configuration to ~/.personalassist/telegram_config.env
Uses atomic writes and token redaction for security.

Features:
- Atomic file writes (temp file + rename)
- Token format validation
- Token redaction in logs
- Backward compatible with environment variables
- Graceful fallback if config file doesn't exist

Usage:
    from packages.messaging.config_store import ConfigStore
    
    store = ConfigStore()
    
    # Save configuration
    store.save(token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", dm_policy="pairing")
    
    # Load configuration
    config = store.load()
    if config:
        print(f"Token: {config['bot_token'][:10]}...")
        print(f"Policy: {config['dm_policy']}")
    
    # Validate token format
    is_valid = store.validate_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
"""

import os
import re
import tempfile
import logging
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Telegram bot token pattern
# Format: {bot_id}:{token}
# - bot_id: 6-10 digits
# - token: 34-50 characters (letters, numbers, underscores, hyphens)
# Note: Actual Telegram tokens vary in length, so we use a flexible pattern
TELEGRAM_TOKEN_PATTERN = re.compile(r'^\d{6,10}:[A-Za-z0-9_-]{34,50}$')


class TelegramConfig(TypedDict):
    """Telegram bot configuration."""
    bot_token: str
    dm_policy: str  # "pairing" | "allowlist" | "open"


class ConfigStore:
    """
    Persistent configuration store for Telegram bot.
    
    Responsibilities:
    - Save/load bot configuration to file
    - Validate token format
    - Atomic writes to prevent corruption
    - Token redaction in logs
    - Backward compatibility with environment variables
    
    File Format:
        TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
        TELEGRAM_DM_POLICY=pairing
    
    Location:
        ~/.personalassist/telegram_config.env
    """
    
    def __init__(self):
        """Initialize configuration store."""
        self.config_dir = Path.home() / ".personalassist"
        self.config_file = self.config_dir / "telegram_config.env"
        self._config_cache: Optional[TelegramConfig] = None
    
    def validate_token(self, token: str) -> bool:
        """
        Validate Telegram bot token format.
        
        Args:
            token: Bot token to validate
            
        Returns:
            True if token is valid format, False otherwise
            
        Examples:
            >>> store = ConfigStore()
            >>> store.validate_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
            True
            >>> store.validate_token("invalid-token")
            False
            >>> store.validate_token("")
            True  # Empty is valid (no token configured)
        """
        if not token or not token.strip():
            return True  # Empty is valid (no token configured)
        
        token = token.strip()
        return bool(TELEGRAM_TOKEN_PATTERN.match(token))
    
    def save(self, bot_token: str, dm_policy: str = "pairing") -> None:
        """
        Atomically save configuration to file.
        
        Uses atomic write pattern (temp file + rename) to prevent
        corruption if the write is interrupted.
        
        Args:
            bot_token: Telegram bot token (can be empty to clear)
            dm_policy: DM policy ("pairing", "allowlist", or "open")
            
        Raises:
            ValueError: If token format is invalid or dm_policy is unknown
            
        Example:
            >>> store = ConfigStore()
            >>> store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        """
        # Validate inputs
        if not self.validate_token(bot_token):
            raise ValueError(
                f"Invalid bot token format. "
                f"Expected format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            )
        
        if dm_policy not in ("pairing", "allowlist", "open"):
            raise ValueError(
                f"Invalid DM policy: {dm_policy}. "
                f"Must be one of: pairing, allowlist, open"
            )
        
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Atomic write using temp file + rename
        fd: Optional[int] = None
        temp_path: Optional[str] = None
        
        try:
            # Create temp file in same directory (ensures same filesystem for atomic rename)
            fd, temp_path = tempfile.mkstemp(
                dir=self.config_dir,
                prefix=".telegram_config_",
                suffix=".env",
            )
            
            # Write configuration
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                if bot_token and bot_token.strip():
                    f.write(f"TELEGRAM_BOT_TOKEN={bot_token.strip()}\n")
                f.write(f"TELEGRAM_DM_POLICY={dm_policy}\n")
            
            # Atomic rename (works on Windows too)
            os.replace(temp_path, self.config_file)
            
            # Clear cache to force reload on next access
            self._config_cache = None
            
            # Log success (with redacted token)
            token_display = self._redact_token(bot_token)
            logger.info(f"Saved Telegram configuration (token: {token_display}, policy: {dm_policy})")
            
        except Exception as e:
            # Clean up temp file on error
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            
            logger.error(f"Failed to save Telegram configuration: {e}")
            raise RuntimeError(f"Failed to save Telegram config: {e}")
    
    def load(self) -> Optional[TelegramConfig]:
        """
        Load configuration from file.
        
        Falls back to environment variables if config file doesn't exist.
        Returns None if neither file nor env vars are configured.
        
        Returns:
            TelegramConfig dict with bot_token and dm_policy, or None
            
        Example:
            >>> store = ConfigStore()
            >>> config = store.load()
            >>> if config:
            ...     print(f"Token: {config['bot_token'][:10]}...")
            ...     print(f"Policy: {config['dm_policy']}")
        """
        # Return cached config if available
        if self._config_cache is not None:
            return self._config_cache
        
        config: TelegramConfig = {
            "bot_token": "",
            "dm_policy": "pairing"
        }
        
        # Try to load from file first
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == "TELEGRAM_BOT_TOKEN":
                                config["bot_token"] = value
                            elif key == "TELEGRAM_DM_POLICY":
                                if value in ("pairing", "allowlist", "open"):
                                    config["dm_policy"] = value
                                else:
                                    logger.warning(
                                        f"Invalid DM_POLICY in config file: {value}. "
                                        f"Using default: pairing"
                                    )
                
                logger.info("Loaded Telegram configuration from file")
                
            except Exception as e:
                logger.error(f"Failed to load Telegram config from file: {e}")
                # Continue to env var fallback
        
        # Fallback to environment variables if no token in file
        if not config["bot_token"]:
            import os
            env_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            env_policy = os.getenv("TELEGRAM_DM_POLICY", "pairing")
            
            if env_token:
                config["bot_token"] = env_token
                config["dm_policy"] = env_policy if env_policy in ("pairing", "allowlist", "open") else "pairing"
                logger.info("Loaded Telegram configuration from environment variables")
        
        # Cache the config
        self._config_cache = config
        
        # Return None if no token configured
        if not config["bot_token"]:
            logger.debug("No Telegram configuration found")
            return None
        
        return config
    
    def get_bot_token(self) -> Optional[str]:
        """
        Get bot token from configuration.
        
        Returns:
            Bot token string or None if not configured
        """
        config = self.load()
        return config["bot_token"] if config else None
    
    def get_dm_policy(self) -> str:
        """
        Get DM policy from configuration.
        
        Returns:
            DM policy ("pairing", "allowlist", or "open")
        """
        config = self.load()
        return config["dm_policy"] if config else "pairing"
    
    def has_config(self) -> bool:
        """
        Check if configuration exists (file or env var).
        
        Returns:
            True if configuration exists, False otherwise
        """
        return self.get_bot_token() is not None
    
    def clear(self) -> None:
        """
        Clear configuration (delete file and cache).
        
        This will force the bot to use environment variables on next load.
        """
        if self.config_file.exists():
            try:
                self.config_file.unlink()
                logger.info("Cleared Telegram configuration file")
            except Exception as e:
                logger.error(f"Failed to clear Telegram config file: {e}")
                raise RuntimeError(f"Failed to clear Telegram config: {e}")
        
        # Clear cache
        self._config_cache = None
    
    def get_config_display(self) -> Dict[str, Any]:
        """
        Get configuration for display (with redacted token).
        
        Returns:
            Dict with bot_token_set (bool), dm_policy (str), token_display (str)
            
        Example:
            {
                "bot_token_set": True,
                "dm_policy": "pairing",
                "token_display": "123...w11"
            }
        """
        config = self.load()
        
        if not config or not config["bot_token"]:
            return {
                "bot_token_set": False,
                "dm_policy": "pairing",
                "token_display": "(not configured)",
            }
        
        return {
            "bot_token_set": True,
            "dm_policy": config["dm_policy"],
            "token_display": self._redact_token(config["bot_token"]),
        }
    
    def _redact_token(self, token: str) -> str:
        """
        Redact bot token for safe display/logging.
        
        Shows first 3 and last 3 characters, masks the rest.
        
        Args:
            token: Bot token to redact
            
        Returns:
            Redacted token string
        """
        if not token or len(token) < 10:
            return "***"
        
        return f"{token[:3]}...{token[-3:]}"
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        config = self.load()
        if config:
            token_display = self._redact_token(config["bot_token"])
            return f"ConfigStore(token={token_display}, policy={config['dm_policy']})"
        return "ConfigStore(not configured)"


# Global config store instance (singleton pattern)
_config_store: Optional[ConfigStore] = None


def get_config_store() -> ConfigStore:
    """
    Get or create the global configuration store.
    
    Returns:
        Global ConfigStore instance
        
    Usage:
        store = get_config_store()
        config = store.load()
    """
    global _config_store
    if _config_store is None:
        _config_store = ConfigStore()
    return _config_store


# Convenience functions for common operations

def save_telegram_config(bot_token: str, dm_policy: str = "pairing") -> None:
    """
    Save Telegram configuration (convenience function).
    
    Args:
        bot_token: Telegram bot token
        dm_policy: DM policy ("pairing", "allowlist", or "open")
        
    Usage:
        save_telegram_config("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
    """
    store = get_config_store()
    store.save(bot_token, dm_policy)


def load_telegram_config() -> Optional[TelegramConfig]:
    """
    Load Telegram configuration (convenience function).
    
    Returns:
        TelegramConfig dict or None if not configured
        
    Usage:
        config = load_telegram_config()
        if config:
            print(f"Token: {config['bot_token'][:10]}...")
    """
    store = get_config_store()
    return store.load()


def get_telegram_token() -> Optional[str]:
    """
    Get Telegram bot token (convenience function).
    
    Returns:
        Bot token string or None if not configured
        
    Usage:
        token = get_telegram_token()
        if token:
            # Use token
    """
    store = get_config_store()
    return store.get_bot_token()


def get_telegram_dm_policy() -> str:
    """
    Get Telegram DM policy (convenience function).
    
    Returns:
        DM policy ("pairing", "allowlist", or "open")
        
    Usage:
        policy = get_telegram_dm_policy()
    """
    store = get_config_store()
    return store.get_dm_policy()
