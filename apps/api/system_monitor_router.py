"""
System Monitor Router

FastAPI router for system monitoring endpoints.
Provides REST API for Windows system metrics.

Endpoints:
- GET /system/cpu - CPU usage and information
- GET /system/memory - Memory (RAM) usage
- GET /system/disk - Disk usage for all drives
- GET /system/battery - Battery status (laptops)
- GET /system/network - Network interface information
- GET /system/processes - Top processes by CPU/memory
- GET /system/logs - Windows Event Logs
- GET /system/summary - Comprehensive system summary

Usage:
    from apps.api.system_monitor_router import router
    
    app.include_router(router)

Dependencies:
    pip install psutil
    pip install pywin32  # For Windows Event Logs (optional)
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


# ── Response Models ───────────────────────────────────────────────────


class CPUInfo:
    """CPU information response model."""
    pass  # Using dict for flexibility


class MemoryInfo:
    """Memory information response model."""
    pass  # Using dict for flexibility


class DiskInfo:
    """Disk information response model."""
    pass  # Using dict for flexibility


# ── CPU Endpoints ─────────────────────────────────────────────────────


@router.get("/cpu")
async def get_cpu_usage():
    """
    Get CPU usage and information.
    
    **Response Fields:**
    - `usage_percent`: Current CPU usage percentage
    - `cores_physical`: Number of physical cores
    - `cores_logical`: Number of logical cores (with hyperthreading)
    - `frequency_mhz`: Current CPU frequency in MHz
    - `per_cpu_usage`: List of usage percentages per core
    
    **Example Response:**
    ```json
    {
        "usage_percent": 45.2,
        "cores_physical": 8,
        "cores_logical": 16,
        "frequency_mhz": 3200,
        "per_cpu_usage": [45.1, 42.3, 48.5, 39.2, ...],
        "available": true,
        "timestamp": "2026-03-29T10:00:00"
    }
    ```
    
    **Error Response:**
    ```json
    {
        "error": "psutil not installed. Run: pip install psutil",
        "available": false
    }
    ```
    """
    try:
        from packages.tools.system_monitor import get_cpu_info
        result = await get_cpu_info()
        return result
    except Exception as e:
        logger.error(f"Get CPU info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Memory Endpoints ──────────────────────────────────────────────────


@router.get("/memory")
async def get_memory_usage():
    """
    Get memory (RAM) usage information.
    
    **Response Fields:**
    - `total_gb`: Total RAM in GB
    - `available_gb`: Available RAM in GB
    - `used_gb`: Used RAM in GB
    - `usage_percent`: Percentage of RAM used
    - `swap_total_gb`: Total swap space in GB
    - `swap_used_gb`: Used swap space in GB
    
    **Example Response:**
    ```json
    {
        "total_gb": 16.0,
        "available_gb": 8.5,
        "used_gb": 7.5,
        "usage_percent": 46.9,
        "swap_total_gb": 2.0,
        "swap_used_gb": 0.5,
        "available": true,
        "timestamp": "2026-03-29T10:00:00"
    }
    ```
    """
    try:
        from packages.tools.system_monitor import get_memory_info
        result = await get_memory_info()
        return result
    except Exception as e:
        logger.error(f"Get memory info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Disk Endpoints ────────────────────────────────────────────────────


@router.get("/disk")
async def get_disk_usage():
    """
    Get disk usage information for all drives.
    
    **Response Fields:**
    - List of drives, each with:
      - `device`: Drive letter/device name
      - `mountpoint`: Mount point path
      - `total_gb`: Total size in GB
      - `used_gb`: Used space in GB
      - `free_gb`: Free space in GB
      - `usage_percent`: Percentage of disk used
      - `fstype`: Filesystem type
    
    **Example Response:**
    ```json
    [
        {
            "device": "C:",
            "mountpoint": "C:\\",
            "total_gb": 512.0,
            "used_gb": 256.0,
            "free_gb": 256.0,
            "usage_percent": 50.0,
            "fstype": "NTFS",
            "available": true
        }
    ]
    ```
    """
    try:
        from packages.tools.system_monitor import get_disk_info
        result = await get_disk_info()
        return result
    except Exception as e:
        logger.error(f"Get disk info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Battery Endpoints ─────────────────────────────────────────────────


@router.get("/battery")
async def get_battery_status():
    """
    Get battery status (laptops only).
    
    **Response Fields:**
    - `present`: Whether battery is present
    - `percent`: Battery percentage (0-100)
    - `time_left_minutes`: Estimated time remaining in minutes
    - `power_plugged`: Whether AC power is connected
    - `status`: charging | discharging | full | unknown
    
    **Example Response (laptop):**
    ```json
    {
        "present": true,
        "percent": 85,
        "time_left_minutes": 120,
        "power_plugged": true,
        "status": "charging",
        "available": true,
        "timestamp": "2026-03-29T10:00:00"
    }
    ```
    
    **Example Response (desktop):**
    ```json
    {
        "present": false,
        "status": "no_battery",
        "available": true,
        "timestamp": "2026-03-29T10:00:00"
    }
    ```
    """
    try:
        from packages.tools.system_monitor import get_battery_info
        result = await get_battery_info()
        return result
    except Exception as e:
        logger.error(f"Get battery info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Network Endpoints ─────────────────────────────────────────────────


@router.get("/network")
async def get_network_status():
    """
    Get network interface information.
    
    **Response Fields:**
    - `interfaces`: List of network interfaces
    - `bytes_sent`: Total bytes sent
    - `bytes_recv`: Total bytes received
    - `packets_sent`: Total packets sent
    - `packets_recv`: Total packets received
    
    **Example Response:**
    ```json
    {
        "interfaces": [
            {
                "name": "Ethernet",
                "is_up": true,
                "speed_mbps": 1000,
                "addresses": [
                    {
                        "type": "IPv4",
                        "address": "192.168.1.100",
                        "netmask": "255.255.255.0"
                    }
                ]
            }
        ],
        "bytes_sent": 1234567890,
        "bytes_recv": 9876543210,
        "available": true,
        "timestamp": "2026-03-29T10:00:00"
    }
    ```
    """
    try:
        from packages.tools.system_monitor import get_network_info
        result = await get_network_info()
        return result
    except Exception as e:
        logger.error(f"Get network info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Process Endpoints ─────────────────────────────────────────────────


@router.get("/processes")
async def get_process_list(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of processes"),
    sort_by: str = Query(default="cpu", enum=["cpu", "memory"], description="Sort criterion"),
):
    """
    Get list of top processes by CPU or memory usage.
    
    **Query Parameters:**
    - `limit`: Maximum number of processes (1-100, default: 20)
    - `sort_by`: Sort criterion ("cpu" or "memory", default: "cpu")
    
    **Response Fields:**
    - List of processes, each with:
      - `pid`: Process ID
      - `name`: Process name
      - `cpu_percent`: CPU usage percentage
      - `memory_percent`: Memory usage percentage
      - `memory_mb`: Memory usage in MB
      - `status`: Process status
    
    **Example Response:**
    ```json
    [
        {
            "pid": 1234,
            "name": "chrome.exe",
            "cpu_percent": 15.2,
            "memory_percent": 8.5,
            "memory_mb": 1342,
            "status": "running"
        }
    ]
    ```
    """
    try:
        from packages.tools.system_monitor import get_process_list
        result = await get_process_list(limit=limit, sort_by=sort_by)
        return result
    except Exception as e:
        logger.error(f"Get process list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Event Log Endpoints ───────────────────────────────────────────────


@router.get("/logs")
async def get_event_logs(
    log_name: str = Query(default="System", enum=["System", "Application", "Security"], description="Log name"),
    max_entries: int = Query(default=50, ge=1, le=500, description="Maximum entries"),
    hours_back: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
):
    """
    Get Windows Event Log entries.
    
    **Query Parameters:**
    - `log_name`: Log name (System, Application, Security)
    - `max_entries`: Maximum number of entries (1-500, default: 50)
    - `hours_back`: Only return entries from last N hours (1-168, default: 24)
    
    **Response Fields:**
    - List of events, each with:
      - `time_created`: When event occurred
      - `source`: Event source
      - `event_id`: Event ID number
      - `event_type`: Error | Warning | Information | Audit Success | Audit Failure
      - `message`: Event message text
      - `computer`: Computer name
    
    **Note:** Only available on Windows with pywin32 installed.
    
    **Example Response:**
    ```json
    [
        {
            "time_created": "2026-03-29T10:00:00",
            "source": "Service Control Manager",
            "event_id": 7036,
            "event_type": "Information",
            "message": "The Windows Update service entered the running state.",
            "computer": "DESKTOP-ABC123"
        }
    ]
    ```
    """
    try:
        from packages.tools.system_monitor import get_windows_event_logs
        result = await get_windows_event_logs(
            log_name=log_name,
            max_entries=max_entries,
            hours_back=hours_back
        )
        return result
    except Exception as e:
        logger.error(f"Get event logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Summary Endpoints ─────────────────────────────────────────────────


@router.get("/summary")
async def get_system_summary():
    """
    Get comprehensive system summary.
    
    Combines CPU, memory, disk, and battery info into a single response.
    Useful for health dashboards and quick system status checks.
    
    **Response Fields:**
    - `cpu`: CPU information (see /system/cpu)
    - `memory`: Memory information (see /system/memory)
    - `disk`: Disk information (see /system/disk)
    - `battery`: Battery information (see /system/battery)
    - `timestamp`: When summary was generated
    
    **Example Response:**
    ```json
    {
        "cpu": {...},
        "memory": {...},
        "disk": [...],
        "battery": {...},
        "timestamp": "2026-03-29T10:00:00",
        "available": true
    }
    ```
    
    **Use Case:**
    Perfect for health dashboards that need all system metrics in a single request.
    """
    try:
        from packages.tools.system_monitor import get_system_summary
        result = await get_system_summary()
        return result
    except Exception as e:
        logger.error(f"Get system summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
