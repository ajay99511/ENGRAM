#!/usr/bin/env python3
"""
Autonomous Agent Manual Test Script

Run this to verify AutonomousAgent functionality.
Note: This tests the agent logic, not actual API integration.
"""

import sys
import asyncio
from datetime import timedelta

sys.path.insert(0, r'C:\Agents\PersonalAssist')

from packages.agents.autonomous_agent import (
    AutonomousAgent,
    get_autonomous_agent,
    reset_autonomous_agent,
    start_autonomous_watch,
    start_autonomous_research,
    start_autonomous_gap_analysis,
    stop_autonomous_all,
    get_autonomous_status,
)


def test_agent_creation():
    """Test autonomous agent instantiation."""
    print("=" * 60)
    print("TEST 1: Agent Creation")
    print("=" * 60)
    
    # Test direct creation
    agent = AutonomousAgent()
    assert agent is not None
    print("✓ AutonomousAgent can be created")
    
    # Test singleton
    reset_autonomous_agent()
    agent1 = get_autonomous_agent()
    agent2 = get_autonomous_agent()
    assert agent1 is agent2
    print("✓ get_autonomous_agent() returns singleton")
    
    # Test initial state
    assert agent.running is False
    assert agent.watch_task is None
    assert agent.research_task is None
    assert agent.gap_analysis_task is None
    print("✓ Initial state is stopped")
    
    # Test status
    status = agent.get_status()
    assert status["running"] is False
    assert status["watch_mode"]["active"] is False
    print(f"✓ Initial status: {status['running']}")
    
    print("✅ Agent creation tests PASSED\n")


def test_callback_registration():
    """Test callback registration and triggering."""
    print("=" * 60)
    print("TEST 2: Callback Registration")
    print("=" * 60)
    
    reset_autonomous_agent()
    agent = get_autonomous_agent()
    
    # Track callback calls
    callback_calls = []
    
    def test_callback(data):
        callback_calls.append(data)
    
    # Register callbacks
    agent.register_callback("on_change", test_callback)
    agent.register_callback("on_research_complete", test_callback)
    agent.register_callback("on_gap_found", test_callback)
    print("✓ Registered callbacks for all event types")
    
    # Verify registration
    status = agent.get_status()
    assert status["callbacks_registered"]["on_change"] == 1
    assert status["callbacks_registered"]["on_research_complete"] == 1
    assert status["callbacks_registered"]["on_gap_found"] == 1
    print("✓ Callbacks appear in status")
    
    # Trigger callback manually
    agent._trigger_callback("on_change", {"test": "data"})
    assert len(callback_calls) == 1
    assert callback_calls[0]["test"] == "data"
    print("✓ Callback triggered successfully")
    
    # Unregister callback
    agent.unregister_callback("on_change", test_callback)
    status = agent.get_status()
    assert status["callbacks_registered"]["on_change"] == 0
    print("✓ Callback unregistered successfully")
    
    print("✅ Callback registration tests PASSED\n")


def test_status_tracking():
    """Test status tracking."""
    print("=" * 60)
    print("TEST 3: Status Tracking")
    print("=" * 60)
    
    reset_autonomous_agent()
    agent = get_autonomous_agent()
    
    # Test initial status
    status = agent.get_status()
    assert "workspace_id" in status
    assert "running" in status
    assert "watch_mode" in status
    assert "research" in status
    assert "gap_analysis" in status
    print("✓ Status contains all required fields")
    
    # Test workspace_id
    assert status["workspace_id"] == "default"
    print(f"✓ Workspace ID: {status['workspace_id']}")
    
    # Test task states
    assert status["watch_mode"]["active"] is False
    assert status["research"]["active"] is False
    assert status["gap_analysis"]["active"] is False
    print("✓ All tasks show inactive initially")
    
    print("✅ Status tracking tests PASSED\n")


