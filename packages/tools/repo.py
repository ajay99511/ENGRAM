"""
Repository Analysis Tools — git integration for agent-driven code insights.

Provides lightweight wrappers around git CLI commands to let agents
understand project history, diffs, and branch status.

Usage:
    from packages.tools.repo import git_status, git_log, git_diff, repo_summary
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────

# Timeout for git commands (seconds)
GIT_TIMEOUT = 15

# Max output size from git commands (256 KB)
MAX_OUTPUT_SIZE = 256 * 1024


# ── Internal Helpers ─────────────────────────────────────────────────


async def _run_git(
    args: list[str],
    cwd: str,
    timeout: int = GIT_TIMEOUT,
) -> dict[str, Any]:
    """
    Run a git command and return its output.

    Returns dict with 'stdout', 'stderr', 'returncode', 'success'.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        out = stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
        err = stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]

        return {
            "stdout": out,
            "stderr": err,
            "returncode": proc.returncode,
            "success": proc.returncode == 0,
        }
    except asyncio.TimeoutError:
        return {"error": f"Git command timed out after {timeout}s", "success": False}
    except FileNotFoundError:
        return {"error": "Git is not installed or not in PATH", "success": False}
    except Exception as exc:
        return {"error": f"Git command failed: {exc}", "success": False}


def _is_git_repo(path: str) -> bool:
    """Check if a directory is a git repository."""
    return (Path(path) / ".git").exists()


# ── Public API ───────────────────────────────────────────────────────


async def git_status(repo_path: str) -> dict[str, Any]:
    """
    Get the working tree status of a git repository.

    Returns:
        Dict with 'branch', 'modified', 'staged', 'untracked' file lists.
    """
    if not _is_git_repo(repo_path):
        return {"error": f"Not a git repository: {repo_path}"}

    # Get branch name
    branch_result = await _run_git(
        ["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path
    )
    branch = branch_result["stdout"].strip() if branch_result.get("success") else "unknown"

    # Get porcelain status
    status_result = await _run_git(
        ["status", "--porcelain", "--branch"], cwd=repo_path
    )
    if not status_result.get("success"):
        return {"error": status_result.get("error", "git status failed")}

    modified, staged, untracked = [], [], []
    for line in status_result["stdout"].splitlines():
        if line.startswith("##"):
            continue
        if len(line) < 4:
            continue
        index_status = line[0]
        work_status = line[1]
        filename = line[3:]

        if index_status != " " and index_status != "?":
            staged.append(filename)
        if work_status == "M":
            modified.append(filename)
        elif work_status == "?" or index_status == "?":
            untracked.append(filename)

    return {
        "repo_path": repo_path,
        "branch": branch,
        "modified": modified,
        "staged": staged,
        "untracked": untracked,
        "clean": len(modified) == 0 and len(staged) == 0 and len(untracked) == 0,
    }


async def git_log(
    repo_path: str,
    max_commits: int = 10,
    oneline: bool = True,
) -> dict[str, Any]:
    """
    Get recent commit history.

    Args:
        repo_path:   Path to the git repository.
        max_commits: Maximum number of commits to return.
        oneline:     Whether to use compact one-line format.

    Returns:
        Dict with 'commits' list and 'branch'.
    """
    if not _is_git_repo(repo_path):
        return {"error": f"Not a git repository: {repo_path}"}

    fmt = "--oneline" if oneline else "--format=%H|%an|%ad|%s"
    result = await _run_git(
        ["log", fmt, f"-n{max_commits}", "--date=short"], cwd=repo_path
    )
    if not result.get("success"):
        return {"error": result.get("error", "git log failed")}

    commits = []
    for line in result["stdout"].strip().splitlines():
        if oneline:
            parts = line.split(" ", 1)
            commits.append({
                "hash": parts[0],
                "message": parts[1] if len(parts) > 1 else "",
            })
        else:
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                })

    return {
        "repo_path": repo_path,
        "commits": commits,
        "count": len(commits),
    }


async def git_diff(
    repo_path: str,
    staged: bool = False,
    file_path: str | None = None,
) -> dict[str, Any]:
    """
    Get the diff of changes in the working tree or staging area.

    Args:
        repo_path: Path to the git repository.
        staged:    If True, show staged (index) changes.
        file_path: Optional specific file to diff.

    Returns:
        Dict with 'diff' text, 'files_changed' count.
    """
    if not _is_git_repo(repo_path):
        return {"error": f"Not a git repository: {repo_path}"}

    args = ["diff"]
    if staged:
        args.append("--cached")
    args.append("--stat")
    if file_path:
        args.extend(["--", file_path])

    stat_result = await _run_git(args, cwd=repo_path)

    # Also get the full diff (capped)
    full_args = ["diff"]
    if staged:
        full_args.append("--cached")
    if file_path:
        full_args.extend(["--", file_path])

    diff_result = await _run_git(full_args, cwd=repo_path)

    return {
        "repo_path": repo_path,
        "staged": staged,
        "stat": stat_result.get("stdout", "") if stat_result.get("success") else "",
        "diff": diff_result.get("stdout", "")[:MAX_OUTPUT_SIZE] if diff_result.get("success") else "",
        "files_changed": len([
            l for l in stat_result.get("stdout", "").splitlines()
            if "|" in l
        ]) if stat_result.get("success") else 0,
    }


async def git_branches(repo_path: str) -> dict[str, Any]:
    """
    List all branches and identify the current one.

    Returns:
        Dict with 'current', 'local' list, 'remote' list.
    """
    if not _is_git_repo(repo_path):
        return {"error": f"Not a git repository: {repo_path}"}

    result = await _run_git(["branch", "-a", "--no-color"], cwd=repo_path)
    if not result.get("success"):
        return {"error": result.get("error", "git branch failed")}

    current = ""
    local, remote = [], []

    for line in result["stdout"].splitlines():
        line = line.strip()
        if line.startswith("* "):
            current = line[2:]
            local.append(current)
        elif line.startswith("remotes/"):
            remote.append(line.replace("remotes/", "", 1))
        elif line:
            local.append(line)

    return {
        "repo_path": repo_path,
        "current": current,
        "local": local,
        "remote": remote,
    }


async def repo_summary(repo_path: str) -> dict[str, Any]:
    """
    Generate a high-level summary of a git repository.

    Combines status, recent commits, and branch info for a quick overview.

    Returns:
        Dict with 'status', 'recent_commits', 'branches'.
    """
    if not _is_git_repo(repo_path):
        return {"error": f"Not a git repository: {repo_path}"}

    status, log, branches = await asyncio.gather(
        git_status(repo_path),
        git_log(repo_path, max_commits=5),
        git_branches(repo_path),
    )

    return {
        "repo_path": repo_path,
        "status": status,
        "recent_commits": log.get("commits", []),
        "branches": branches,
    }
