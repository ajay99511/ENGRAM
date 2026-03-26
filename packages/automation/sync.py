import json
import logging
import shutil
import time
from pathlib import Path

import httpx
from qdrant_client import AsyncQdrantClient

from packages.shared.config import settings

logger = logging.getLogger(__name__)


async def create_qdrant_snapshot() -> dict:
    """Generate snapshots for all Qdrant collections and download locally."""
    result = {
        "status": "error",
        "message": "Snapshot export failed",
        "exported": [],
        "failed": [],
    }

    try:
        url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
        client = AsyncQdrantClient(url=url)

        try:
            res = await client.get_collections()
            collections = [c.name for c in res.collections]
        except Exception as exc:
            logger.warning("Could not list collections: %s", exc)
            result["error"] = f"Could not list collections: {exc}"
            return result

        if not collections:
            result["status"] = "skipped"
            result["message"] = "No collections found to snapshot"
            return result

        snapshot_dir = Path(settings.data_dir) / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        for collection in collections:
            try:
                logger.info("Creating snapshot for collection: %s", collection)
                snapshot_info = await client.create_snapshot(collection_name=collection)
                snapshot_name = snapshot_info.name

                snapshot_path = snapshot_dir / f"{collection}_{snapshot_name}"
                download_url = f"{url}/collections/{collection}/snapshots/{snapshot_name}"

                async with httpx.AsyncClient() as http_client:
                    async with http_client.stream("GET", download_url) as response:
                        response.raise_for_status()
                        with snapshot_path.open("wb") as handle:
                            async for chunk in response.aiter_bytes():
                                handle.write(chunk)

                logger.info("Successfully exported snapshot to %s", snapshot_path)
                result["exported"].append(str(snapshot_path))

            except Exception as exc:
                logger.error("Failed to snapshot collection %s: %s", collection, exc)
                result["failed"].append({"collection": collection, "error": str(exc)})

        # Also snapshot the chat database (SQLite)
        try:
            from packages.shared.db import db_path
            if db_path.exists():
                ts = int(time.time())
                chat_snapshot = snapshot_dir / f"chat_db_{ts}.sqlite"
                shutil.copy2(db_path, chat_snapshot)
                result["exported"].append(str(chat_snapshot))
        except Exception as exc:
            logger.warning("Failed to snapshot chat DB: %s", exc)

        if result["exported"] and result["failed"]:
            result["status"] = "partial"
            result["message"] = "Snapshots exported with partial failures"
        elif result["exported"]:
            result["status"] = "success"
            result["message"] = "Snapshots exported successfully"
        else:
            result["status"] = "error"
            result["message"] = "Failed to export snapshots"

        return result

    except Exception as exc:
        logger.error("Snapshotting background job failed: %s", exc)
        result["error"] = str(exc)
        return result


async def restore_latest_snapshots():
    """
    Check sync directory for newer snapshots and restore if needed.
    """
    snapshot_dir = Path(settings.data_dir) / "snapshots"
    if not snapshot_dir.exists():
        return

    tracker_file = snapshot_dir / ".last_restore_times.json"
    last_restore_times: dict[str, float] = {}
    if tracker_file.exists():
        try:
            last_restore_times = json.loads(tracker_file.read_text(encoding="utf-8"))
        except Exception:
            last_restore_times = {}

    url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
    snapshots = list(snapshot_dir.glob("*.snapshot"))

    # Restore latest snapshot per collection
    known_collections = [
        settings.mem0_collection,
        settings.podcast_qdrant_collection,
        settings.qdrant_collection,
    ]
    latest_by_collection: dict[str, Path] = {}
    for snap in snapshots:
        matched = None
        for coll in sorted(known_collections, key=len, reverse=True):
            if snap.name.startswith(f"{coll}_"):
                matched = coll
                break
        if not matched:
            continue
        existing = latest_by_collection.get(matched)
        if existing is None or snap.stat().st_mtime > existing.stat().st_mtime:
            latest_by_collection[matched] = snap

    for collection_name, latest_snapshot in latest_by_collection.items():
        last_restore = float(last_restore_times.get(collection_name, 0.0))
        if latest_snapshot.stat().st_mtime <= last_restore + 60:
            continue

        logger.info("Detected newer P2P snapshot: %s. Restoring to Qdrant...", latest_snapshot.name)
        try:
            upload_url = f"{url}/collections/{collection_name}/snapshots/upload?priority=snapshot"

            async with httpx.AsyncClient(timeout=300.0) as http_client:
                with latest_snapshot.open("rb") as handle:
                    files = {"snapshot": (latest_snapshot.name, handle, "application/octet-stream")}
                    response = await http_client.post(upload_url, files=files)
                    response.raise_for_status()

            logger.info("Successfully restored snapshot %s into %s", latest_snapshot.name, collection_name)
            last_restore_times[collection_name] = latest_snapshot.stat().st_mtime

        except Exception as exc:
            logger.error("Failed to restore snapshot %s: %s", latest_snapshot.name, exc)

    # Restore latest chat DB snapshot if present
    chat_snaps = list(snapshot_dir.glob("chat_db_*.sqlite"))
    if chat_snaps:
        latest_chat = max(chat_snaps, key=lambda p: p.stat().st_mtime)
        last_chat = float(last_restore_times.get("chat_db", 0.0))
        if latest_chat.stat().st_mtime > last_chat + 60:
            try:
                from packages.shared.db import db_path
                db_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(latest_chat, db_path)
                last_restore_times["chat_db"] = latest_chat.stat().st_mtime
                logger.info("Restored chat DB snapshot %s", latest_chat.name)
            except Exception as exc:
                logger.error("Failed to restore chat DB snapshot %s: %s", latest_chat.name, exc)

    try:
        tracker_file.write_text(json.dumps(last_restore_times, indent=2), encoding="utf-8")
    except Exception:
        pass