def test_stop_all():
    """Test stop all functionality."""
    print("=" * 60)
    print("TEST 4: Stop All")
    print("=" * 60)
    
    reset_autonomous_agent()
    agent = get_autonomous_agent()
    
    # Stop when nothing is running (should not crash)
    agent.stop_all()
    print("✓ stop_all() works when nothing running")
    
    # Verify state
    status = agent.get_status()
    assert status["running"] is False
    print("✓ State correct after stop_all()")
    
    print("✅ Stop all tests PASSED\n")


def test_convenience_functions():
    """Test convenience functions."""
    print("=" * 60)
    print("TEST 5: Convenience Functions")
    print("=" * 60)
    
    reset_autonomous_agent()
    
    # Test get_autonomous_status
    status = get_autonomous_status()
    assert "running" in status
    print("✓ get_autonomous_status() works")
    
    # Test stop_autonomous_all
    stop_autonomous_all()
    print("✓ stop_autonomous_all() works")
    
    print("✅ Convenience function tests PASSED\n")


async def test_watch_mode_short():
    """Test watch mode with short interval (doesn't actually start task)."""
    print("=" * 60)
    print("TEST 6: Watch Mode (Simulated)")
    print("=" * 60)
    
    reset_autonomous_agent()
    agent = get_autonomous_agent()
    
    # Test config creation
    agent.watch_config = {
        "repo_path": "/test/path",
        "interval": timedelta(minutes=1),
        "started_at": "2026-03-29T10:00:00",
    }
    print("✓ Watch config can be set")
    
    # Test status with config
    status = agent.get_status()
    assert status["watch_mode"]["config"] is not None
    print("✓ Watch config appears in status")
    
    # Clean up
    agent.watch_config = None
    print("✓ Watch config cleared")
    
    print("✅ Watch mode tests PASSED\n")


async def test_research_short():
    """Test research with short interval (doesn't actually start task)."""
    print("=" * 60)
    print("TEST 7: Research (Simulated)")
    print("=" * 60)
    
    reset_autonomous_agent()
    agent = get_autonomous_agent()
    
    # Test config creation
    agent.research_config = {
        "topics": ["Python best practices", "FastAPI security"],
        "interval": timedelta(hours=1),
        "started_at": "2026-03-29T10:00:00",
    }
    print("✓ Research config can be set")
    
    # Test status with config
    status = agent.get_status()
    assert status["research"]["config"] is not None
    print("✓ Research config appears in status")
    
    # Clean up
    agent.research_config = None
    print("✓ Research config cleared")
    
    print("✅ Research tests PASSED\n")


async def test_gap_analysis_short():
    """Test gap analysis with short interval (doesn't actually start task)."""
    print("=" * 60)
    print("TEST 8: Gap Analysis (Simulated)")
    print("=" * 60)
    
    reset_autonomous_agent()
    agent = get_autonomous_agent()
    
    # Test config creation
    agent.gap_analysis_config = {
        "project_path": "/test/project",
        "interval": timedelta(days=1),
        "started_at": "2026-03-29T10:00:00",
    }
    print("✓ Gap analysis config can be set")
    
    # Test status with config
    status = agent.get_status()
    assert status["gap_analysis"]["config"] is not None
    print("✓ Gap analysis config appears in status")
    
    # Clean up
    agent.gap_analysis_config = None
    print("✓ Gap analysis config cleared")
    
    print("✅ Gap analysis tests PASSED\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Autonomous Agent Test Suite")
    print("=" * 60 + "\n")
    
    try:
        # Synchronous tests
        test_agent_creation()
        test_callback_registration()
        test_status_tracking()
        test_stop_all()
        test_convenience_functions()
        
        # Asynchronous tests
        asyncio.run(test_watch_mode_short())
        asyncio.run(test_research_short())
        asyncio.run(test_gap_analysis_short())
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNote: These tests verify AutonomousAgent logic.")
        print("Full integration testing requires:")
        print("  - Running API server")
        print("  - Git repository for watch mode")
        print("  - Network connectivity for research")
        print("  - Project directory for gap analysis")
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
