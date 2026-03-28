"""
Phase 1: 5-Layer Memory System - Comprehensive Test Suite

Tests all components of the 5-layer memory system:
- Layer 1: Bootstrap Injection
- Layer 2: JSONL Transcripts
- Layer 3: Session Pruning
- Layer 4: Compaction
- Layer 5: Memory Search
- Secret Redaction

Usage:
    pytest tests/test_phase1_memory.py -v
    pytest tests/test_phase1_memory.py::test_secret_redaction -v
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────────────────────────────────────
# Secret Redaction Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSecretRedaction:
    """Test secret redaction middleware."""
    
    @pytest.fixture
    def redactor(self):
        from packages.shared.redaction import SecretRedactor
        return SecretRedactor()
    
    def test_redact_openai_api_key(self, redactor):
        """Test OpenAI API key redaction."""
        text = "My API key is sk-abc123def456ghi789jkl012mno345pqr"
        redacted, count = redactor.redact(text)
        
        assert count == 1
        assert "sk-" not in redacted
        assert "[REDACTED_OPENAI_API_KEY]" in redacted
    
    def test_redact_google_api_key(self, redactor):
        """Test Google API key redaction."""
        text = "Use AIzaSyDaGmWKa4JsXZ5HWzB5q3gQeYgT9jKLMnO for testing"
        redacted, count = redactor.redact(text)
        
        assert count == 1
        assert "AIza" not in redacted
        assert "[REDACTED_GOOGLE_API_KEY]" in redacted
    
    def test_redact_github_token(self, redactor):
        """Test GitHub token redaction."""
        text = "Token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij12"
        redacted, count = redactor.redact(text)
        
        assert count == 1
        assert "ghp_" not in redacted
        assert "[REDACTED_GITHUB_TOKEN]" in redacted
    
    def test_redact_aws_access_key(self, redactor):
        """Test AWS access key redaction."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        redacted, count = redactor.redact(text)
        
        assert count == 1
        assert "AKIA" not in redacted
        assert "[REDACTED_AWS_ACCESS_KEY]" in redacted
    
    def test_redact_password(self, redactor):
        """Test password redaction."""
        text = "Database password=mySecretPassword123 connection"
        redacted, count = redactor.redact(text)
        
        assert count == 1
        assert "mySecretPassword123" not in redacted
        assert "password=[REDACTED]" in redacted
    
    def test_redact_private_key(self, redactor):
        """Test private key redaction."""
        text = """
        -----BEGIN RSA PRIVATE KEY-----
        MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy
        -----END RSA PRIVATE KEY-----
        """
        redacted, count = redactor.redact(text)
        
        assert count == 1
        assert "BEGIN RSA PRIVATE KEY" not in redacted
        assert "[REDACTED_PRIVATE_KEY]" in redacted
    
    def test_redact_bearer_token(self, redactor):
        """Test JWT bearer token redaction."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        redacted, count = redactor.redact(text)
        
        assert count == 1
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        assert "Bearer [REDACTED_JWT]" in redacted
    
    def test_redact_tool_result(self, redactor):
        """Test tool result redaction."""
        tool_result = {
            "tool_name": "exec",
            "success": True,
            "output": "API Key: sk-abc123def456ghi789jkl012mno345pqr",
            "args": {
                "command": "ls -la",
                "password": "secret123"
            }
        }
        
        redacted = redactor.redact_tool_result(tool_result)
        
        assert "[REDACTED_OPENAI_API_KEY]" in redacted["output"]
        assert redacted["args"]["password"] == "[REDACTED]"
        assert "_redaction_metadata" in redacted
        assert redacted["_redaction_metadata"]["redacted_count"] == 2
    
    def test_no_redaction_needed(self, redactor):
        """Test text without secrets."""
        text = "Hello, this is a normal message without secrets."
        redacted, count = redactor.redact(text)
        
        assert count == 0
        assert redacted == text
    
    def test_multiple_secrets(self, redactor):
        """Test multiple secrets in one text."""
        text = """
        API Key: sk-abc123def456ghi789jkl012mno345pqr
        AWS: AKIAIOSFODNN7EXAMPLE
        Password: mysecret123
        """
        redacted, count = redactor.redact(text)
        
        assert count >= 3
        assert "sk-" not in redacted
        assert "AKIA" not in redacted
        assert "mysecret123" not in redacted


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap File Manager Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBootstrapManager:
    """Test bootstrap file manager (Layer 1)."""
    
    @pytest.fixture
    def temp_bootstrap_dir(self, tmp_path):
        """Create temporary bootstrap directory with test files."""
        # Create test bootstrap files
        files = {
            "AGENTS.md": "# Agents\nTest agent instructions",
            "SOUL.md": "# Soul\nTest persona",
            "USER.md": "# User\nTest user profile",
            "IDENTITY.md": "# Identity\nTest agent identity",
            "TOOLS.md": "# Tools\nTest tool definitions",
            "HEARTBEAT.md": "# Heartbeat\nTest checklist",
            "MEMORY.md": "# Memory\nTest long-term memory",
        }
        
        for filename, content in files.items():
            (tmp_path / filename).write_text(content)
        
        # Mock get_bootstrap_dir
        with patch('packages.memory.bootstrap.get_bootstrap_dir', return_value=tmp_path):
            yield tmp_path
    
    @pytest.mark.asyncio
    async def test_load_all_bootstrap_files(self, temp_bootstrap_dir):
        """Test loading all bootstrap files."""
        from packages.memory.bootstrap import load_bootstrap_files
        
        context = await load_bootstrap_files(agent_type="main")
        
        assert "## AGENTS" in context
        assert "## SOUL" in context
        assert "## USER" in context
        assert "## IDENTITY" in context
        assert "## TOOLS" in context
        assert "## HEARTBEAT" in context
        assert "## MEMORY" in context
    
    @pytest.mark.asyncio
    async def test_load_sub_agent_files(self, temp_bootstrap_dir):
        """Test loading limited bootstrap for sub-agents."""
        from packages.memory.bootstrap import load_bootstrap_files
        
        context = await load_bootstrap_files(agent_type="sub-agent")
        
        assert "## AGENTS" in context
        assert "## TOOLS" in context
        assert "## SOUL" not in context
        assert "## USER" not in context
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_files(self, tmp_path):
        """Test loading when files don't exist."""
        from packages.memory.bootstrap import load_bootstrap_files
        
        with patch('packages.memory.bootstrap.get_bootstrap_dir', return_value=tmp_path):
            context = await load_bootstrap_files(agent_type="main")
        
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_truncation(self, tmp_path):
        """Test truncation when files exceed limits."""
        from packages.memory.bootstrap import MAX_TOTAL_CHARS, load_bootstrap_files
        
        # Create oversized file
        large_content = "# Large\n" + "x" * (MAX_TOTAL_CHARS + 1000)
        (tmp_path / "AGENTS.md").write_text(large_content)
        
        with patch('packages.memory.bootstrap.get_bootstrap_dir', return_value=tmp_path):
            context = await load_bootstrap_files(agent_type="main")
        
        assert len(context) <= MAX_TOTAL_CHARS + 500  # Some buffer for headers
        assert "[... content truncated" in context


