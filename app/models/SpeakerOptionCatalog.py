"""
Shared MongoDB access for speaker option collections: name, slug, type.
Collections: speakerTopics, speakerTargetAudeince, deliveryModes, speakingFormats.
"""
import os
import re
from typing import List, Optional, Tuple

from app.helpers.Database import MongoDB


def name_to_slug(name: str) -> str:
    """Lowercase slug: spaces, '&' -> hyphens (matches seed script)."""
    s = name.strip().lower()
    s = re.sub(r"\s*&\s*", "-and-", s)
    s = re.sub(r"[^\w\-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


class SpeakerOptionCatalogModel:
    """CRUD helpers for catalog documents {_id, name, slug, type}."""

    def __init__(self, collection_name: str, db_name: Optional[str] = None):
        self.collection = MongoDB.get_database(db_name or os.getenv("DB_NAME"))[
            collection_name
        ]

    def _to_public(self, doc: dict) -> dict:
        return {
            "_id": str(doc["_id"]),
            "name": doc.get("name", ""),
            "slug": doc.get("slug", ""),
            "type": doc.get("type") or "system",
        }

    def _filter_query_for_type(self, doc_type: Optional[str]) -> dict:
        """Mongo filter for catalog rows. None/empty = no filter (all rows)."""
        if doc_type is None or not str(doc_type).strip():
            return {}
        dt = str(doc_type).strip()
        if dt == "system":
            # Include legacy docs with no type (API treats them as system in _to_public).
            return {
                "$or": [
                    {"type": "system"},
                    {"type": {"$exists": False}},
                    {"type": None},
                    {"type": ""},
                ]
            }
        return {"type": dt}

    async def get_all(self, doc_type: Optional[str] = None) -> List[dict]:
        query = self._filter_query_for_type(doc_type)
        cursor = self.collection.find(query)
        docs = await cursor.to_list(length=None)
        out = []
        for doc in docs:
            if doc:
                out.append(self._to_public(doc))
        return out

    async def get_by_slug(self, slug: str) -> Optional[dict]:
        if not slug or not isinstance(slug, str):
            return None
        doc = await self.collection.find_one({"slug": slug.strip().lower()})
        if not doc:
            return None
        return self._to_public(doc)

    async def get_by_name(self, name: str) -> Optional[dict]:
        if not name or not isinstance(name, str):
            return None
        doc = await self.collection.find_one({"name": name.strip()})
        if not doc:
            return None
        return self._to_public(doc)

    async def get_many_by_names(self, names: List[str]) -> List[dict]:
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

    async def create_one(
        self,
        name: str,
        slug: Optional[str] = None,
        doc_type: str = "custom",
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Insert a catalog row. Returns (document, error_code).
        error_code is 'duplicate_slug', 'duplicate_name', or 'invalid_name'.
        """
        name = (name or "").strip()
        if not name:
            return None, "invalid_name"
        slug_final = (slug or name_to_slug(name)).strip().lower()
        if not slug_final:
            return None, "invalid_name"
        if await self.collection.find_one({"slug": slug_final}):
            return None, "duplicate_slug"
        if await self.collection.find_one({"name": name}):
            return None, "duplicate_name"
        doc = {"name": name, "slug": slug_final, "type": (doc_type or "custom").strip() or "custom"}
        result = await self.collection.insert_one(doc)
        created = await self.collection.find_one({"_id": result.inserted_id})
        if not created:
            return None, "invalid_name"
        return self._to_public(created), None
