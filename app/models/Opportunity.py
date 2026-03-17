from typing import List

from app.helpers.Database import MongoDB
from bson import ObjectId
import os


class OpportunityModel:
    """Model for Opportunities - each opportunity stored at root level."""

    def __init__(self, db_name=os.getenv("DB_NAME"), collection_name="Opportunities"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def insert_many(self, opportunities: list[dict]) -> list[str]:
        """Insert multiple opportunities as root-level documents."""
        if not opportunities:
            return []
        result = await self.collection.insert_many(opportunities)
        return [str(oid) for oid in result.inserted_ids]

    async def get_list(self, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[dict]:
        """Get opportunities with pagination. Returns list of documents."""
        if sort_by is None:
            sort_by = {"_id": -1}
        cursor = (
            self.collection.find({})
            .sort(list(sort_by.items()))
            .skip(skip)
            .limit(limit)
        )
        return [doc async for doc in cursor]

    async def count(self) -> int:
        """Get total count of opportunities."""
        return await self.collection.count_documents({})

    async def delete_by_id(self, opportunity_id: str) -> bool:
        """Delete an opportunity by ID. Returns True if deleted."""
        result = await self.collection.delete_one({"_id": ObjectId(opportunity_id)})
        return result.deleted_count > 0

    async def get_by_id(self, opportunity_id: str) -> dict | None:
        """Get a single opportunity by ID."""
        doc = await self.collection.find_one({"_id": ObjectId(opportunity_id)})
        return doc

    async def get_by_ids(self, opportunity_ids: List[str]) -> List[dict]:
        """Get opportunities by list of IDs. Returns list in same order as ids; skips invalid/not-found ids."""
        if not opportunity_ids:
            return []
        oids = []
        for sid in opportunity_ids:
            try:
                oids.append(ObjectId(sid))
            except Exception:
                continue
        if not oids:
            return []
        cursor = self.collection.find({"_id": {"$in": oids}})
        docs = await cursor.to_list(length=len(oids))
        id_to_doc = {str(d["_id"]): d for d in docs}
        result = []
        for sid in opportunity_ids:
            if sid in id_to_doc:
                result.append(id_to_doc[sid])
        return result
