#!/usr/bin/env python3
"""
BotManager Manual Test Script

Run this to verify BotManager functionality.
Note: This tests the manager logic, not actual Telegram bot connectivity.
"""

import sys
import asyncio
from datetime import datetime

sys.path.insert(0, r'C:\Agents\PersonalAssist')

from packages.messaging.bot_manager import (
    BotManager,
    get_bot_manager,
    reset_bot_manager,
    start_telegram_bot,
    stop_telegram_bot,
    reload_telegram_bot,
    get_telegram_bot_status,
    is_telegram_bot_running,
)


def test_bot_manager_creation():
    """Test bot manager instantiation."""
    print("=" * 60)
    print("TEST 1: Bot Manager Creation")
    print("=" * 60)
    
    # Test direct creation
    manager = BotManager()
    assert manager is not None
    print("✓ BotManager can be created")
    
    # Test singleton
    reset_bot_manager()
    manager1 = get_bot_manager()
    manager2 = get_bot_manager()
    assert manager1 is manager2
    print("✓ get_bot_manager() returns singleton")
    
    # Test initial state
    assert manager.state == "stopped"
    assert manager.started_at is None
    assert manager.error_message is None
    print("✓ Initial state is 'stopped'")
    
    # Test status
    status = manager.get_status()
    assert status["state"] == "stopped"
    assert status["dm_policy"] == "pairing"
    print(f"✓ Initial status: {status}")
    
    print("✅ Bot manager creation tests PASSED\n")


def test_dm_policy_update():
    """Test DM policy update without restart."""
    print("=" * 60)
    print("TEST 2: DM Policy Update")
    print("=" * 60)
    
    reset_bot_manager()
    manager = get_bot_manager()
    
    # Test valid policy updates
    manager.update_dm_policy("open")
    assert manager.config["dm_policy"] == "open"
    print("✓ DM policy updated to 'open'")
    
    manager.update_dm_policy("allowlist")
    assert manager.config["dm_policy"] == "allowlist"
    print("✓ DM policy updated to 'allowlist'")
    
    manager.update_dm_policy("pairing")
    assert manager.config["dm_policy"] == "pairing"
    print("✓ DM policy updated to 'pairing'")
    
    # Test invalid policy
    manager.update_dm_policy("invalid")
    assert manager.config["dm_policy"] == "pairing"  # Should not change
    print("✓ Invalid DM policy rejected")
    
    # Test status reflects policy
    status = manager.get_status()
    assert status["dm_policy"] == "pairing"
    print(f"✓ Status reflects current policy: {status['dm_policy']}")
    
    print("✅ DM policy update tests PASSED\n")