# ─────────────────────────────────────────────────────────────────────────────
# JSONL Transcript Store Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestJSONLStore:
    """Test JSONL transcript store (Layer 2)."""
    
    @pytest.fixture
    def temp_sessions_dir(self, tmp_path):
        """Create temporary sessions directory."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        
        with patch('packages.memory.jsonl_store.get_sessions_dir', return_value=sessions_dir):
            yield sessions_dir
    
    @pytest.mark.asyncio
    async def test_append_and_load_entry(self, temp_sessions_dir):
        """Test appending and loading entries."""
        from packages.memory.jsonl_store import JSONLEntry, append_entry, load_transcript
        
        session_id = "test_session"
        entry = JSONLEntry(
            type="message",
            content={"role": "user", "content": "Hello"},
        )
        
        entry_id = await append_entry(session_id, entry)
        entries = await load_transcript(session_id)
        
        assert len(entries) == 1
        assert entries[0].id == entry_id
        assert entries[0].type == "message"
        assert entries[0].content["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_transcript(self, temp_sessions_dir):
        """Test loading nonexistent transcript."""
        from packages.memory.jsonl_store import load_transcript
        
        entries = await load_transcript("nonexistent_session")
        
        assert entries == []
    
    @pytest.mark.asyncio
    async def test_secret_redaction_in_tool_result(self, temp_sessions_dir):
        """Test that tool results are redacted before writing."""
        from packages.memory.jsonl_store import JSONLEntry, append_entry, load_transcript
        
        session_id = "test_session_redact"
        entry = JSONLEntry(
            type="toolResult",
            content={
                "tool_name": "exec",
                "output": "API Key: sk-abc123def456ghi789jkl012mno345pqr",
            },
        )
        
        await append_entry(session_id, entry)
        entries = await load_transcript(session_id)
        
        assert len(entries) == 1
        assert "[REDACTED_OPENAI_API_KEY]" in entries[0].content["output"]
        assert "sk-" not in entries[0].content["output"]
    
    @pytest.mark.asyncio
    async def test_get_session_stats(self, temp_sessions_dir):
        """Test getting session statistics."""
        from packages.memory.jsonl_store import JSONLEntry, append_entry, get_session_stats
        
        session_id = "test_session_stats"
        
        # Add multiple entries
        await append_entry(session_id, JSONLEntry(type="message", content={"role": "user", "content": "Hello"}))
        await append_entry(session_id, JSONLEntry(type="message", content={"role": "assistant", "content": "Hi"}))
        await append_entry(session_id, JSONLEntry(type="toolResult", content={"tool_name": "exec"}))
        
        stats = await get_session_stats(session_id)
        
        assert stats.total_entries == 3
        assert stats.message_count == 2
        assert stats.tool_result_count == 1
    
    @pytest.mark.asyncio
    async def test_delete_transcript(self, temp_sessions_dir):
        """Test deleting transcript."""
        from packages.memory.jsonl_store import JSONLEntry, append_entry, delete_transcript
        
        session_id = "test_session_delete"
        await append_entry(session_id, JSONLEntry(type="message", content={"role": "user", "content": "Hello"}))
        
        deleted = await delete_transcript(session_id)
        
        assert deleted is True
        
        # Verify file is gone
        deleted_again = await delete_transcript(session_id)
        assert deleted_again is False


# ─────────────────────────────────────────────────────────────────────────────
# Session Pruning Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionPruning:
    """Test session pruning (Layer 3)."""
    
    @pytest.mark.asyncio
    async def test_prune_old_tool_results(self):
        """Test pruning old tool results."""
        from packages.memory.pruning import prune_messages
        
        now = datetime.now()
        old_time = (now - timedelta(minutes=10)).isoformat()
        recent_time = (now - timedelta(minutes=1)).isoformat()
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "tool", "content": "Old result", "_timestamp": old_time},
            {"role": "assistant", "content": "Response"},
            {"role": "tool", "content": "Recent result", "_timestamp": recent_time},
        ]
        
        pruned = await prune_messages(messages, ttl_seconds=300)
        
        # Old tool result should be pruned, recent should remain
        assert len(pruned) == 4
        assert pruned[1]["content"] == "[Old tool result content cleared]"
        assert pruned[3]["content"] == "Recent result"
    
    @pytest.mark.asyncio
    async def test_protect_last_messages(self):
        """Test protecting last N messages."""
        from packages.memory.pruning import prune_messages
        
        old_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        
        messages = [
            {"role": "user", "content": "Msg 1"},
            {"role": "tool", "content": "Old", "_timestamp": old_time},
            {"role": "user", "content": "Msg 2"},
            {"role": "user", "content": "Msg 3"},  # Protected
        ]
        
        pruned = await prune_messages(messages, ttl_seconds=300, protect_last_n=3)
        
        # Last 3 messages should be protected
        assert len(pruned) == 4
        assert pruned[1]["content"] == "[Old tool result content cleared]"
    
    @pytest.mark.asyncio
    async def test_apply_token_limit(self):
        """Test applying token limit."""
        from packages.memory.pruning import prune_messages
        
        # Create many messages
        messages = [
            {"role": "user", "content": f"Message {i}" * 100}
            for i in range(20)
        ]
        
        pruned = await prune_messages(messages, max_tokens=500)
        
        # Should be pruned to fit token limit
        assert len(pruned) < 20
    
    @pytest.mark.asyncio
    async def test_soft_trim(self):
        """Test soft trim."""
        from packages.memory.pruning import soft_trim
        
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(100)]
        
        trimmed = await soft_trim(messages, threshold_ratio=0.5, max_tokens=1000)
        
        # Should keep head + tail with trim marker
        assert len(trimmed) < 100
        assert any("omitted for brevity" in str(m.get("content", "")) for m in trimmed)


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests (Require Docker)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.getenv("TEST_INTEGRATION"),
    reason="Integration tests require Docker and are slow"
)
class TestIntegration:
    """Integration tests for 5-layer memory system."""
    
    @pytest.mark.asyncio
    async def test_full_context_assembly(self):
        """Test full context assembly with all layers."""
        from packages.memory.memory_service import build_context
        
        # This requires Qdrant and Mem0 to be running
        context = await build_context(
            user_message="What is my name?",
            user_id="test_user",
        )
        
        # Should return some context (even if empty structure)
        assert isinstance(context, str)
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test full session lifecycle."""
        from packages.memory.session_manager import SessionManager
        
        async with SessionManager(user_id="test_user", session_type="isolated") as session:
            # Add messages
            await session.add_message("user", "Hello")
            await session.add_message("assistant", "Hi there!")
            
            # Get stats
            stats = await session.get_stats()
            
            assert stats.total_entries >= 2
            assert stats.message_count >= 2


