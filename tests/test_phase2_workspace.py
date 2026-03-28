"""
Phase 2: Workspace Isolation - Test Suite

Tests all components of the workspace isolation system:
- Workspace Manager
- A2A Registry
- Tier 1 Agent Cards
- Tool Integration
- API Endpoints

Usage:
    pytest tests/test_phase2_workspace.py -v
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────────────────────────────
# Workspace Manager Tests
# ─────────────────────────────────────────────────────────────────────

class TestWorkspaceManager:
    """Test workspace manager permission checks."""
    
    @pytest.fixture
    def temp_workspace_config(self, tmp_path):
        """Create temporary workspace config."""
        from packages.agents.workspace import WorkspaceConfig, WorkspacePermissions
        
        config = WorkspaceConfig(
            project_id="test-project",
            root=tmp_path,
            permissions=WorkspacePermissions(
                read=["src/**/*", "tests/**/*"],
                write=["src/**/*"],
                execute=False,
                git_operations=True,
                network_access=False,
            ),
            context_collection="test_project",
        )
        
        # Create test directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        
        return config
    
    def test_workspace_creation(self, temp_workspace_config):
        """Test workspace config creation."""
        assert temp_workspace_config.project_id == "test-project"
        assert temp_workspace_config.root.exists()
        assert len(temp_workspace_config.permissions.read) == 2
    
    def test_can_read_allowed_path(self, temp_workspace_config):
        """Test reading from allowed path."""
        from packages.agents.workspace import WorkspaceManager
        
        manager = WorkspaceManager(temp_workspace_config)
        path = temp_workspace_config.root / "src" / "main.py"
        
        allowed, reason = manager.can_read(path)
        
        assert allowed is True
        assert "allowlist" in reason.lower()
    
    def test_can_read_outside_root(self, temp_workspace_config):
        """Test reading from outside workspace root."""
        from packages.agents.workspace import WorkspaceManager
        
        manager = WorkspaceManager(temp_workspace_config)
        path = Path("C:\\Windows\\System32\\config")
        
        allowed, reason = manager.can_read(path)
        
        assert allowed is False
        assert "dangerous" in reason.lower() or "outside" in reason.lower()
    
    def test_can_write_allowed_path(self, temp_workspace_config):
        """Test writing to allowed path."""
        from packages.agents.workspace import WorkspaceManager
        
        manager = WorkspaceManager(temp_workspace_config)
        path = temp_workspace_config.root / "src" / "new_file.py"
        
        allowed, reason = manager.can_write(path)
        
        assert allowed is True
    
    def test_can_write_denied_path(self, temp_workspace_config):
        """Test writing to denied path."""
        from packages.agents.workspace import WorkspaceManager
        
        manager = WorkspaceManager(temp_workspace_config)
        path = temp_workspace_config.root / "tests" / "test_file.py"
        
        allowed, reason = manager.can_write(path)
        
        # Tests dir is in read but not write
        assert allowed is False
    
    def test_can_execute_disabled(self, temp_workspace_config):
        """Test execute when disabled."""
        from packages.agents.workspace import WorkspaceManager
        
        manager = WorkspaceManager(temp_workspace_config)
        
        allowed, reason = manager.can_execute("pip list")
        
        assert allowed is False
        assert "not allowed" in reason.lower()
    
    def test_audit_logging(self, temp_workspace_config, tmp_path):
        """Test audit logging."""
        from packages.agents.workspace import WorkspaceManager
        
        manager = WorkspaceManager(temp_workspace_config)
        path = temp_workspace_config.root / "src" / "main.py"
        
        # Perform some actions
        manager.can_read(path)
        manager.can_write(path)
        
        # Check audit log
        entries = manager.get_audit_log()
        
        assert len(entries) >= 2
        assert entries[-1]["action"] == "write"
        assert entries[-1]["allowed"] is True
    
    def test_dangerous_path_blocking(self, temp_workspace_config):
        """Test dangerous path blocking."""
        from packages.agents.workspace import WorkspaceManager
        
        manager = WorkspaceManager(temp_workspace_config)
        
        # Test various dangerous patterns
        dangerous_paths = [
            Path("C:/Windows/System32"),
            Path("C:/$Recycle.Bin"),
            Path.home() / ".ssh" / "id_rsa",
            Path.home() / ".aws" / "credentials",
            Path.home() / ".env",
        ]
        
        for path in dangerous_paths:
            allowed, reason = manager.can_read(path)
            assert allowed is False, f"Failed to block dangerous path: {path}"
            assert "dangerous" in reason.lower()


# ─────────────────────────────────────────────────────────────────────
# A2A Registry Tests
# ─────────────────────────────────────────────────────────────────────

class TestA2ARegistry:
    """Test A2A registry functionality."""
    
    @pytest.fixture
    def registry(self):
        """Create fresh registry instance."""
        from packages.agents.a2a.registry import A2ARegistry
        
        # Create new instance (bypass singleton for testing)
        A2ARegistry._instance = None
        return A2ARegistry()
    
    def test_register_agent(self, registry):
        """Test agent registration."""
        from packages.agents.a2a.registry import AgentCard
        
        card = AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            capabilities=["test", "demo"],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        
        registry.register(card)
        
        assert "test-agent" in registry.agents
        assert registry.get_agent("test-agent") == card
    
    def test_discover_agents(self, registry):
        """Test agent discovery."""
        from packages.agents.a2a.registry import AgentCard
        
        # Register multiple agents
        registry.register(AgentCard(
            agent_id="agent1",
            name="Agent 1",
            description="Test",
            capabilities=["code_review", "security"],
            input_schema={},
            output_schema={},
        ))
        
        registry.register(AgentCard(
            agent_id="agent2",
            name="Agent 2",
            description="Test",
            capabilities=["test_generation"],
            input_schema={},
            output_schema={},
        ))
        
        # Discover by capability
        agents = registry.discover("code_review")
        
        assert len(agents) == 1
        assert agents[0].agent_id == "agent1"
    
    def test_list_capabilities(self, registry):
        """Test listing all capabilities."""
        from packages.agents.a2a.registry import AgentCard
        
        registry.register(AgentCard(
            agent_id="agent1",
            name="Agent 1",
            description="Test",
            capabilities=["code_review", "security"],
            input_schema={},
            output_schema={},
        ))
        
        registry.register(AgentCard(
            agent_id="agent2",
            name="Agent 2",
            description="Test",
            capabilities=["test_generation", "code_review"],
            input_schema={},
            output_schema={},
        ))
        
        capabilities = registry.list_capabilities()
        
        assert "code_review" in capabilities
        assert "security" in capabilities
        assert "test_generation" in capabilities
        assert len(capabilities) == 3
    
    @pytest.mark.asyncio
    async def test_delegate_task(self, registry):
        """Test task delegation."""
        from packages.agents.a2a.registry import AgentCard
        
        # Create handler
        async def test_handler(task, **kwargs):
            return {"result": "success", "task": task}
        
        # Register agent with handler
        card = AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            description="Test",
            capabilities=["test"],
            input_schema={},
            output_schema={},
        )
        
        registry.register(card, handler=test_handler)
        
        # Delegate task
        task_handle = await registry.delegate(
            agent_id="test-agent",
            task={"test_key": "test_value"},
        )
        
        assert task_handle.agent_id == "test-agent"
        assert task_handle.status.value == "queued"
        
        # Wait for completion
        result = await registry.wait_for_task(task_handle.task_id, timeout=5)
        
        assert result.status.value == "completed"
        assert result.result["result"] == "success"


# ─────────────────────────────────────────────────────────────────────
# Tier 1 Agent Cards Tests
# ─────────────────────────────────────────────────────────────────────

class TestTier1Agents:
    """Test Tier 1 agent card definitions."""
    
    def test_code_reviewer_card(self):
        """Test code reviewer agent card."""
        from packages.agents.a2a.agents import CODE_REVIEWER_CARD
        
        assert CODE_REVIEWER_CARD["agent_id"] == "code-reviewer"
        assert "code_review" in CODE_REVIEWER_CARD["capabilities"]
        assert "security_scan" in CODE_REVIEWER_CARD["capabilities"]
        assert CODE_REVIEWER_CARD["permissions"]["execute"] is False
    
    def test_workspace_analyzer_card(self):
        """Test workspace analyzer agent card."""
        from packages.agents.a2a.agents import WORKSPACE_ANALYZER_CARD
        
        assert WORKSPACE_ANALYZER_CARD["agent_id"] == "workspace-analyzer"
        assert "workspace_analysis" in WORKSPACE_ANALYZER_CARD["capabilities"]
        assert WORKSPACE_ANALYZER_CARD["permissions"]["read"] == ["**/*"]
    
    def test_test_generator_card(self):
        """Test test generator agent card."""
        from packages.agents.a2a.agents import TEST_GENERATOR_CARD
        
        assert TEST_GENERATOR_CARD["agent_id"] == "test-generator"
        assert "test_generation" in TEST_GENERATOR_CARD["capabilities"]
        assert "tests/**/*" in TEST_GENERATOR_CARD["permissions"]["write"]
    
    def test_dependency_auditor_card(self):
        """Test dependency auditor agent card."""
        from packages.agents.a2a.agents import DEPENDENCY_AUDITOR_CARD
        
        assert DEPENDENCY_AUDITOR_CARD["agent_id"] == "dependency-auditor"
        assert "dependency_audit" in DEPENDENCY_AUDITOR_CARD["capabilities"]
        assert "**/requirements.txt" in DEPENDENCY_AUDITOR_CARD["permissions"]["read"]


# ─────────────────────────────────────────────────────────────────────
# Integration Tests (Require API)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not __import__("os").getenv("TEST_INTEGRATION"),
    reason="Integration tests require running API"
)
class TestAPIIntegration:
    """Test API endpoint integration."""
    
    @pytest.mark.asyncio
    async def test_create_workspace_api(self):
        """Test workspace creation via API."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/workspaces/create",
                json={
                    "project_id": "test-api",
                    "root": str(Path.home()),
                    "permissions": {
                        "read": ["**/*"],
                        "write": [],
                        "execute": False,
                        "git_operations": True,
                        "network_access": False,
                    },
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["project_id"] == "test-api"
    
    @pytest.mark.asyncio
    async def test_list_workspaces_api(self):
        """Test workspace listing via API."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/workspaces/list")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_check_permission_api(self):
        """Test permission check via API."""
        import httpx
        
        # First create a workspace
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8000/workspaces/create",
                json={
                    "project_id": "test-perm",
                    "root": str(Path.home()),
                    "permissions": {
                        "read": ["src/**/*"],
                        "write": [],
                        "execute": False,
                        "git_operations": True,
                        "network_access": False,
                    },
                },
            )
            
            # Check permission
            response = await client.post(
                "http://localhost:8000/workspaces/test-perm/check-permission",
                json={
                    "path": "src/main.py",
                    "action": "read",
                },
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "allowed" in data
            assert "reason" in data


# ─────────────────────────────────────────────────────────────────────
# Test Runners
# ─────────────────────────────────────────────────────────────────────

def run_unit_tests():
    """Run unit tests only."""
    pytest.main([__file__, "-v", "-k", "not integration"])

def run_all_tests():
    """Run all tests including integration tests."""
    import os
    os.environ["TEST_INTEGRATION"] = "1"
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    print("="*70)
    print("Phase 2: Workspace Isolation - Test Suite")
    print("="*70)
    print("\nRunning unit tests...\n")
    
    run_unit_tests()
    
    print("\n" + "="*70)
    print("Unit tests complete!")
    print("="*70)
    print("\nTo run integration tests (requires running API):")
    print("  TEST_INTEGRATION=1 pytest tests/test_phase2_workspace.py -v")
