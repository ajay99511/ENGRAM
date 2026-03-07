import logging
import asyncio
from pathlib import Path
from qdrant_client import AsyncQdrantClient
from packages.shared.config import settings
import httpx

logger = logging.getLogger(__name__)

async def create_qdrant_snapshot():
    """Generates a snapshot for all Qdrant collections and downloads it to the data directory."""
    try:
        url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
        client = AsyncQdrantClient(url=url)
        
        # Determine the collections to snapshot
        collections = []
        try:
            res = await client.get_collections()
            collections = [c.name for c in res.collections]
        except Exception as e:
            logger.warning(f"Could not list collections: {e}")
            return
            
        snapshot_dir = Path(settings.data_dir) / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        for collection in collections:
            try:
                # 1. Trigger snapshot creation on Qdrant Server
                logger.info(f"Creating snapshot for collection: {collection}")
                snapshot_info = await client.create_snapshot(collection_name=collection)
                snapshot_name = snapshot_info.name
                
                # 2. Download snapshot file to the synced directory
                snapshot_path = snapshot_dir / f"{collection}_{snapshot_name}"
                download_url = f"{url}/collections/{collection}/snapshots/{snapshot_name}"
                
                async with httpx.AsyncClient() as http_client:
                    async with http_client.stream("GET", download_url) as r:
                        r.raise_for_status()
                        with snapshot_path.open("wb") as f:
                            async for chunk in r.aiter_bytes():
                                f.write(chunk)
                
                logger.info(f"Successfully exported snapshot to {snapshot_path}")
                
            except Exception as e:
                logger.error(f"Failed to snapshot collection {collection}: {e}")
                
    except Exception as exc:
        logger.error(f"Snapshotting background job failed: {exc}")


async def restore_latest_snapshots():
    """
    Checks the sync directory for new Qdrant snapshots.
    If a snapshot is newer than the last restored timestamp, upload and recover it.
    """
    snapshot_dir = Path(settings.data_dir) / "snapshots"
    if not snapshot_dir.exists():
        return

    tracker_file = snapshot_dir / ".last_restore_time"
    last_restore = 0.0
    if tracker_file.exists():
        last_restore = float(tracker_file.read_text().strip())

    url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
    
    # Group snapshots by collection name based on our naming convention: {collection}_{uuid}.snapshot
    # For simplicity, let's just find the newest snapshot file overall assuming it's a monolithic state
    snapshots = list(snapshot_dir.glob("*.snapshot"))
    if not snapshots:
        return
        
    latest_snapshot = max(snapshots, key=lambda p: p.stat().st_mtime)
    
    if latest_snapshot.stat().st_mtime > last_restore + 60: # 60 second breathing room
        logger.info(f"Detected newer P2P snapshot: {latest_snapshot.name}. Restoring to Qdrant...")
        
        collection_name = "personal_memories" # Attempt to extract or default
        for prefix in [settings.mem0_collection, settings.podcast_qdrant_collection, settings.qdrant_collection]:
            if latest_snapshot.name.startswith(prefix):
                collection_name = prefix
                break
                
        try:
            # Upload and restore snapshot via Qdrant REST API
            upload_url = f"{url}/collections/{collection_name}/snapshots/upload?priority=snapshot"
            
            async with httpx.AsyncClient(timeout=300.0) as http_client:
                with latest_snapshot.open("rb") as f:
                    # Qdrant multipart upload
                    files = {"snapshot": (latest_snapshot.name, f, "application/octet-stream")}
                    r = await http_client.post(upload_url, files=files)
                    r.raise_for_status()
            
            logger.info(f"Successfully restored snapshot {latest_snapshot.name} into {collection_name}")
            tracker_file.write_text(str(latest_snapshot.stat().st_mtime))
            
        except Exception as e:
            logger.error(f"Failed to restore snapshot {latest_snapshot.name}: {e}")
