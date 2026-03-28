"""
Workspace API Endpoints

Provides REST API for workspace management:
- Create/update/list workspaces
- Get audit logs
- Check permissions
- Run agents with workspace support

Usage:
    from apps.api.workspace_router import router
    
    app.include_router(router)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ── Request/Response Models ──────────────────────────────────────────


class WorkspacePermissionsRequest(BaseModel):
    """Request model for workspace permissions."""
    
    read: list[str] = Field(default=["**/*"], description="Read path patterns")
    write: list[str] = Field(default=[], description="Write path patterns")
    execute: bool = Field(default=False, description="Allow command execution")
    git_operations: bool = Field(default=True, description="Allow Git operations")
    network_access: bool = Field(default=False, description="Allow network access")


class WorkspaceCreateRequest(BaseModel):
    """Request model for creating a workspace."""
    
    project_id: str = Field(..., description="Unique project identifier")
    root: str = Field(..., description="Root directory path")
    permissions: WorkspacePermissionsRequest
    context_collection: str = Field(default="", description="Qdrant collection name")
    agent_instructions: str = Field(default="", description="Custom agent instructions")


class WorkspaceUpdateRequest(BaseModel):
    """Request model for updating a workspace."""
    
    permissions: Optional[WorkspacePermissionsRequest] = None
    context_collection: Optional[str] = None
    agent_instructions: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Response model for workspace information."""
    
    project_id: str
    root: str
    permissions: dict[str, Any]
    context_collection: str
    agent_instructions: str
    created_at: str
    updated_at: str


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    
    timestamp: str
    action: str
    target: str
    allowed: bool
    reason: str


class AuditLogResponse(BaseModel):
    """Response model for audit log."""
    
    entries: list[AuditLogEntry]
    total: int
    limit: int


class PermissionCheckRequest(BaseModel):
    """Request model for permission check."""
    
    path: str
    action: str = Field(..., description="Action: read, write, or execute")


class PermissionCheckResponse(BaseModel):
    """Response model for permission check."""
    
    allowed: bool
    reason: str


# ── Helper Functions ─────────────────────────────────────────────────


def _get_workspace_manager():
    """Lazy import of workspace manager."""
    from packages.agents.workspace import WorkspaceManager, WorkspaceConfig, WorkspacePermissions
    
    return WorkspaceManager, WorkspaceConfig, WorkspacePermissions


# ── API Endpoints ────────────────────────────────────────────────────


