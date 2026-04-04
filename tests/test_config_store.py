"""
Tests for Telegram Configuration Store

Tests cover:
- Token validation
- Atomic file writes
- Configuration persistence
- Token redaction
- Environment variable fallback
- Error handling
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from packages.messaging.config_store import (
    ConfigStore,
    TelegramConfig,
    get_config_store,
    save_telegram_config,
    load_telegram_config,
    get_telegram_token,
    get_telegram_dm_policy,
)


class TestTokenValidation:
    """Test bot token format validation."""
    
    def test_validate_valid_token(self):
        """Test valid token formats."""
        store = ConfigStore()
        
        # Standard format
        assert store.validate_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") is True
        
        # With underscores
        assert store.validate_token("987654:abc_def-ghi_jkl-mno_pqr-stu_vwx") is True
        
        # With hyphens
        assert store.validate_token("111111:ABC-DEF-GHI-JKL-MNO-PQR-STU-VWX-YZ") is True
    
    def test_validate_empty_token(self):
        """Test empty token is valid (no token configured)."""
        store = ConfigStore()
        assert store.validate_token("") is True
        assert store.validate_token(None) is True
        assert store.validate_token("   ") is True
    
    def test_validate_invalid_tokens(self):
        """Test invalid token formats."""
        store = ConfigStore()
        
        # Missing colon
        assert store.validate_token("123456ABC-DEF1234ghIkl-zyx57W2v1u123ew11") is False
        
        # Too short token part
        assert store.validate_token("123456:ABC") is False
        
        # Invalid characters
        assert store.validate_token("123456:ABC!DEF@GHI#JKL") is False
        
        # Missing bot_id
        assert store.validate_token(":ABC-DEF1234ghIkl-zyx57W2v1u123ew11") is False
        
        # Non-numeric bot_id
        assert store.validate_token("abcdef:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") is False
    
    def test_validate_token_with_whitespace(self):
        """Test token validation strips whitespace."""
        store = ConfigStore()
        token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert store.validate_token(f"  {token}  ") is True


class TestConfigStore:
    """Test configuration store functionality."""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / ".personalassist"
        config_dir.mkdir()
        return config_dir
    
    @pytest.fixture
    def store(self, temp_config_dir):
        """Create ConfigStore with temporary directory."""
        with patch.object(ConfigStore, '__init__', lambda x: None):
            store = ConfigStore()
            store.config_dir = temp_config_dir
            store.config_file = temp_config_dir / "telegram_config.env"
            store._config_cache = None
            return store
    
    def test_save_and_load_config(self, store):
        """Test saving and loading configuration."""
        # Save config
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        
        # Load config
        config = store.load()
        
        assert config is not None
        assert config["bot_token"] == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert config["dm_policy"] == "pairing"
    
    def test_save_config_open_policy(self, store):
        """Test saving with open DM policy."""
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "open")
        config = store.load()
        
        assert config["dm_policy"] == "open"
    
    def test_save_config_allowlist_policy(self, store):
        """Test saving with allowlist DM policy."""
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "allowlist")
        config = store.load()
        
        assert config["dm_policy"] == "allowlist"
    
    def test_save_invalid_token_raises_error(self, store):
        """Test saving invalid token raises ValueError."""
        with pytest.raises(ValueError, match="Invalid bot token format"):
            store.save("invalid-token", "pairing")
    
    def test_save_invalid_policy_raises_error(self, store):
        """Test saving invalid policy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid DM policy"):
            store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "invalid")
    
    def test_clear_config(self, store):
        """Test clearing configuration."""
        # Save config
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        assert store.has_config() is True
        
        # Clear config
        store.clear()
        assert store.has_config() is False
    
    def test_get_bot_token(self, store):
        """Test getting bot token."""
        # No token initially
        assert store.get_bot_token() is None
        
        # Save and get token
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        token = store.get_bot_token()
        
        assert token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    
    def test_get_dm_policy(self, store):
        """Test getting DM policy."""
        # Default policy
        assert store.get_dm_policy() == "pairing"
        
        # Save and get policy
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "open")
        assert store.get_dm_policy() == "open"
    
    def test_has_config(self, store):
        """Test checking if config exists."""
        # No config initially
        assert store.has_config() is False
        
        # Save config
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        assert store.has_config() is True
    
    def test_get_config_display(self, store):
        """Test getting config for display (with redacted token)."""
        # No config
        display = store.get_config_display()
        assert display["bot_token_set"] is False
        assert display["token_display"] == "(not configured)"
        
        # With config
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        display = store.get_config_display()
        
        assert display["bot_token_set"] is True
        assert display["token_display"] == "123...w11"
        assert display["dm_policy"] == "pairing"
    
    def test_config_file_format(self, store):
        """Test configuration file format."""
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        
        # Read raw file content
        content = store.config_file.read_text()
        
        assert "TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" in content
        assert "TELEGRAM_DM_POLICY=pairing" in content
    
    def test_load_nonexistent_file(self, store):
        """Test loading when config file doesn't exist."""
        config = store.load()
        
        # Should return None (no config)
        assert config is None
    
    def test_env_var_fallback(self, store):
        """Test fallback to environment variables."""
        # Remove config file
        if store.config_file.exists():
            store.config_file.unlink()
        
        # Set env vars
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "999999:XYZ-ABC123def456GHI789jkl012MNO",
            "TELEGRAM_DM_POLICY": "open"
        }):
            config = store.load()
            
            assert config is not None
            assert config["bot_token"] == "999999:XYZ-ABC123def456GHI789jkl012MNO"
            assert config["dm_policy"] == "open"
    
    def test_env_var_fallback_default_policy(self, store):
        """Test env var fallback with missing policy uses default."""
        if store.config_file.exists():
            store.config_file.unlink()
        
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "999999:XYZ-ABC123def456GHI789jkl012MNO"
        }, clear=False):
            # Remove policy if exists
            os.environ.pop("TELEGRAM_DM_POLICY", None)
            
            config = store.load()
            
            assert config is not None
            assert config["dm_policy"] == "pairing"  # Default
    
    def test_config_caching(self, store):
        """Test configuration is cached."""
        # Save config
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        
        # First load (reads from file)
        config1 = store.load()
        
        # Second load (should use cache)
        config2 = store.load()
        
        # Both should be same object (cached)
        assert config1 is config2
    
    def test_cache_cleared_on_save(self, store):
        """Test cache is cleared when saving."""
        # Save initial config
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        config1 = store.load()
        
        # Save new config
        store.save("999999:XYZ-ABC123def456GHI789jkl012MNO", "open")
        
        # Load should get new config (cache was cleared)
        config2 = store.load()
        
        assert config2["bot_token"] == "999999:XYZ-ABC123def456GHI789jkl012MNO"
        assert config2["dm_policy"] == "open"


