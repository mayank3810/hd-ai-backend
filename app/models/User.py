from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from app.schemas.User import UserSchema
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId
from dotenv import load_dotenv

load_dotenv()

class UserModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Users"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def get_user(self, filters: dict) -> Optional[UserSchema]:
        """
        Retrieve a single user matching the given filters.
        """
        document = await self.collection.find_one(filters)
        if document:
            return UserSchema(**document)
        return None

    async def get_company(self, filters: dict) -> Optional[UserSchema]:
        """
        Retrieve a single company (user) matching the given filters.
        Alias for get_user for semantic clarity.
        """
        return await self.get_user(filters)

    
    async def get_documents_count(self, filters: dict) -> int:
        """
        Retrieve a count of documents matching the given filters.
        """
        total_count = await self.collection.count_documents(filters)
        if total_count:
            return total_count
        return 0
    
    async def update_many(self, filters: dict, update: dict) -> int:
        await self.collection.update_many(
                filters,
                update
            )
        return True

    async def get_users(self, filters: dict = {}, skip: int = 0, limit: int = 10, sort: list = None) -> List[UserSchema]:
        """
        Retrieve a list of users matching the given filters with pagination.
        """
        cursor = self.collection.find(filters)
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        return [UserSchema(**doc) for doc in results]
    
    async def get_users_with_projection(self, filters: dict = {}, skip: int = 0, limit: int = 10, fields: List[str] = None) -> List[dict]:
        """
        Retrieve a list of users matching the given filters with pagination. with pagination and projection.
        """
        if fields is None:
            projection = {}
        else:
            projection = {field: 1 for field in fields}

        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def create_user(self, data: dict) -> PyObjectId:
        """
        Create a new user document in the database.
        """
        data["createdOn"] = datetime.utcnow()
        user = UserSchema(**data)
        result = await self.collection.insert_one(user.dict(by_alias=True))
        return result.inserted_id

    async def update_user(self, user_id: str, updates: dict) -> bool:
        """
        Update an existing user by its ID.
        """
        filters = {"_id": ObjectId(user_id)}
        result = await self.collection.update_one(filters, {"$set": updates})
        return result.modified_count > 0

    async def push_knowledge_id(self, user_id: str, knowledge,) -> bool:
        """
        Update an existing user by its ID.
        """
        filters = {"_id": ObjectId(user_id), "isDeleted": False}
        result = await self.collection.update_one(filters, {"$push": {"KnowledgeIds": knowledge}})
        return result.modified_count > 0

    async def soft_delete_user(self, user_id: str) -> bool:
        """
        Soft delete a user by marking it as deleted and setting DeletedOn.
        """
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id), "IsDeleted": False},
            {"$set": {"IsDeleted": True, "DeletedOn": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def delete_user(self, user_id: str) -> bool:
        """
        Permanently delete a user document from the database.
        """
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0
    
    async def update_password(self, email: str, new_password: str) -> bool:
        """Update the password of a user based on email."""
        result = await self.collection.update_one(
            {"email": email},
            {"$set": {"password": new_password, "updatedOn": datetime.utcnow()}}
        )
        return result.modified_count > 0    