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
