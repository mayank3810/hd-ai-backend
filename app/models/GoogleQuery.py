import os
from bson import ObjectId

from app.helpers.Database import MongoDB


class GoogleQueryModel:
    """Model for GoogleQueries - stores query, status, urls, and processing metadata."""

    def __init__(self, db_name=os.getenv("DB_NAME"), collection_name="GoogleQueries"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create(self, data: dict) -> str:
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def get_by_id(self, google_query_id: str, user_id: str | None = None) -> dict | None:
        query = {"_id": ObjectId(google_query_id)}
        if user_id is not None:
            query["userId"] = user_id
        return await self.collection.find_one(query)

    async def update_by_id(self, google_query_id: str, update_data: dict) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(google_query_id)},
            {"$set": update_data},
        )
        return result.modified_count > 0