def test_start_with_invalid_config():
    """Test start with invalid configuration."""
    print("=" * 60)
    print("TEST 3: Start with Invalid Configuration")
    print("=" * 60)
    
    reset_bot_manager()
    manager = get_bot_manager()
    
    # Test empty token
    result = asyncio.run(manager.start("", "pairing"))
    assert result is False
    print("✓ Empty token rejected")
    
    # Test None token
    result = asyncio.run(manager.start(None, "pairing"))  # type: ignore
    assert result is False
    print("✓ None token rejected")
    
    # Test invalid policy
    result = asyncio.run(manager.start("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "invalid"))
    assert result is False
    print("✓ Invalid DM policy rejected")
    
    # Test state unchanged after failure
    assert manager.state == "stopped"
    print("✓ State unchanged after failed start")
    
    print("✅ Invalid configuration tests PASSED\n")


def test_convenience_functions():
    """Test convenience functions."""
    print("=" * 60)
    print("TEST 4: Convenience Functions")
    print("=" * 60)
    
    reset_bot_manager()
    
    # Test get_telegram_bot_status
    status = get_telegram_bot_status()
    assert "state" in status
    assert "dm_policy" in status
    print(f"✓ get_telegram_bot_status() works: {status['state']}")
    
    # Test is_telegram_bot_running
    running = is_telegram_bot_running()
    assert running is False  # Should be False initially
    print(f"✓ is_telegram_bot_running() works: {running}")
    
    # Test start with invalid token (should fail gracefully)
    result = asyncio.run(start_telegram_bot("", "pairing"))
    assert result is False
    print("✓ start_telegram_bot() handles invalid token")
    
    # Test stop when not running
    asyncio.run(stop_telegram_bot())
    print("✓ stop_telegram_bot() works when not running")
    
    print("✅ Convenience function tests PASSED\n")


def test_state_transitions():
    """Test valid state transitions."""
    print("=" * 60)
    print("TEST 5: State Transitions")
    print("=" * 60)
    
    reset_bot_manager()
    manager = get_bot_manager()
    
    # Initial state
    assert manager.state == "stopped"
    print("✓ Initial state: stopped")
    
    # Test status in stopped state
    status = manager.get_status()
    assert status["state"] == "stopped"
    assert "started_at" not in status
    assert "uptime_seconds" not in status
    print("✓ Stopped state status correct")
    
    # Test is_running
    assert manager.is_running() is False
    print("✓ is_running() returns False when stopped")
    
    # Test get_uptime
    uptime = manager.get_uptime()
    assert uptime is None
    print("✓ get_uptime() returns None when stopped")
    
    print("✅ State transition tests PASSED\n")


def test_error_state():
    """Test error state handling."""
    print("=" * 60)
    print("TEST 6: Error State Handling")
    print("=" * 60)
    
    reset_bot_manager()
    manager = get_bot_manager()
    
    # Manually set error state for testing
    manager.state = "error"
    manager.error_message = "Test error message"
    
    # Test status includes error message
    status = manager.get_status()
    assert status["state"] == "error"
    assert status["error_message"] == "Test error message"
    print(f"✓ Error state includes error message")
    
    # Reset state
    manager.state = "stopped"
    manager.error_message = None
    
    # Test status without error message
    status = manager.get_status()
    assert status["state"] == "stopped"
    assert "error_message" not in status
    print("✓ Non-error state excludes error_message")
    
    print("✅ Error state handling tests PASSED\n")


def test_concurrent_access():
    """Test thread safety with concurrent access."""
    print("=" * 60)
    print("TEST 7: Concurrent Access (Thread Safety)")
    print("=" * 60)
    
    reset_bot_manager()
    manager = get_bot_manager()
    
    async def concurrent_updates():
        """Simulate concurrent policy updates."""
        tasks = []
        for i in range(10):
            policy = ["pairing", "open", "allowlist"][i % 3]
            tasks.append(asyncio.create_task(
                asyncio.to_thread(manager.update_dm_policy, policy)
            ))
        
        await asyncio.gather(*tasks)
    
    # Run concurrent updates
    asyncio.run(concurrent_updates())
    
    # Should complete without errors
    print("✓ Concurrent policy updates completed")
    
    # Final state should be valid
    assert manager.config["dm_policy"] in ("pairing", "open", "allowlist")
    print(f"✓ Final policy is valid: {manager.config['dm_policy']}")
    
    print("✅ Concurrent access tests PASSED\n")


def test_reset_function():
    """Test reset_bot_manager function."""
    print("=" * 60)
    print("TEST 8: Reset Function")
    print("=" * 60)
    
    # Get initial manager
    manager1 = get_bot_manager()
    manager1.update_dm_policy("open")
    
    # Reset
    reset_bot_manager()
    
    # Get new manager
    manager2 = get_bot_manager()
    
    # Should be different instance
    assert manager1 is not manager2
    print("✓ Reset creates new instance")
    
    # New instance should have default state
    assert manager2.state == "stopped"
    assert manager2.config["dm_policy"] == "pairing"
    print("✓ New instance has default state")
    
    print("✅ Reset function tests PASSED\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("BotManager Test Suite")
    print("=" * 60 + "\n")
    
    try:
        test_bot_manager_creation()
        test_dm_policy_update()
        test_start_with_invalid_config()
        test_convenience_functions()
        test_state_transitions()
        test_error_state()
        test_concurrent_access()
        test_reset_function()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNote: These tests verify BotManager logic.")
        print("Actual Telegram bot connectivity requires:")
        print("  - python-telegram-bot package installed")
        print("  - Valid Telegram bot token")
        print("  - Network connectivity to Telegram API")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
