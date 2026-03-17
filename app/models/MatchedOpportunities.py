"""
MongoDB model for matched opportunities per speaker.
Collection: matchedOpportunities. One document per speaker: { speaker_id, opportunities: [opportunity_id, ...], updatedAt }.
"""
import os
from datetime import datetime
from typing import List

from app.helpers.Database import MongoDB


class MatchedOpportunitiesModel:
    """Model for matchedOpportunities collection: speaker_id -> list of opportunity ids."""

    def __init__(
        self,
        db_name: str = None,
        collection_name: str = "matchedOpportunities",
    ):
        db_name = db_name or os.getenv("DB_NAME")
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def upsert_by_speaker_id(self, speaker_id: str, opportunity_ids: List[str]) -> bool:
        """Insert or replace document for this speaker_id with the given opportunity ids. Returns True on success."""
        if not speaker_id:
            return False
        doc = {
            "speaker_id": str(speaker_id),
            "opportunities": [str(oid) for oid in (opportunity_ids or [])],
            "updatedAt": datetime.utcnow(),
        }
        await self.collection.update_one(
            {"speaker_id": str(speaker_id)},
            {"$set": doc},
            upsert=True,
        )
        return True

    async def get_by_speaker_id(self, speaker_id: str) -> dict | None:
        """Get document by speaker_id. Returns { speaker_id, opportunities: [...], updatedAt } or None."""
        if not speaker_id:
            return None
        doc = await self.collection.find_one({"speaker_id": str(speaker_id)})
        return doc
