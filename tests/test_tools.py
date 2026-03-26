"""
Unit tests for local operations tools: fs.py, repo.py, exec.py.

These tests verify the safety mechanisms and basic functionality
of the new tool modules.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

# ── Helper ───────────────────────────────────────────────────────────

def run_async(coro):
    """Run an async function synchronously for test compatibility."""
    return asyncio.run(coro)


# ========================================================================
# File System Tools (packages/tools/fs.py)
# ========================================================================

class TestFsTools:
    """Tests for packages.tools.fs"""

    def test_read_file_success(self, tmp_path):
        """Read a simple text file."""
        from packages.tools.fs import read_file

        test_file = tmp_path / "hello.txt"
        test_file.write_text("line 1\nline 2\nline 3")

        result = run_async(read_file(str(test_file)))
        assert "error" not in result
        assert result["content"] == "line 1\nline 2\nline 3"
        assert result["line_count"] == 3
        assert result["truncated"] is False

    def test_read_file_with_max_lines(self, tmp_path):
        """Read a file but truncate to max_lines."""
        from packages.tools.fs import read_file

        test_file = tmp_path / "long.txt"
        test_file.write_text("\n".join(f"line {i}" for i in range(100)))

        result = run_async(read_file(str(test_file), max_lines=5))
        assert result["line_count"] == 5
        assert result["truncated"] is True

    def test_read_file_not_found(self):
        """Return error for non-existent file."""
        from packages.tools.fs import read_file

        result = run_async(read_file("C:\\nonexistent\\fake.txt"))
        assert "error" in result

    def test_write_file_success(self, tmp_path):
        """Write a new file."""
        from packages.tools.fs import write_file

        target = tmp_path / "output.txt"
        result = run_async(write_file(str(target), "hello world"))
        assert "error" not in result
        assert result["created"] is True
        assert target.read_text() == "hello world"

    def test_write_file_protected_path(self):
        """Block writes to protected system directories."""
        from packages.tools.fs import write_file

        result = run_async(write_file("C:\\Windows\\test.txt", "nope"))
        assert "error" in result
        assert "protected" in result["error"].lower()

    def test_find_files(self, tmp_path):
        """Find files matching a pattern."""
        from packages.tools.fs import find_files

        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.py").write_text("pass")
        (tmp_path / "c.txt").write_text("hello")

        result = run_async(find_files(str(tmp_path), pattern="*.py"))
        assert "error" not in result
        assert result["total_found"] == 2

    def test_list_directory(self, tmp_path):
        """List directory contents."""
        from packages.tools.fs import list_directory

        (tmp_path / "file.txt").write_text("data")
        (tmp_path / "subdir").mkdir()

        result = run_async(list_directory(str(tmp_path)))
        assert "error" not in result
        assert result["total_items"] == 2
        names = {item["name"] for item in result["items"]}
        assert "file.txt" in names
        assert "subdir" in names

    def test_file_info(self, tmp_path):
        """Get metadata for a file."""
        from packages.tools.fs import file_info

        target = tmp_path / "info.txt"
        target.write_text("test content")

        result = run_async(file_info(str(target)))
        assert "error" not in result
        assert result["type"] == "file"
        assert result["extension"] == ".txt"
        assert result["size_bytes"] > 0


# ========================================================================
# Repository Tools (packages/tools/repo.py)
# ========================================================================

class TestRepoTools:
    """Tests for packages.tools.repo"""

    def test_not_a_git_repo(self, tmp_path):
        """Return error for non-git directory."""
        from packages.tools.repo import git_status

        result = run_async(git_status(str(tmp_path)))
        assert "error" in result

    def test_git_status_on_real_repo(self):
        """Test git status on the PersonalAssist repo itself."""
        from packages.tools.repo import git_status

        repo = str(Path(__file__).resolve().parent.parent)
        result = run_async(git_status(repo))
        assert "error" not in result
        assert "branch" in result

    def test_git_log_on_real_repo(self):
        """Test git log on the PersonalAssist repo."""
        from packages.tools.repo import git_log

        repo = str(Path(__file__).resolve().parent.parent)
        result = run_async(git_log(repo, max_commits=3))
        assert "error" not in result
        assert len(result["commits"]) <= 3

    def test_repo_summary_on_real_repo(self):
        """Test repo summary on the PersonalAssist repo."""
        from packages.tools.repo import repo_summary

        repo = str(Path(__file__).resolve().parent.parent)
        result = run_async(repo_summary(repo))
        assert "error" not in result
        assert "status" in result
        assert "recent_commits" in result
        assert "branches" in result


# ========================================================================
# Execution Tools (packages/tools/exec.py)
# ========================================================================

class TestExecTools:
    """Tests for packages.tools.exec"""

    def test_allowed_command(self):
        """Pre-approved commands should be allowed."""
        from packages.tools.exec import check_allowlist

        result = check_allowlist("git status")
        assert result["allowed"] is True
        assert result["blocked"] is False

    def test_blocked_command(self):
        """Dangerous commands should be blocked."""
        from packages.tools.exec import check_allowlist

        result = check_allowlist("rm -rf /")
        assert result["blocked"] is True
        assert result["allowed"] is False

    def test_requires_approval(self):
        """Unknown commands should require approval."""
        from packages.tools.exec import check_allowlist

        result = check_allowlist("curl http://example.com")
        assert result["requires_approval"] is True
        assert result["allowed"] is False
        assert result["blocked"] is False

    def test_run_allowed_command(self):
        """Execute a pre-approved command."""
        from packages.tools.exec import run_command

        result = run_async(run_command("whoami"))
        assert result["success"] is True
        assert len(result["stdout"]) > 0

    def test_run_unapproved_returns_pending(self):
        """Unapproved commands should return pending_approval."""
        from packages.tools.exec import run_command

        result = run_async(run_command("some_random_command"))
        assert result.get("status") == "pending_approval"
        assert result["success"] is False

    def test_run_blocked_returns_error(self):
        """Blocked commands should return error."""
        from packages.tools.exec import run_command

        result = run_async(run_command("rm -rf /"))
        assert result.get("blocked") is True
        assert result["success"] is False

    def test_force_approve_bypasses_check(self):
        """Force-approved commands bypass the allowlist."""
        from packages.tools.exec import run_command

        result = run_async(run_command("echo hello_test", force_approve=True))
        assert result["success"] is True
        assert "hello_test" in result["stdout"]


class TestAgentToolRegistry:
    def test_build_native_tool_schemas_read_only(self):
        from packages.agents.tools import build_native_tool_schemas

        schemas = build_native_tool_schemas(
            allow_exec_tools=False,
            allow_mutating_tools=False,
        )
        names = {s.get("function", {}).get("name") for s in schemas}
        assert "read_file" in names
        assert "search_documents" in names
        assert "write_file" not in names
        assert "exec_command" not in names

    def test_build_native_tool_schemas_with_mutations(self):
        from packages.agents.tools import build_native_tool_schemas

        schemas = build_native_tool_schemas(
            allow_exec_tools=True,
            allow_mutating_tools=True,
        )
        names = {s.get("function", {}).get("name") for s in schemas}
        assert "write_file" in names
        assert "exec_command" in names

    def test_execute_registered_tool_rejects_bad_args(self):
        from packages.agents.tools import execute_registered_tool

        result = run_async(
            execute_registered_tool(
                "read_file",
                {"not_path": "abc"},
                allow_exec_tools=False,
                allow_mutating_tools=False,
            )
        )
        assert result["success"] is False
        assert "Missing required argument" in result["error"]

    def test_execute_registered_tool_unknown(self):
        from packages.agents.tools import execute_registered_tool

        result = run_async(
            execute_registered_tool(
                "nonexistent_tool",
                {},
                allow_exec_tools=False,
                allow_mutating_tools=False,
            )
        )
        assert result["success"] is False
        assert "not allowed or not found" in result["error"]
