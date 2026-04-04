#!/usr/bin/env python3
"""
ConfigStore Manual Test Script

Run this to verify ConfigStore functionality before pytest is available.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r'C:\Agents\PersonalAssist')

from packages.messaging.config_store import ConfigStore, get_config_store

def test_token_validation():
    """Test token format validation."""
    print("=" * 60)
    print("TEST 1: Token Validation")
    print("=" * 60)
    
    store = ConfigStore()
    
    # Valid tokens
    assert store.validate_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") is True
    print("✓ Valid token format accepted")
    
    # Empty token
    assert store.validate_token("") is True
    print("✓ Empty token accepted (no token configured)")
    
    # Invalid tokens
    assert store.validate_token("invalid") is False
    print("✓ Invalid token format rejected")
    
    assert store.validate_token("123456:short") is False
    print("✓ Too-short token rejected")
    
    print("✅ Token validation tests PASSED\n")


def test_save_and_load():
    """Test saving and loading configuration."""
    print("=" * 60)
    print("TEST 2: Save and Load Configuration")
    print("=" * 60)
    
    temp_dir = Path(tempfile.mkdtemp())
    store = ConfigStore()
    store.config_dir = temp_dir
    store.config_file = temp_dir / "telegram_config.env"
    store._config_cache = None
    
    # Initial state
    assert store.has_config() is False
    print("✓ Initial state: no config")
    
    # Save config
    store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
    assert store.config_file.exists()
    print("✓ Config file created")
    
    # Load config
    config = store.load()
    assert config is not None
    assert config["bot_token"] == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert config["dm_policy"] == "pairing"
    print("✓ Config loaded successfully")
    print(f"  Token: {config['bot_token'][:10]}...")
    print(f"  Policy: {config['dm_policy']}")
    
    # Test has_config
    assert store.has_config() is True
    print("✓ has_config() returns True")
    
    # Test get_config_display
    display = store.get_config_display()
    assert display["bot_token_set"] is True
    assert display["token_display"] == "123...w11"
    print(f"✓ Token redaction works: {display['token_display']}")
    
    # Clear config
    store.clear()
    assert store.has_config() is False
    assert not store.config_file.exists()
    print("✓ Config cleared successfully")
    
    print("✅ Save and load tests PASSED\n")


def test_dm_policies():
    """Test different DM policy values."""
    print("=" * 60)
    print("TEST 3: DM Policy Values")
    print("=" * 60)
    
    temp_dir = Path(tempfile.mkdtemp())
    store = ConfigStore()
    store.config_dir = temp_dir
    store.config_file = temp_dir / "telegram_config.env"
    store._config_cache = None
    
    # Test pairing policy
    store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "pairing")
    assert store.get_dm_policy() == "pairing"
    print("✓ 'pairing' policy works")
    
    # Test open policy
    store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "open")
    assert store.get_dm_policy() == "open"
    print("✓ 'open' policy works")
    
    # Test allowlist policy
    store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "allowlist")
    assert store.get_dm_policy() == "allowlist"
    print("✓ 'allowlist' policy works")
    
    # Test invalid policy
    try:
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Invalid policy rejected: {e}")
    
    print("✅ DM policy tests PASSED\n")


def test_error_handling():
    """Test error handling."""
    print("=" * 60)
    print("TEST 4: Error Handling")
    print("=" * 60)
    
    temp_dir = Path(tempfile.mkdtemp())
    store = ConfigStore()
    store.config_dir = temp_dir
    store.config_file = temp_dir / "telegram_config.env"
    store._config_cache = None
    
    # Test invalid token
    try:
        store.save("invalid-token", "pairing")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Invalid token rejected: {str(e)[:50]}...")
    
    # Test invalid policy
    try:
        store.save("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "bad_policy")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Invalid policy rejected: {str(e)[:50]}...")
    
    print("✅ Error handling tests PASSED\n")


def test_convenience_functions():
    """Test convenience functions."""
    print("=" * 60)
    print("TEST 5: Convenience Functions")
    print("=" * 60)
    
    from packages.messaging.config_store import (
        get_config_store,
        get_telegram_token,
        get_telegram_dm_policy,
    )
    
    # Test get_config_store (singleton)
    store1 = get_config_store()
    store2 = get_config_store()
    assert store1 is store2
    print("✓ get_config_store() returns singleton")
    
    # Test get_telegram_dm_policy (default)
    policy = get_telegram_dm_policy()
    assert policy in ("pairing", "allowlist", "open")  # Should be one of valid policies
    print(f"✓ Default DM policy: {policy}")
    
    # Test get_telegram_token (may be None or env var)
    token = get_telegram_token()
    # Token can be None (no config) or a string (from env var)
    assert token is None or isinstance(token, str)
    if token:
        print(f"✓ get_telegram_token() returns token from env: {token[:10]}...")
    else:
        print("✓ get_telegram_token() returns None when not configured")
    
    print("✅ Convenience function tests PASSED\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ConfigStore Test Suite")
    print("=" * 60 + "\n")
    
    try:
        test_token_validation()
        test_save_and_load()
        test_dm_policies()
        test_error_handling()
        test_convenience_functions()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
