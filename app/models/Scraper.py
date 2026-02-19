from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.Scraper import ScraperSchema
import os


class ScraperModel:
    def __init__(self, db_name=os.getenv("DB_NAME"), collection_name="Scrapers"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create(self, data: dict) -> str:
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def get_by_id(self, scraper_id: str, user_id: str = None) -> ScraperSchema | None:
        query = {"_id": ObjectId(scraper_id)}
        if user_id is not None:
            query["userId"] = user_id
        doc = await self.collection.find_one(query)
        if doc:
            return ScraperSchema(**doc)
        return None

    async def get_list(self, user_id: str, skip: int = 0, limit: int = 100, sort_by: dict = None) -> list[ScraperSchema]:
        if sort_by is None:
            sort_by = {"createdAt": -1}
        cursor = (
            self.collection.find({"userId": user_id})
            .sort(list(sort_by.items()))
            .skip(skip)
            .limit(limit)
        )
        return [ScraperSchema(**doc) async for doc in cursor]

    async def count(self, user_id: str) -> int:
        return await self.collection.count_documents({"userId": user_id})

    async def update(self, scraper_id: str, user_id: str, update_data: dict) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(scraper_id), "userId": user_id},
            {"$set": update_data},
        )
        return result.modified_count > 0

    async def delete(self, scraper_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": ObjectId(scraper_id), "userId": user_id}
        )
        return result.deleted_count > 0