# ─────────────────────────────────────────────────────────────────────────────
# Performance Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.getenv("TEST_PERFORMANCE"),
    reason="Performance tests are slow"
)
class TestPerformance:
    """Performance tests for 5-layer memory system."""
    
    @pytest.mark.asyncio
    async def test_bootstrap_load_performance(self, tmp_path):
        """Test bootstrap load performance."""
        import time
        from packages.memory.bootstrap import load_bootstrap_files
        
        # Create test files
        for filename in ["AGENTS.md", "SOUL.md", "USER.md"]:
            (tmp_path / filename).write_text("# Test\n" + "x" * 10000)
        
        with patch('packages.memory.bootstrap.get_bootstrap_dir', return_value=tmp_path):
            start = time.time()
            await load_bootstrap_files(agent_type="main")
            elapsed = time.time() - start
        
        # Should load in <100ms
        assert elapsed < 0.1
    
    @pytest.mark.asyncio
    async def test_jsonl_append_performance(self, temp_sessions_dir):
        """Test JSONL append performance."""
        import time
        from packages.memory.jsonl_store import JSONLEntry, append_entry
        
        session_id = "perf_test"
        
        # Append 100 entries
        start = time.time()
        for i in range(100):
            await append_entry(
                session_id,
                JSONLEntry(type="message", content={"role": "user", "content": f"Message {i}"}),
            )
        elapsed = time.time() - start
        
        # Should append 100 entries in <1 second
        assert elapsed < 1.0
        assert elapsed / 100 < 0.01  # <10ms per append


# ─────────────────────────────────────────────────────────────────────────────
# Test Runners
# ─────────────────────────────────────────────────────────────────────────────

def run_unit_tests():
    """Run unit tests only."""
    pytest.main([__file__, "-v", "-k", "not integration and not performance"])

def run_all_tests():
    """Run all tests including integration tests."""
    os.environ["TEST_INTEGRATION"] = "1"
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    print("="*70)
    print("Phase 1: 5-Layer Memory System - Test Suite")
    print("="*70)
    print("\nRunning unit tests...\n")
    
    run_unit_tests()
    
    print("\n" + "="*70)
    print("Unit tests complete!")
    print("="*70)
    print("\nTo run integration tests (requires Docker):")
    print("  TEST_INTEGRATION=1 pytest tests/test_phase1_memory.py -v")
    print("\nTo run performance tests:")
    print("  TEST_PERFORMANCE=1 pytest tests/test_phase1_memory.py -v")
