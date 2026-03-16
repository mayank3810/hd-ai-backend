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

    async def get_list(
        self, user_id: str | None = None, skip: int = 0, limit: int = 100, sort_by: dict | None = None
    ) -> list[dict]:
        """Get GoogleQueries with pagination. Optionally filter by user_id."""
        if sort_by is None:
            sort_by = {"createdAt": -1}
        query = {}
        if user_id is not None:
            query["userId"] = user_id
        cursor = (
            self.collection.find(query)
            .sort(list(sort_by.items()))
            .skip(skip)
            .limit(limit)
        )
        return [doc async for doc in cursor]

    async def count(self, user_id: str | None = None) -> int:
        """Total count. Optionally filter by user_id."""
        query = {}
        if user_id is not None:
            query["userId"] = user_id
        return await self.collection.count_documents(query)

    async def delete_by_id(self, google_query_id: str, user_id: str | None = None) -> bool:
        """Delete a GoogleQuery by _id. Optionally restrict to user_id (own record only)."""
        query = {"_id": ObjectId(google_query_id)}
        if user_id is not None:
            query["userId"] = user_id
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0