class TestTokenRedaction:
    """Test token redaction for security."""
    
    def test_redact_short_token(self):
        """Test redacting short token."""
        store = ConfigStore()
        result = store._redact_token("12345")
        assert result == "***"
    
    def test_redact_normal_token(self):
        """Test redacting normal token."""
        store = ConfigStore()
        token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        result = store._redact_token(token)
        assert result == "123...w11"
    
    def test_redact_empty_token(self):
        """Test redacting empty token."""
        store = ConfigStore()
        result = store._redact_token("")
        assert result == "***"
    
    def test_redact_none_token(self):
        """Test redacting None token."""
        store = ConfigStore()
        result = store._redact_token(None)
        assert result == "***"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_save_telegram_config(self, tmp_path):
        """Test save_telegram_config convenience function."""
        with patch('packages.messaging.config_store._config_store', None):
            with patch.object(ConfigStore, '__init__', lambda x: None):
                store = ConfigStore()
                store.config_dir = tmp_path
                store.config_file = tmp_path / "telegram_config.env"
                store._config_cache = None
                
                with patch('packages.messaging.config_store.get_config_store', return_value=store):
                    save_telegram_config("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "open")
                    
                    config = store.load()
                    assert config["bot_token"] == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                    assert config["dm_policy"] == "open"
    
    def test_get_telegram_token(self):
        """Test get_telegram_token convenience function."""
        # Test with no config
        with patch('packages.messaging.config_store.get_config_store') as mock_store:
            mock_store.return_value.get_bot_token.return_value = None
            result = get_telegram_token()
            assert result is None
    
    def test_get_telegram_dm_policy(self):
        """Test get_telegram_dm_policy convenience function."""
        with patch('packages.messaging.config_store.get_config_store') as mock_store:
            mock_store.return_value.get_dm_policy.return_value = "open"
            result = get_telegram_dm_policy()
            assert result == "open"


class TestAtomicWrites:
    """Test atomic write behavior."""
    
    def test_atomic_write_success(self, tmp_path):
        """Test atomic write completes successfully."""
        store = ConfigStore()
        store.config_dir = tmp_path
        store.config_file = tmp_path / "telegram_config.env"
        store._config_cache = None
        
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        
        # File should exist
        assert store.config_file.exists()
        
        # No temp files should remain
        temp_files = list(tmp_path.glob(".telegram_config_*.env"))
        assert len(temp_files) == 0
    
    def test_atomic_write_cleanup_on_error(self, tmp_path):
        """Test temp file is cleaned up on error."""
        store = ConfigStore()
        store.config_dir = tmp_path
        store.config_file = tmp_path / "telegram_config.env"
        store._config_cache = None
        
        # Try to save invalid token (should fail)
        with pytest.raises(ValueError):
            store.save("invalid-token", "pairing")
        
        # No temp files should remain
        temp_files = list(tmp_path.glob(".telegram_config_*.env"))
        assert len(temp_files) == 0
        
        # Config file should not exist
        assert not store.config_file.exists()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_save_empty_token_clears(self, tmp_path):
        """Test saving empty token clears configuration."""
        store = ConfigStore()
        store.config_dir = tmp_path
        store.config_file = tmp_path / "telegram_config.env"
        store._config_cache = None
        
        # Save with token
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        
        # Save with empty token
        store.save("", "pairing")
        
        # Token should be cleared
        config = store.load()
        assert config is None or config["bot_token"] == ""
    
    def test_load_malformed_config_file(self, tmp_path):
        """Test loading malformed config file."""
        store = ConfigStore()
        store.config_dir = tmp_path
        store.config_file = tmp_path / "telegram_config.env"
        store._config_cache = None
        
        # Write malformed config
        store.config_file.write_text("this is not valid config\n")
        
        # Should not raise, should return None or use env fallback
        config = store.load()
        # Either None or falls back to env vars
    
    def test_load_config_with_comments(self, tmp_path):
        """Test loading config file with comments."""
        store = ConfigStore()
        store.config_dir = tmp_path
        store.config_file = tmp_path / "telegram_config.env"
        store._config_cache = None
        
        # Write config with comments
        content = """
# This is a comment
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
# Another comment
TELEGRAM_DM_POLICY=pairing
"""
        store.config_file.write_text(content)
        
        config = store.load()
        
        assert config is not None
        assert config["bot_token"] == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert config["dm_policy"] == "pairing"
    
    def test_multiple_stores_independent(self, tmp_path):
        """Test multiple store instances are independent."""
        store1 = ConfigStore()
        store1.config_dir = tmp_path / "store1"
        store1.config_file = store1.config_dir / "telegram_config.env"
        store1._config_cache = None
        store1.config_dir.mkdir(parents=True, exist_ok=True)
        
        store2 = ConfigStore()
        store2.config_dir = tmp_path / "store2"
        store2.config_file = store2.config_dir / "telegram_config.env"
        store2._config_cache = None
        store2.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Save different configs
        store1.save("111111:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        store2.save("222222:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "open")
        
        # Load and verify
        config1 = store1.load()
        config2 = store2.load()
        
        assert config1["bot_token"] == "111111:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert config1["dm_policy"] == "pairing"
        
        assert config2["bot_token"] == "222222:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert config2["dm_policy"] == "open"


class TestIntegration:
    """Integration tests with real file system."""
    
    def test_full_lifecycle(self, tmp_path):
        """Test complete lifecycle: save, load, update, clear."""
        store = ConfigStore()
        store.config_dir = tmp_path
        store.config_file = tmp_path / "telegram_config.env"
        store._config_cache = None
        
        # 1. Initial state: no config
        assert store.has_config() is False
        
        # 2. Save config
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
        assert store.has_config() is True
        
        # 3. Load config
        config = store.load()
        assert config is not None
        assert config["bot_token"] == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert config["dm_policy"] == "pairing"
        
        # 4. Update config
        store.save("999999:XYZ-ABC123def456GHI789jkl012MNO", "open")
        config = store.load()
        assert config["bot_token"] == "999999:XYZ-ABC123def456GHI789jkl012MNO"
        assert config["dm_policy"] == "open"
        
        # 5. Clear config
        store.clear()
        assert store.has_config() is False
        
        # 6. Verify file deleted
        assert not store.config_file.exists()
