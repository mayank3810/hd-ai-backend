import os
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB
from app.schemas.PyObjectId import PyObjectId


class AirbnbTemporaryCompetitorsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="AirbnbTemporaryCompetitors"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_airbnb_temporary_competitor(self, data:dict) -> List[PyObjectId]:
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def get_airbnb_temporary_competitor(self, filters: dict = {}) -> Optional[dict]:
        document = await self.collection.find_one(filters)
        if document:
            return document
        return None

    async def update_airbnb_temporary_competitor(self, filters: dict, data: dict) -> bool:
        data["updatedAt"] = datetime.utcnow()
        result = await self.collection.update_one(
            filters,
            {"$set": data}
        )
        return result.modified_count > 0

    async def delete_airbnb_temporary_competitor(self, filters: dict) -> bool:
        result = await self.collection.delete_one(filters)
        return result.deleted_count > 0
