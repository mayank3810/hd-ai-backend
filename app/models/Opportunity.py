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
