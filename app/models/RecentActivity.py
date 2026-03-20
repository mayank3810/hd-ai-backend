import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from app.helpers.Database import MongoDB

logger = logging.getLogger(__name__)


def _serialize_activity_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    ca = out.get("createdAt")
    if hasattr(ca, "isoformat"):
        out["createdAt"] = ca.isoformat()
    return out


class RecentActivityModel:
    """Append-only feed for dashboard / audit: scraper runs, opportunity batches, Google query jobs."""

    def __init__(self, db_name=os.getenv("DB_NAME"), collection_name: str = "recentActivities"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def insert_activity(self, activity_type: str, message: str) -> str:
        doc = {
            "type": activity_type,
            "message": message,
            "createdAt": datetime.utcnow(),
        }
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def try_insert_activity(self, activity_type: str, message: str) -> None:
        """Insert activity; log and swallow errors so ingestion pipelines are not blocked."""
        try:
            await self.insert_activity(activity_type, message)
        except Exception as e:
            logger.warning("Recent activity insert failed type=%s: %s", activity_type, e)

    async def list_created_between(self, start_inclusive: datetime, end_exclusive: datetime) -> List[dict]:
        """Activities with createdAt in [start_inclusive, end_exclusive), newest first."""
        cursor = (
            self.collection.find(
                {"createdAt": {"$gte": start_inclusive, "$lt": end_exclusive}}
            ).sort("createdAt", -1)
        )
        docs = await cursor.to_list(length=None)
        return [_serialize_activity_doc(d) for d in docs]

    async def list_recent(self, limit: int) -> List[dict]:
        """Newest activities first, capped at limit."""
        cursor = self.collection.find({}).sort("createdAt", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [_serialize_activity_doc(d) for d in docs]
