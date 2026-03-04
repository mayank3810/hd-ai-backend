from app.helpers.Database import MongoDB
from bson import ObjectId
import os


class UrlCollectionModel:
    """Model for UrlCollection - stores only url and createdAt."""

    def __init__(self, db_name=os.getenv("DB_NAME"), collection_name="UrlCollections"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create(self, data: dict) -> str:
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def get_by_id(self, url_collection_id: str) -> dict | None:
        doc = await self.collection.find_one({"_id": ObjectId(url_collection_id)})
        return doc
