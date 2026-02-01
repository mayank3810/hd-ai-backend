import os
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB
from app.schemas.AirbnbAdminData import AirbnbAdminData
from app.schemas.PyObjectId import PyObjectId


class AirbnbAdminDataModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="AirbnbAdminData"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def save_airbnb_admin_data(self, data: dict) -> PyObjectId:
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def list_airbnb_admin_data(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[dict]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("createdAt", -1)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_airbnb_admin_data_with_projection(
        self, filters: dict = {}, skip: int = 0, limit: int = 100, fields: List[str] = None
    ) -> List[dict]:
        projection = {field: 1 for field in fields} if fields else {}
        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_airbnb_admin_data(self, filters: dict) -> Optional[AirbnbAdminData]:
        document = await self.collection.find_one(filters)
        if document:
            return AirbnbAdminData(**document)
        return None

    async def update_airbnb_admin_data(self, operator_id: str, data: dict) -> bool:
        data["updatedAt"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(operator_id)},
            {"$set": data}
        )
        return result.modified_count > 0

    async def delete_airbnb_admin(self, operator_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(operator_id)})
        return result.deleted_count > 0
