"""
Workspace Integration for Tools

Wraps existing tool functions with workspace permission checks and audit logging.

Usage:
    from packages.tools.workspace_integration import with_workspace
    
    @with_workspace
    async def read_file(path: str, workspace_manager: WorkspaceManager):
        # Permission check happens automatically
        pass
"""

import logging
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from packages.agents.workspace import WorkspaceManager

logger = logging.getLogger(__name__)


class WorkspacePermissionError(Exception):
    """Raised when a workspace permission check fails."""
    
    def __init__(self, action: str, target: str, reason: str):
        self.action = action
        self.target = target
        self.reason = reason
        super().__init__(f"{action} denied for {target}: {reason}")


def check_read_permission(func: Callable) -> Callable:
    """
    Decorator to check read permission before executing a function.
    
    Usage:
        @check_read_permission
        async def read_file(path: str, workspace_manager: WorkspaceManager, ...):
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract workspace_manager and path from args/kwargs
        workspace_manager: WorkspaceManager | None = kwargs.get('workspace_manager')
        path_str = kwargs.get('path')
        
        # Try to get from positional args
        if not workspace_manager and len(args) > 1:
            workspace_manager = args[1]
        if not path_str and len(args) > 0:
            path_str = args[0]
        
        # Skip check if no workspace manager
        if not workspace_manager or not path_str:
            return await func(*args, **kwargs)
        
        # Check permission
        path = Path(path_str) if isinstance(path_str, str) else path_str
        allowed, reason = workspace_manager.can_read(path)
        
        if not allowed:
            logger.warning(f"Read permission denied: {path} - {reason}")
            raise WorkspacePermissionError("read", str(path), reason)
        
        return await func(*args, **kwargs)
    
    return wrapper


def check_write_permission(func: Callable) -> Callable:
    """
    Decorator to check write permission before executing a function.
    
    Usage:
        @check_write_permission
        async def write_file(path: str, content: str, workspace_manager: WorkspaceManager, ...):
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract workspace_manager and path from args/kwargs
        workspace_manager: WorkspaceManager | None = kwargs.get('workspace_manager')
        path_str = kwargs.get('path')
        
        # Try to get from positional args
        if not workspace_manager and len(args) > 1:
            workspace_manager = args[1]
        if not path_str and len(args) > 0:
            path_str = args[0]
        
        # Skip check if no workspace manager
        if not workspace_manager or not path_str:
            return await func(*args, **kwargs)
        
        # Check permission
        path = Path(path_str) if isinstance(path_str, str) else path_str
        allowed, reason = workspace_manager.can_write(path)
        
        if not allowed:
            logger.warning(f"Write permission denied: {path} - {reason}")
            raise WorkspacePermissionError("write", str(path), reason)
        
        return await func(*args, **kwargs)
    
    return wrapper


def check_execute_permission(func: Callable) -> Callable:
    """
    Decorator to check execute permission before executing a function.
    
    Usage:
        @check_execute_permission
        async def run_command(command: str, workspace_manager: WorkspaceManager, ...):
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract workspace_manager and command from args/kwargs
        workspace_manager: WorkspaceManager | None = kwargs.get('workspace_manager')
        command = kwargs.get('command')
        
        # Try to get from positional args
        if not workspace_manager and len(args) > 1:
            workspace_manager = args[1]
        if not command and len(args) > 0:
            command = args[0]
        
        # Skip check if no workspace manager
        if not workspace_manager or not command:
            return await func(*args, **kwargs)
        
        # Check permission
        allowed, reason = workspace_manager.can_execute(command)
        
        if not allowed:
            logger.warning(f"Execute permission denied: {command} - {reason}")
            raise WorkspacePermissionError("execute", command, reason)
        
        return await func(*args, **kwargs)
    
    return wrapper


def check_git_permission(func: Callable) -> Callable:
    """
    Decorator to check Git operation permission before executing a function.
    
    Usage:
        @check_git_permission
        async def git_operation(operation: str, workspace_manager: WorkspaceManager, ...):
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract workspace_manager and operation from args/kwargs
        workspace_manager: WorkspaceManager | None = kwargs.get('workspace_manager')
        operation = kwargs.get('operation')
        
        # Try to get from positional args
        if not workspace_manager and len(args) > 1:
            workspace_manager = args[1]
        if not operation and len(args) > 0:
            operation = args[0]
        
        # Skip check if no workspace manager
        if not workspace_manager or not operation:
            return await func(*args, **kwargs)
        
        # Check permission
        allowed, reason = workspace_manager.can_perform_git_operation(operation)
        
        if not allowed:
            logger.warning(f"Git operation denied: {operation} - {reason}")
            raise WorkspacePermissionError("git", operation, reason)
        
        return await func(*args, **kwargs)
    
    return wrapper


def get_workspace_manager(project_id: str) -> WorkspaceManager | None:
    """
    Get workspace manager for a project.
    
    Args:
        project_id: Project identifier
    
    Returns:
        WorkspaceManager or None if not configured
    """
    from packages.agents.workspace import load_workspace_config
    
    config = load_workspace_config(project_id)
    if not config:
        return None
    
    return WorkspaceManager(config)


async def execute_with_workspace(
    func: Callable,
    project_id: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Execute a function with workspace permission checks.
    
    Args:
        func: Function to execute
        project_id: Project identifier
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
    
    Returns:
        Function result
    
    Raises:
        WorkspacePermissionError: If permission check fails
    """
    workspace_manager = get_workspace_manager(project_id)
    
    if not workspace_manager:
        # No workspace configured, execute without checks
        return await func(*args, **kwargs)
    
    # Add workspace_manager to kwargs
    kwargs['workspace_manager'] = workspace_manager
    
    return await func(*args, **kwargs)