@router.post("/create", response_model=WorkspaceResponse)
async def create_workspace(req: WorkspaceCreateRequest):
    """
    Create a new workspace configuration.
    
    Args:
        req: Workspace creation request
    
    Returns:
        Created workspace configuration
    """
    from packages.agents.workspace import (
        WorkspaceConfig,
        WorkspacePermissions,
        save_workspace_config,
    )
    
    try:
        # Create config
        permissions = WorkspacePermissions(**req.permissions.model_dump())
        config = WorkspaceConfig(
            project_id=req.project_id,
            root=Path(req.root),
            permissions=permissions,
            context_collection=req.context_collection,
            agent_instructions=req.agent_instructions,
        )
        
        # Save config
        config_path = save_workspace_config(config)
        
        logger.info(f"Created workspace: {config_path}")
        
        return WorkspaceResponse(
            project_id=config.project_id,
            root=str(config.root),
            permissions=config.permissions.model_dump(),
            context_collection=config.context_collection,
            agent_instructions=config.agent_instructions,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
    
    except Exception as exc:
        logger.error(f"Failed to create workspace: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/list", response_model=list[WorkspaceResponse])
async def list_workspaces():
    """
    List all workspace configurations.
    
    Returns:
        List of workspace configurations
    """
    from packages.agents.workspace import list_workspace_configs
    
    try:
        configs = list_workspace_configs()
        
        return [
            WorkspaceResponse(
                project_id=config.project_id,
                root=str(config.root),
                permissions=config.permissions.model_dump(),
                context_collection=config.context_collection,
                agent_instructions=config.agent_instructions,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
            for config in configs
        ]
    
    except Exception as exc:
        logger.error(f"Failed to list workspaces: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}", response_model=WorkspaceResponse)
async def get_workspace(project_id: str):
    """
    Get workspace configuration by project ID.
    
    Args:
        project_id: Project identifier
    
    Returns:
        Workspace configuration
    """
    from packages.agents.workspace import load_workspace_config
    
    try:
        config = load_workspace_config(project_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        return WorkspaceResponse(
            project_id=config.project_id,
            root=str(config.root),
            permissions=config.permissions.model_dump(),
            context_collection=config.context_collection,
            agent_instructions=config.agent_instructions,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get workspace: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{project_id}", response_model=WorkspaceResponse)
async def update_workspace(project_id: str, req: WorkspaceUpdateRequest):
    """
    Update workspace configuration.
    
    Args:
        project_id: Project identifier
        req: Update request
    
    Returns:
        Updated workspace configuration
    """
    from packages.agents.workspace import load_workspace_config, save_workspace_config
    
    try:
        config = load_workspace_config(project_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Apply updates
        if req.permissions:
            from packages.agents.workspace import WorkspacePermissions
            config.permissions = WorkspacePermissions(**req.permissions.model_dump())
        
        if req.context_collection is not None:
            config.context_collection = req.context_collection
        
        if req.agent_instructions is not None:
            config.agent_instructions = req.agent_instructions
        
        # Save updated config
        save_workspace_config(config)
        
        logger.info(f"Updated workspace: {project_id}")
        
        return WorkspaceResponse(
            project_id=config.project_id,
            root=str(config.root),
            permissions=config.permissions.model_dump(),
            context_collection=config.context_collection,
            agent_instructions=config.agent_instructions,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update workspace: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{project_id}")
async def delete_workspace(project_id: str):
    """
    Delete workspace configuration.
    
    Args:
        project_id: Project identifier
    """
    from packages.agents.workspace import get_workspace_dir
    
    try:
        workspace_dir = get_workspace_dir()
        config_file = workspace_dir / f"{project_id}.json"
        
        if not config_file.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        config_file.unlink()
        
        logger.info(f"Deleted workspace: {project_id}")
        
        return {"status": "deleted", "project_id": project_id}
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to delete workspace: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}/audit", response_model=AuditLogResponse)
async def get_workspace_audit_log(
    project_id: str,
    limit: int = 100,
):
    """
    Get audit log for a workspace.
    
    Args:
        project_id: Project identifier
        limit: Maximum number of entries to return
    
    Returns:
        Audit log entries
    """
    from packages.agents.workspace import WorkspaceManager, WorkspaceConfig, WorkspacePermissions
    
    try:
        # Load config
        from packages.agents.workspace import load_workspace_config
        config = load_workspace_config(project_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Get audit log
        manager = WorkspaceManager(config)
        entries = manager.get_audit_log(limit=limit)
        
        return AuditLogResponse(
            entries=[AuditLogEntry(**entry) for entry in entries],
            total=len(entries),
            limit=limit,
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get audit log: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{project_id}/check-permission", response_model=PermissionCheckResponse)
async def check_permission(project_id: str, req: PermissionCheckRequest):
    """
    Check if an action is allowed for a workspace.
    
    Args:
        project_id: Project identifier
        req: Permission check request
    
    Returns:
        Permission check result
    """
    from packages.agents.workspace import WorkspaceManager
    
    try:
        # Load config
        from packages.agents.workspace import load_workspace_config
        config = load_workspace_config(project_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Check permission
        manager = WorkspaceManager(config)
        
        if req.action == "read":
            allowed, reason = manager.can_read(Path(req.path))
        elif req.action == "write":
            allowed, reason = manager.can_write(Path(req.path))
        elif req.action == "execute":
            allowed, reason = manager.can_execute(req.path)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
        
        return PermissionCheckResponse(allowed=allowed, reason=reason)
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to check permission: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}/stats")
async def get_workspace_stats(project_id: str):
    """
    Get workspace statistics.
    
    Args:
        project_id: Project identifier
    
    Returns:
        Workspace statistics
    """
    from packages.agents.workspace import WorkspaceManager
    
    try:
        # Load config
        from packages.agents.workspace import load_workspace_config
        config = load_workspace_config(project_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Get stats
        manager = WorkspaceManager(config)
        stats = manager.get_stats()
        
        return stats
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get workspace stats: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
