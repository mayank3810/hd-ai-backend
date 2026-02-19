"""
MongoDB model for Speaker Topics (used in onboarding topics step).
"""
import os
from typing import List, Optional

from app.helpers.Database import MongoDB

SPEAKER_TOPICS_COLLECTION = "speakerTopics"


class SpeakerTopicsModel:
    """Fetches topic options from speakerTopics collection."""

    def __init__(self, db_name: Optional[str] = None):
        self.collection = MongoDB.get_database(db_name or os.getenv("DB_NAME"))[
            SPEAKER_TOPICS_COLLECTION
        ]

    async def get_all(self) -> List[dict]:
        """
        Return all topic documents as list of dicts with _id (string), name, slug.
        """
        cursor = self.collection.find({})
        docs = await cursor.to_list(length=None)
        out = []
        for doc in docs:
            if not doc:
                continue
            out.append({
                "_id": str(doc["_id"]),
                "name": doc.get("name", ""),
                "slug": doc.get("slug", ""),
            })
        return out
