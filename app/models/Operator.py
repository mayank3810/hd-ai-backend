import os
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB
from app.schemas.Operator import Operator
from app.schemas.PyObjectId import PyObjectId


class OperatorModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Operators"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_operator(self, data: dict) -> PyObjectId:
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def list_operators(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[dict]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("createdAt", -1)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_operators_with_projection(
        self, filters: dict = {}, skip: int = 0, limit: int = 100, fields: List[str] = None
    ) -> List[dict]:
        projection = {field: 1 for field in fields} if fields else {}
        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_operator(self, filters: dict) -> Optional[Operator]:
        document = await self.collection.find_one(filters)
        if document:
            return Operator(**document)
        return None

    async def update_operator(self, operator_id: str, data: dict) -> bool:
        # Make a copy to avoid modifying the original dict
        data = data.copy()
        data["updatedAt"] = datetime.utcnow()
        
        # Separate cookies and userId from other data for special handling
        update_operations = {"$set": {}}
        userId_to_add = data.pop("userId", None)
        
        for key, value in data.items():
            if key == "updatedAt":
                update_operations["$set"][key] = value
            elif isinstance(value, dict) and "cookies" in value:
                # Handle platform configs with cookies
                platform_name = key
                platform_data = value.copy()
                cookies = platform_data.pop("cookies", None)
                
                # Set other platform fields using dot notation to avoid overwriting
                if platform_data:
                    for field, field_value in platform_data.items():
                        update_operations["$set"][f"{platform_name}.{field}"] = field_value
                
                # Handle cookies with $set to REPLACE the cookies array (not append)
                # Using $set ensures cookies are overwritten, preventing accumulation
                if cookies is not None:
                    update_operations["$set"][f"{platform_name}.cookies"] = cookies
            else:
                # Handle all other fields normally
                update_operations["$set"][key] = value
        
        # Handle userId separately - use $addToSet to append new user IDs without duplicates
        if userId_to_add:
            if not isinstance(userId_to_add, list):
                userId_to_add = [userId_to_add]
            update_operations["$addToSet"] = update_operations.get("$addToSet", {})
            update_operations["$addToSet"]["userId"] = {"$each": userId_to_add}
        
        result = await self.collection.update_one(
            {"_id": ObjectId(operator_id)},
            update_operations
        )
        return result.modified_count > 0

    async def remove_user_from_operator(self, operator_id: str, user_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(operator_id)},
            {"$pull": {"userId": user_id}, "$set": {"updatedAt": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def delete_operator(self, operator_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(operator_id)})
        return result.deleted_count > 0
