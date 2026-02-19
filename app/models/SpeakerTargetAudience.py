"""
MongoDB model for Speaker Target Audience (used in onboarding target_audiences step).
Collection name matches seed script: speakerTargetAudeince.
"""
import os
from typing import List, Optional

from app.helpers.Database import MongoDB

SPEAKER_TARGET_AUDIENCE_COLLECTION = "speakerTargetAudeince"


class SpeakerTargetAudienceModel:
    """Fetches target audience options from speakerTargetAudeince collection."""

    def __init__(self, db_name: Optional[str] = None):
        self.collection = MongoDB.get_database(db_name or os.getenv("DB_NAME"))[
            SPEAKER_TARGET_AUDIENCE_COLLECTION
        ]

    async def get_all(self) -> List[dict]:
        """
        Return all audience documents as list of dicts with _id (string), name, slug.
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
