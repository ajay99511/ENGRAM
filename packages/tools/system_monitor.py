"""
Windows System Monitor Tools

Provides tools for monitoring Windows system metrics:
- CPU usage and information
- Memory (RAM) usage
- Disk usage for all drives
- Battery status (laptops only)
- Windows Event Logs

These tools are read-only and safe to use in agent workflows.

Usage:
    from packages.tools.system_monitor import (
        get_cpu_info,
        get_memory_info,
        get_disk_info,
        get_battery_info,
        get_system_summary,
    )
    
    cpu = await get_cpu_info()
    memory = await get_memory_info()
    disk = await get_disk_info()
    battery = await get_battery_info()
    summary = await get_system_summary()

Dependencies:
    pip install psutil
    pip install pywin32  # Windows Event Logs only (optional)
"""

import asyncio
import logging
import platform
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check if running on Windows
IS_WINDOWS = platform.system() == "Windows"

# Import psutil conditionally
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not installed. System monitoring tools will return error messages.")

# Import Windows-specific modules conditionally
if IS_WINDOWS:
    try:
        import win32evtlog
        import win32evtlogutil
        import win32con
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        logger.warning("pywin32 not installed. Windows Event Log tools disabled.")
else:
    WIN32_AVAILABLE = False


async def get_cpu_info() -> Dict[str, Any]:
    """
    Get CPU usage and information.
    
    Returns:
        Dict with CPU metrics:
        - usage_percent: Current CPU usage percentage
        - cores_physical: Number of physical cores
        - cores_logical: Number of logical cores (with hyperthreading)
        - frequency_mhz: Current CPU frequency in MHz
        - per_cpu_usage: List of usage percentages per core
        
    Example:
        {
            "usage_percent": 45.2,
            "cores_physical": 8,
            "cores_logical": 16,
            "frequency_mhz": 3200,
            "per_cpu_usage": [45.1, 42.3, 48.5, ...]
        }
    """
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not installed. Run: pip install psutil",
            "available": False
        }
    
    try:
        # Get CPU usage with 1-second interval for accuracy
        usage = await asyncio.to_thread(psutil.cpu_percent, interval=1.0)
        per_cpu = await asyncio.to_thread(psutil.cpu_percent, interval=1.0, percpu=True)
        freq = await asyncio.to_thread(psutil.cpu_freq)
        
        result = {
            "usage_percent": usage,
            "cores_physical": await asyncio.to_thread(psutil.cpu_count, logical=False),
            "cores_logical": await asyncio.to_thread(psutil.cpu_count, logical=True),
            "frequency_mhz": freq.current if freq else 0,
            "per_cpu_usage": per_cpu,
            "available": True,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.debug(f"CPU info retrieved: {usage}% usage, {result['cores_logical']} cores")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get CPU info: {e}")
        return {
            "error": str(e),
            "available": False
        }


async def get_memory_info() -> Dict[str, Any]:
    """
    Get memory (RAM) usage information.
    
    Returns:
        Dict with memory metrics:
        - total_gb: Total RAM in GB
        - available_gb: Available RAM in GB
        - used_gb: Used RAM in GB
        - usage_percent: Percentage of RAM used
        - swap_total_gb: Total swap space in GB
        - swap_used_gb: Used swap space in GB
        
    Example:
        {
            "total_gb": 16.0,
            "available_gb": 8.5,
            "used_gb": 7.5,
            "usage_percent": 46.9,
            "swap_total_gb": 2.0,
            "swap_used_gb": 0.5
        }
    """
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not installed. Run: pip install psutil",
            "available": False
        }
    
    try:
        mem = await asyncio.to_thread(psutil.virtual_memory)
        swap = await asyncio.to_thread(psutil.swap_memory)
        
        result = {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "usage_percent": mem.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "available": True,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.debug(f"Memory info retrieved: {result['used_gb']}/{result['total_gb']} GB used")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get memory info: {e}")
        return {
            "error": str(e),
            "available": False
        }


async def get_disk_info() -> List[Dict[str, Any]]:
    """
    Get disk usage information for all drives.
    
    Returns:
        List of dicts, one per drive:
        - device: Drive letter/device name
        - mountpoint: Mount point path
        - total_gb: Total size in GB
        - used_gb: Used space in GB
        - free_gb: Free space in GB
        - usage_percent: Percentage of disk used
        
    Example:
        [
            {
                "device": "C:",
                "mountpoint": "C:\\",
                "total_gb": 512.0,
                "used_gb": 256.0,
                "free_gb": 256.0,
                "usage_percent": 50.0
            },
            ...
        ]
    """
    if not PSUTIL_AVAILABLE:
        return [{
            "error": "psutil not installed. Run: pip install psutil",
            "available": False
        }]
    
    try:
        partitions = await asyncio.to_thread(psutil.disk_partitions)
        result = []
        
        for partition in partitions:
            try:
                usage = await asyncio.to_thread(psutil.disk_usage, partition.mountpoint)
                result.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "usage_percent": usage.percent,
                    "fstype": partition.fstype,
                })
            except PermissionError:
                # Skip inaccessible drives
                logger.debug(f"Skipping inaccessible drive: {partition.device}")
                continue
            except Exception as e:
                logger.warning(f"Failed to get disk info for {partition.device}: {e}")
                continue
        
        logger.debug(f"Disk info retrieved for {len(result)} drives")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get disk info: {e}")
        return [{
            "error": str(e),
            "available": False
        }]


