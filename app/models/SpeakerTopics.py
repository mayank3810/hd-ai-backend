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

    async def get_by_slug(self, slug: str) -> Optional[dict]:
        """Return topic document by slug (case-insensitive)."""
        if not slug or not isinstance(slug, str):
            return None
        doc = await self.collection.find_one({"slug": slug.strip().lower()})
        if not doc:
            return None
        return {"_id": str(doc["_id"]), "name": doc.get("name", ""), "slug": doc.get("slug", "")}

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Return topic document by exact name match (case-sensitive)."""
        if not name or not isinstance(name, str):
            return None
        doc = await self.collection.find_one({"name": name.strip()})
        if not doc:
            return None
        return {"_id": str(doc["_id"]), "name": doc.get("name", ""), "slug": doc.get("slug", "")}

    async def get_many_by_names(self, names: List[str]) -> List[dict]:
        """Return topic documents for names that exist (match by name or slug)."""
        if not names:
            return []
        seen = set()
        out = []
        for n in names:
            n = (n or "").strip()
            if not n or n in seen:
                continue
            doc = await self.get_by_name(n)
            if not doc:
                doc = await self.get_by_slug(n.lower().replace(" ", "-").replace("&", "and"))
            if doc:
                seen.add(n)
                out.append(doc)
        return out
