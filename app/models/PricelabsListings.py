import os
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB
from app.schemas.PyObjectId import PyObjectId
from app.schemas.PricelabsListings import PricelabsListings


class PricelabsListingsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="PricelabsListings"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_pricelabs_listings(self, data: list[dict]) -> List[PyObjectId]:
        result = await self.collection.insert_many(data)
        return result.inserted_ids

    async def get_pricelabs_listings_with_pagination(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[dict]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("createdAt", -1)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_pricelabs_listings_with_projection(
        self, filters: dict = {}, skip: int = 0, limit: int = 100, fields: List[str] = None
    ) -> List[dict]:
        projection = {field: 1 for field in fields} if fields else {}
        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_pricelabs_listings(self, filters: dict):
        document = await self.collection.find_one(filters)
        if document:
            return document
        return None

    async def update_pricelabs_listings(self, operator_id: str, data: dict) -> bool:
        data["updatedAt"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"operatorId": operator_id},
            {"$set": data}
        )
        return result.modified_count > 0

    async def delete_pricelabs_listings(self, operator_id: str) -> bool:
        result = await self.collection.delete_many({"operatorId": operator_id})
        return result.deleted_count > 0
