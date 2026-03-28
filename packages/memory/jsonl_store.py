"""
JSONL Transcript Store (Layer 2 of 5-Layer Memory System)

Manages append-only JSONL transcript files for session history.
Each session has its own JSONL file with tree-structured entries.

Features:
- Append-only writes (fast, crash-safe)
- Tree structure (entries have id + parentId for branching)
- Secret redaction before persistence
- Atomic writes (temp file + rename for compaction)
- Entry types: message, toolResult, compaction, session_info

File Location: ~/.personalassist/sessions/<session_id>.jsonl

Usage:
    from packages.memory.jsonl_store import append_entry, load_transcript
    
    # Append a message
    await append_entry(session_id, JSONLEntry(
        id=str(uuid.uuid4()),
        type="message",
        content={"role": "user", "content": "Hello"},
    ))
    
    # Load full transcript
    entries = await load_transcript(session_id)
"""

import json
import logging
import tempfile
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

from packages.shared.redaction import redact_tool_result

logger = logging.getLogger(__name__)


class JSONLEntry(BaseModel):
    """A single entry in a JSONL transcript."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["message", "toolResult", "compaction", "session_info", "custom"]
    parent_id: str | None = None
    content: dict
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = Field(default_factory=dict)
    
    class ConfigDict:
        extra = "allow"  # Allow additional fields for flexibility


class SessionStats(BaseModel):
    """Statistics about a session transcript."""
    
    session_id: str
    total_entries: int
    message_count: int
    tool_result_count: int
    compaction_count: int
    first_entry_at: str | None
    last_entry_at: str | None
    file_size_bytes: int
    estimated_tokens: int


def get_sessions_dir() -> Path:
    """Get the sessions directory (~/.personalassist/sessions/)."""
    sessions_dir = Path.home() / ".personalassist" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


async def append_entry(session_id: str, entry: JSONLEntry) -> str:
    """
    Append an entry to a session transcript.
    
    Args:
        session_id: Session identifier (becomes filename)
        entry: Entry to append
    
    Returns:
        Entry ID
    """
    file_path = get_sessions_dir() / f"{session_id}.jsonl"
    
    # Redact secrets from tool results
    if entry.type == "toolResult":
        entry.content = redact_tool_result(entry.content)
    
    # Append to JSONL file
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry.model_dump(), ensure_ascii=False) + '\n')
        
        logger.debug(f"Appended {entry.type} entry to session {session_id}")
        return entry.id
    
    except Exception as exc:
        logger.error(f"Failed to append entry to session {session_id}: {exc}")
        raise


async def load_transcript(session_id: str) -> list[JSONLEntry]:
    """
    Load a session transcript from JSONL file.
    
    Args:
        session_id: Session identifier
    
    Returns:
        List of entries in chronological order
    """
    file_path = get_sessions_dir() / f"{session_id}.jsonl"
    
    if not file_path.exists():
        logger.debug(f"Session transcript not found: {session_id}")
        return []
    
    entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = JSONLEntry(**json.loads(line))
                    entries.append(entry)
                except Exception as exc:
                    logger.warning(f"Failed to parse line {line_num} in session {session_id}: {exc}")
                    continue
        
        logger.debug(f"Loaded {len(entries)} entries from session {session_id}")
        return entries
    
    except Exception as exc:
        logger.error(f"Failed to load transcript for session {session_id}: {exc}")
        return []


async def load_transcript_range(
    session_id: str,
    start_index: int = 0,
    end_index: int | None = None,
) -> list[JSONLEntry]:
    """
    Load a range of entries from a session transcript.
    
    More efficient than loading full transcript for large sessions.
    
    Args:
        session_id: Session identifier
        start_index: Start index (0-based)
        end_index: End index (exclusive), or None for all remaining
    
    Returns:
        List of entries in the specified range
    """
    all_entries = await load_transcript(session_id)
    
    if end_index is None:
        return all_entries[start_index:]
    
    return all_entries[start_index:end_index]


async def get_session_stats(session_id: str) -> SessionStats:
    """
    Get statistics about a session transcript.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session statistics
    """
    file_path = get_sessions_dir() / f"{session_id}.jsonl"
    
    if not file_path.exists():
        return SessionStats(
            session_id=session_id,
            total_entries=0,
            message_count=0,
            tool_result_count=0,
            compaction_count=0,
            first_entry_at=None,
            last_entry_at=None,
            file_size_bytes=0,
            estimated_tokens=0,
        )
    
    entries = await load_transcript(session_id)
    file_size = file_path.stat().st_size
    
    # Count by type
    message_count = sum(1 for e in entries if e.type == "message")
    tool_result_count = sum(1 for e in entries if e.type == "toolResult")
    compaction_count = sum(1 for e in entries if e.type == "compaction")
    
    # Get timestamps
    timestamps = [e.timestamp for e in entries if e.timestamp]
    first_entry_at = min(timestamps) if timestamps else None
    last_entry_at = max(timestamps) if timestamps else None
    
    # Estimate tokens (rough: 1 token ≈ 4 chars for English)
    total_chars = sum(
        len(json.dumps(e.content)) + len(e.type) + len(e.timestamp)
        for e in entries
    )
    estimated_tokens = total_chars // 4
    
    return SessionStats(
        session_id=session_id,
        total_entries=len(entries),
        message_count=message_count,
        tool_result_count=tool_result_count,
        compaction_count=compaction_count,
        first_entry_at=first_entry_at,
        last_entry_at=last_entry_at,
        file_size_bytes=file_size,
        estimated_tokens=estimated_tokens,
    )


async def delete_transcript(session_id: str) -> bool:
    """
    Delete a session transcript.
    
    Args:
        session_id: Session identifier
    
    Returns:
        True if deleted, False if file didn't exist
    """
    file_path = get_sessions_dir() / f"{session_id}.jsonl"
    
    if not file_path.exists():
        return False
    
    file_path.unlink()
    logger.info(f"Deleted transcript for session {session_id}")
    return True


async def archive_transcript(session_id: str) -> Path | None:
    """
    Archive a session transcript (move to archive directory).
    
    Args:
        session_id: Session identifier
    
    Returns:
        Path to archived file, or None if file didn't exist
    """
    file_path = get_sessions_dir() / f"{session_id}.jsonl"
    
    if not file_path.exists():
        return None
    
    # Create archive directory
    archive_dir = get_sessions_dir() / "archive" / datetime.now().strftime("%Y-%m")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Move file
    archive_path = archive_dir / f"{session_id}.jsonl"
    shutil.move(str(file_path), str(archive_path))
    
    logger.info(f"Archived session {session_id} to {archive_path}")
    return archive_path


async def compact_transcript(
    session_id: str,
    summary: str,
    first_kept_entry_id: str,
) -> bool:
    """
    Compact a session transcript by replacing old entries with a summary.
    
    Atomic operation: writes to temp file, then renames.
    
    Args:
        session_id: Session identifier
        summary: Compaction summary text
        first_kept_entry_id: ID of first entry to keep (entries before this are summarized)
    
    Returns:
        True if successful
    """
    file_path = get_sessions_dir() / f"{session_id}.jsonl"
    
    if not file_path.exists():
        logger.warning(f"Cannot compact non-existent session: {session_id}")
        return False
    
    # Load all entries
    entries = await load_transcript(session_id)
    
    # Find entries to keep
    entries_to_keep = []
    found_first_kept = False
    
    for entry in entries:
        if entry.id == first_kept_entry_id:
            found_first_kept = True
        if found_first_kept:
            entries_to_keep.append(entry)
    
    if not found_first_kept:
        logger.error(f"First kept entry not found: {first_kept_entry_id}")
        return False
    
    # Create compaction entry
    compaction_entry = JSONLEntry(
        id=str(uuid.uuid4()),
        type="compaction",
        content={
            "summary": summary,
            "firstKeptEntryId": first_kept_entry_id,
            "entries_removed": len(entries) - len(entries_to_keep),
        },
        metadata={
            "compacted_at": datetime.now().isoformat(),
        },
    )
    
    # Write to temp file, then rename (atomic)
    temp_fd, temp_path = tempfile.mkstemp(
        suffix='.jsonl',
        prefix=f'{session_id}_',
        dir=get_sessions_dir(),
    )
    
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            # Write compaction entry first
            f.write(json.dumps(compaction_entry.model_dump(), ensure_ascii=False) + '\n')
            
            # Write kept entries
            for entry in entries_to_keep:
                f.write(json.dumps(entry.model_dump(), ensure_ascii=False) + '\n')
        
        # Atomic rename
        shutil.move(temp_path, str(file_path))
        
        logger.info(
            f"Compacted session {session_id}: "
            f"removed {len(entries) - len(entries_to_keep)} entries, "
            f"kept {len(entries_to_keep)} entries"
        )
        return True
    
    except Exception as exc:
        logger.error(f"Failed to compact session {session_id}: {exc}")
        # Clean up temp file
        try:
            Path(temp_path).unlink()
        except:
            pass
        return False


async def list_sessions() -> list[str]:
    """
    List all session IDs with transcripts.
    
    Returns:
        List of session IDs
    """
    sessions_dir = get_sessions_dir()
    session_ids = []
    
    for file_path in sessions_dir.glob("*.jsonl"):
        session_ids.append(file_path.stem)
    
    return sorted(session_ids)


async def entry_to_message_dict(entry: JSONLEntry) -> dict:
    """
    Convert a JSONLEntry to a message dict suitable for LLM API.
    
    Args:
        entry: Entry to convert
    
    Returns:
        Message dict with role and content
    """
    if entry.type == "message":
        content = entry.content
        if isinstance(content, dict):
            return {
                "role": content.get("role", "user"),
                "content": content.get("content", ""),
            }
        else:
            return {
                "role": "user",
                "content": str(content),
            }
    
    elif entry.type == "toolResult":
        return {
            "role": "tool",
            "content": json.dumps(entry.content),
            "tool_call_id": entry.content.get("tool_call_id", entry.id),
        }
    
    elif entry.type == "compaction":
        return {
            "role": "system",
            "content": f"[Session compaction summary: {entry.content.get('summary', '')}]",
        }
    
    elif entry.type == "session_info":
        # Don't include session info in message context
        return {}
    
    else:
        return {}
