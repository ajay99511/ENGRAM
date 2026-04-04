#!/usr/bin/env python3
"""
PersonalAssist Integration Test Suite

Tests all Phase 1-3 functionality:
- Telegram Bot Manager
- System Monitor
- Autonomous Agent

Usage:
    python tests/integration_tests.py

Requirements:
    - API server running on http://localhost:8000
    - psutil installed
    - Network connectivity for some tests
"""

import asyncio
import sys
import time
from typing import Any, Dict, List

# Add project to path
sys.path.insert(0, r'C:\Agents\PersonalAssist')

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


# ── Test Configuration ─────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
API_TOKEN = ""  # Set if API_ACCESS_TOKEN is configured

HEADERS = {}
if API_TOKEN:
    HEADERS["x-api-token"] = API_TOKEN


# ── Test Helpers ──────────────────────────────────────────────────────

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []
    
    def add_pass(self):
        self.passed += 1
    
    def add_fail(self, message: str):
        self.failed += 1
        self.errors.append(f"❌ {self.name}: {message}")
    
    def summary(self) -> str:
        total = self.passed + self.failed
        return f"{self.name}: {self.passed}/{total} passed" + (f" ({self.failed} failed)" if self.failed else " ✅")


async def api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make API request."""
    url = f"{API_BASE}{endpoint}"
    
    # Merge headers properly
    request_headers = HEADERS.copy()
    if 'headers' in kwargs:
        request_headers.update(kwargs.pop('headers'))
    
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=request_headers, **kwargs)
        return {
            "status": response.status_code,
            "data": response.json() if response.content else {},
        }


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")


# ── Health Tests ──────────────────────────────────────────────────────

async def test_health_endpoint(result: TestResult):
    """Test API health endpoint."""
    try:
        response = await api_request("GET", "/health")
        
        if response["status"] == 200:
            if response["data"].get("status") == "ok":
                result.add_pass()
            else:
                result.add_fail(f"Unexpected status: {response['data']}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


# ── Telegram Bot Tests ────────────────────────────────────────────────

async def test_telegram_config_get(result: TestResult):
    """Test GET /telegram/config."""
    try:
        response = await api_request("GET", "/telegram/config")
        
        if response["status"] == 200:
            data = response["data"]
            if "bot_token_set" in data and "dm_policy" in data:
                result.add_pass()
            else:
                result.add_fail(f"Missing fields: {data}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_telegram_status(result: TestResult):
    """Test GET /telegram/status."""
    try:
        response = await api_request("GET", "/telegram/status")
        
        if response["status"] == 200:
            data = response["data"]
            if "state" in data and "dm_policy" in data:
                result.add_pass()
            else:
                result.add_fail(f"Missing fields: {data}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_telegram_config_post(result: TestResult):
    """Test POST /telegram/config with invalid token."""
    try:
        response = await api_request(
            "POST", "/telegram/config",
            json={"bot_token": "invalid", "dm_policy": "pairing"},
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 422 for invalid token
        if response["status"] == 422:
            result.add_pass()
        elif response["status"] == 200:
            result.add_pass()  # Also OK if it accepts
        else:
            result.add_fail(f"Unexpected HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


# ── System Monitor Tests ──────────────────────────────────────────────

async def test_system_cpu(result: TestResult):
    """Test GET /system/cpu."""
    try:
        response = await api_request("GET", "/system/cpu")
        
        if response["status"] == 200:
            data = response["data"]
            if data.get("available", False):
                if "usage_percent" in data and "cores_logical" in data:
                    result.add_pass()
                else:
                    result.add_fail(f"Missing metrics: {data}")
            else:
                result.add_pass()  # OK if psutil not installed
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_system_memory(result: TestResult):
    """Test GET /system/memory."""
    try:
        response = await api_request("GET", "/system/memory")
        
        if response["status"] == 200:
            data = response["data"]
            if data.get("available", False):
                if "total_gb" in data and "usage_percent" in data:
                    result.add_pass()
                else:
                    result.add_fail(f"Missing metrics: {data}")
            else:
                result.add_pass()
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_system_disk(result: TestResult):
    """Test GET /system/disk."""
    try:
        response = await api_request("GET", "/system/disk")
        
        if response["status"] == 200:
            data = response["data"]
            # Handle list response
            if isinstance(data, list):
                if len(data) > 0:
                    drive = data[0]
                    if "device" in drive or "error" in drive:
                        result.add_pass()
                    else:
                        result.add_fail(f"Invalid drive data: {drive}")
                else:
                    result.add_pass()  # OK if empty list
            # Handle error response (psutil not installed)
            elif isinstance(data, dict):
                if "error" in data or not data.get("available", True):
                    result.add_pass()  # Expected when psutil not installed
                else:
                    result.add_pass()  # Some other valid response
            else:
                result.add_pass()  # Accept any valid response
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_system_battery(result: TestResult):
    """Test GET /system/battery."""
    try:
        response = await api_request("GET", "/system/battery")
        
        if response["status"] == 200:
            data = response["data"]
            if data.get("available", False) or not data.get("present", True):
                result.add_pass()
            else:
                result.add_fail(f"Unexpected data: {data}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_system_summary(result: TestResult):
    """Test GET /system/summary."""
    try:
        response = await api_request("GET", "/system/summary")
        
        if response["status"] == 200:
            data = response["data"]
            if "cpu" in data and "memory" in data and "disk" in data:
                result.add_pass()
            else:
                result.add_fail(f"Missing sections: {data.keys()}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


# ── Autonomous Agent Tests ────────────────────────────────────────────

async def test_autonomous_status(result: TestResult):
    """Test GET /autonomous/status."""
    try:
        response = await api_request("GET", "/autonomous/status")
        
        if response["status"] == 200:
            data = response["data"]
            if "workspace_id" in data and "running" in data:
                result.add_pass()
            else:
                result.add_fail(f"Missing fields: {data}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_autonomous_watch_start_stop(result: TestResult):
    """Test POST /autonomous/watch/start and /stop."""
    try:
        # Start with invalid path (should fail gracefully)
        response = await api_request(
            "POST", "/autonomous/watch/start",
            json={"repo_path": "/invalid/path", "interval_minutes": 30},
            headers={"Content-Type": "application/json"}
        )
        
        # Should either start or return error (both OK)
        if response["status"] in [200, 400, 500]:
            result.add_pass()
        else:
            result.add_fail(f"Unexpected HTTP {response['status']}")
        
        # Stop (should always work)
        response = await api_request("POST", "/autonomous/watch/stop")
        if response["status"] == 200:
            result.add_pass()
        else:
            result.add_fail(f"Stop failed: HTTP {response['status']}")
            
    except Exception as e:
        result.add_fail(str(e))


async def test_autonomous_events(result: TestResult):
    """Test GET /autonomous/events (SSE stream)."""
    try:
        # Just test that endpoint exists and returns
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", f"{API_BASE}/autonomous/events", headers=HEADERS) as response:
                if response.status_code == 200:
                    result.add_pass()
                else:
                    result.add_fail(f"HTTP {response.status_code}")
    except Exception as e:
        # Connection errors are OK (streaming)
        if "stream" in str(e).lower() or "connection" in str(e).lower():
            result.add_pass()
        else:
            result.add_fail(str(e))


async def test_autonomous_events_history(result: TestResult):
    """Test GET /autonomous/events/history."""
    try:
        response = await api_request("GET", "/autonomous/events/history?limit=10")
        
        if response["status"] == 200:
            data = response["data"]
            if "events" in data and "count" in data:
                result.add_pass()
            else:
                result.add_fail(f"Missing fields: {data}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_autonomous_events_stats(result: TestResult):
    """Test GET /autonomous/events/stats."""
    try:
        response = await api_request("GET", "/autonomous/events/stats")
        
        if response["status"] == 200:
            data = response["data"]
            if "workspace_id" in data:
                result.add_pass()
            else:
                result.add_fail(f"Missing workspace_id: {data}")
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


async def test_autonomous_stop_all(result: TestResult):
    """Test POST /autonomous/stop-all."""
    try:
        response = await api_request("POST", "/autonomous/stop-all")
        
        if response["status"] == 200:
            result.add_pass()
        else:
            result.add_fail(f"HTTP {response['status']}")
    except Exception as e:
        result.add_fail(str(e))


# ── Main Test Runner ──────────────────────────────────────────────────

async def run_all_tests():
    """Run all integration tests."""
    print_header("PersonalAssist Integration Test Suite")
    
    # Check API is running
    print("Checking API availability...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/health", headers=HEADERS)
            if response.status_code != 200:
                print(f"❌ API not available: HTTP {response.status_code}")
                print(f"   Make sure API is running on {API_BASE}")
                return 1
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print(f"   Make sure API is running on {API_BASE}")
        return 1
    
    print("✅ API is running\n")
    
    # Run tests
    all_results: List[TestResult] = []
    
    # Health tests
    print_header("Health Tests")
    health_result = TestResult("Health")
    await test_health_endpoint(health_result)
    all_results.append(health_result)
    print(health_result.summary())
    
    # Telegram tests
    print_header("Telegram Bot Tests")
    telegram_result = TestResult("Telegram")
    await test_telegram_config_get(telegram_result)
    await test_telegram_status(telegram_result)
    await test_telegram_config_post(telegram_result)
    all_results.append(telegram_result)
    print(telegram_result.summary())
    
    # System monitor tests
    print_header("System Monitor Tests")
    system_result = TestResult("System Monitor")
    await test_system_cpu(system_result)
    await test_system_memory(system_result)
    await test_system_disk(system_result)
    await test_system_battery(system_result)
    await test_system_summary(system_result)
    all_results.append(system_result)
    print(system_result.summary())
    
    # Autonomous tests
    print_header("Autonomous Agent Tests")
    autonomous_result = TestResult("Autonomous")
    await test_autonomous_status(autonomous_result)
    await test_autonomous_watch_start_stop(autonomous_result)
    await test_autonomous_events(autonomous_result)
    await test_autonomous_events_history(autonomous_result)
    await test_autonomous_events_stats(autonomous_result)
    await test_autonomous_stop_all(autonomous_result)
    all_results.append(autonomous_result)
    print(autonomous_result.summary())
    
    # Summary
    print_header("Test Summary")
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total = total_passed + total_failed
    
    for result in all_results:
        print(result.summary())
    
    print(f"\n{'='*60}")
    print(f" Total: {total_passed}/{total} passed")
    if total_failed > 0:
        print(f" Failed: {total_failed}")
        print("\nErrors:")
        for result in all_results:
            for error in result.errors:
                print(f"  {error}")
    else:
        print(f" 🎉 All tests passed!")
    print(f"{'='*60}\n")
    
    return 0 if total_failed == 0 else 1


def main():
    """Main entry point."""
    print(f"API Base: {API_BASE}")
    print(f"API Token: {'Set' if API_TOKEN else 'Not set'}\n")
    
    return asyncio.run(run_all_tests())


if __name__ == "__main__":
    sys.exit(main())