async def get_battery_info() -> Dict[str, Any]:
    """
    Get battery status (laptops only).
    
    Returns:
        Dict with battery metrics:
        - present: Whether battery is present
        - percent: Battery percentage (0-100)
        - time_left_minutes: Estimated time remaining in minutes
        - power_plugged: Whether AC power is connected
        - status: charging | discharging | full | unknown
        
    Example (laptop):
        {
            "present": True,
            "percent": 85,
            "time_left_minutes": 120,
            "power_plugged": True,
            "status": "charging"
        }
        
    Example (desktop):
        {
            "present": False,
            "status": "no_battery"
        }
    """
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not installed. Run: pip install psutil",
            "present": False,
            "available": False
        }
    
    try:
        battery = await asyncio.to_thread(psutil.sensors_battery)
        
        if battery is None:
            return {
                "present": False,
                "status": "no_battery",
                "available": True,
                "timestamp": datetime.now().isoformat(),
            }
        
        # Determine status
        if battery.power_plugged:
            status = "charging" if battery.percent < 100 else "full"
        else:
            status = "discharging" if battery.percent < 100 else "full"
        
        result = {
            "present": True,
            "percent": battery.percent,
            "time_left_minutes": (
                battery.secsleft // 60 if battery.secsleft != -1 else None
            ),
            "power_plugged": battery.power_plugged,
            "status": status,
            "available": True,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.debug(f"Battery info retrieved: {battery.percent}%, {status}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get battery info: {e}")
        return {
            "error": str(e),
            "present": False,
            "available": False
        }


async def get_windows_event_logs(
    log_name: str = "System",
    max_entries: int = 50,
    hours_back: int = 24,
) -> List[Dict[str, Any]]:
    """
    Get Windows Event Log entries.
    
    Args:
        log_name: Log name (System, Application, Security)
        max_entries: Maximum number of entries to return
        hours_back: Only return entries from last N hours
    
    Returns:
        List of event log entries:
        - time_created: When event occurred
        - source: Event source
        - event_id: Event ID number
        - event_type: Error | Warning | Information | Audit Success | Audit Failure
        - message: Event message text
        
    Example:
        [
            {
                "time_created": "2026-03-29T10:00:00",
                "source": "Service Control Manager",
                "event_id": 7036,
                "event_type": "Information",
                "message": "The Windows Update service entered the running state."
            },
            ...
        ]
    """
    if not IS_WINDOWS:
        return [{
            "error": "Windows Event Logs only available on Windows",
            "available": False
        }]
    
    if not WIN32_AVAILABLE:
        return [{
            "error": "pywin32 not installed. Run: pip install pywin32",
            "available": False
        }]
    
    try:
        # Get event log handle
        logtype = win32evtlog.EVENTLOG_BACKWARDS_READ
        flags = win32evtlog.EVENTLOG_SEQUENTIAL_READ | logtype
        
        handle = win32evtlog.OpenEventLog(None, log_name)
        
        if not handle:
            return [{
                "error": f"Failed to open {log_name} event log",
                "available": False
            }]
        
        # Calculate cutoff time
        cutoff = datetime.now() - timedelta(hours=hours_back)
        
        events = []
        try:
            while len(events) < max_entries:
                events_chunk = win32evtlog.ReadEventLog(handle, flags, 0)
                
                if not events_chunk:
                    break
                
                for event in events_chunk:
                    event_time = event.TimeGenerated.Format()
                    
                    # Parse time and check cutoff
                    try:
                        event_datetime = datetime.strptime(
                            event_time, "%Y-%m-%d %H:%M:%S"
                        )
                        if event_datetime < cutoff:
                            break
                    except:
                        pass
                    
                    # Get event type string
                    event_type_map = {
                        win32evtlog.EVENTLOG_ERROR_TYPE: "Error",
                        win32evtlog.EVENTLOG_WARNING_TYPE: "Warning",
                        win32evtlog.EVENTLOG_INFORMATION_TYPE: "Information",
                        win32evtlog.EVENTLOG_AUDIT_SUCCESS: "Audit Success",
                        win32evtlog.EVENTLOG_AUDIT_FAILURE: "Audit Failure",
                    }
                    event_type = event_type_map.get(
                        event.EventType, "Unknown"
                    )
                    
                    # Get message (may require additional lookup)
                    try:
                        message = win32evtlogutil.SafeFormatMessage(
                            event, log_name
                        )
                    except:
                        message = str(event.StringData) if hasattr(event, "StringData") else "No message"
                    
                    events.append({
                        "time_created": event_time,
                        "source": event.SourceName,
                        "event_id": event.EventID,
                        "event_type": event_type,
                        "message": message[:500],  # Truncate long messages
                        "computer": event.ComputerName,
                    })
                    
                    if len(events) >= max_entries:
                        break
                
                if not events_chunk:
                    break
            
        finally:
            win32evtlog.CloseEventLog(handle)
        
        logger.info(f"Retrieved {len(events)} events from {log_name} log")
        return events
        
    except Exception as e:
        logger.error(f"Failed to get event logs: {e}")
        return [{
            "error": str(e),
            "available": False
        }]


async def get_system_summary() -> Dict[str, Any]:
    """
    Get comprehensive system summary.
    
    Combines CPU, memory, disk, and battery info into a single response.
    Useful for health dashboards and quick system status checks.
    
    Returns:
        Dict with all system metrics:
        - cpu: CPU information
        - memory: Memory information
        - disk: List of disk information
        - battery: Battery information
        - timestamp: When summary was generated
        
    Example:
        {
            "cpu": {...},
            "memory": {...},
            "disk": [...],
            "battery": {...},
            "timestamp": "2026-03-29T10:00:00"
        }
    """
    cpu, memory, disk, battery = await asyncio.gather(
        get_cpu_info(),
        get_memory_info(),
        get_disk_info(),
        get_battery_info(),
    )
    
    return {
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "battery": battery,
        "timestamp": datetime.now().isoformat(),
        "available": True,
    }


async def get_network_info() -> Dict[str, Any]:
    """
    Get network interface information.
    
    Returns:
        Dict with network metrics:
        - interfaces: List of network interfaces
        - bytes_sent: Total bytes sent
        - bytes_recv: Total bytes received
        
    Example:
        {
            "interfaces": [
                {
                    "name": "Ethernet",
                    "is_up": True,
                    "speed_mbps": 1000
                }
            ],
            "bytes_sent": 1234567890,
            "bytes_recv": 9876543210
        }
    """
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not installed. Run: pip install psutil",
            "available": False
        }
    
    try:
        # Get network I/O counters
        net_io = await asyncio.to_thread(psutil.net_io_counters)
        
        # Get network interfaces
        interfaces = []
        addrs = await asyncio.to_thread(psutil.net_if_addrs)
        stats = await asyncio.to_thread(psutil.net_if_stats)
        
        for name, addr_list in addrs.items():
            if name not in stats:
                continue
            
            interface_info = {
                "name": name,
                "is_up": stats[name].isup,
                "speed_mbps": stats[name].speed // (1024 * 1024) if stats[name].speed else 0,
                "addresses": []
            }
            
            for addr in addr_list:
                if addr.family.name == 'AF_INET':  # IPv4
                    interface_info["addresses"].append({
                        "type": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask
                    })
                elif addr.family.name == 'AF_INET6':  # IPv6
                    interface_info["addresses"].append({
                        "type": "IPv6",
                        "address": addr.address
                    })
            
            interfaces.append(interface_info)
        
        result = {
            "interfaces": interfaces,
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "available": True,
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.debug(f"Network info retrieved for {len(interfaces)} interfaces")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get network info: {e}")
        return {
            "error": str(e),
            "available": False
        }


async def get_process_list(
    limit: int = 20,
    sort_by: str = "cpu",
) -> List[Dict[str, Any]]:
    """
    Get list of top processes by CPU or memory usage.
    
    Args:
        limit: Maximum number of processes to return
        sort_by: Sort criterion ("cpu" or "memory")
    
    Returns:
        List of process information:
        - pid: Process ID
        - name: Process name
        - cpu_percent: CPU usage percentage
        - memory_percent: Memory usage percentage
        - memory_mb: Memory usage in MB
        - status: Process status
        
    Example:
        [
            {
                "pid": 1234,
                "name": "chrome.exe",
                "cpu_percent": 15.2,
                "memory_percent": 8.5,
                "memory_mb": 1342,
                "status": "running"
            },
            ...
        ]
    """
    if not PSUTIL_AVAILABLE:
        return [{
            "error": "psutil not installed. Run: pip install psutil",
            "available": False
        }]
    
    try:
        processes = []
        
        # Get all processes
        for proc in await asyncio.to_thread(psutil.process_iter, ['pid', 'name']):
            try:
                pinfo = proc.info
                
                # Get additional info
                cpu = await asyncio.to_thread(proc.cpu_percent, 0.1)
                mem = await asyncio.to_thread(proc.memory_percent)
                mem_info = await asyncio.to_thread(proc.memory_info)
                status = await asyncio.to_thread(proc.status)
                
                processes.append({
                    "pid": pinfo["pid"],
                    "name": pinfo["name"],
                    "cpu_percent": cpu,
                    "memory_percent": mem,
                    "memory_mb": round(mem_info.rss / (1024 * 1024), 2),
                    "status": status,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by specified criterion
        if sort_by == "memory":
            processes.sort(key=lambda x: x["memory_percent"], reverse=True)
        else:  # default to cpu
            processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        
        # Limit results
        result = processes[:limit]
        
        logger.debug(f"Process list retrieved: {len(result)} processes (sorted by {sort_by})")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get process list: {e}")
        return [{
            "error": str(e),
            "available": False
        }]
