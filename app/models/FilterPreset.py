from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.FilterPreset import FilterPresetSchema
import os

class FilterPresetModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="FilterPresets"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_filter_preset(self, filter_preset_data: dict) -> str:
        """Create a new filter preset"""
        result = await self.collection.insert_one(filter_preset_data)
        return str(result.inserted_id)

    async def exists_with_name_for_operator(self, name: str, operator_id: str) -> bool:
        """Check if a filter preset exists with same name for operator"""
        query = {
            "name": name,
            "operatorId": operator_id
        }
        count = await self.collection.count_documents(query)
        return count > 0

    async def get_filter_preset(self, filter_query: dict) -> FilterPresetSchema:
        """Get a single filter preset by filter"""
        filter_preset_doc = await self.collection.find_one(filter_query)
        if filter_preset_doc:
            return FilterPresetSchema(**filter_preset_doc)
        return None

    async def get_filter_presets(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[FilterPresetSchema]:
        """Get multiple filter presets with pagination and sorting
        
        Args:
            filter_query: MongoDB filter query
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort_by: MongoDB sort specification, e.g., {"createdAt": -1} for descending order
        """
        if filter_query is None:
            filter_query = {}
        if sort_by is None:
            sort_by = {"createdAt": -1}  # Default sort by creation date, newest first
            
        cursor = self.collection.find(filter_query).sort(list(sort_by.items())).skip(skip).limit(limit)
        presets = []
        async for doc in cursor:
            presets.append(FilterPresetSchema(**doc))
        return presets

    async def get_filter_presets_count(self, filter_query: dict = None) -> int:
        """Get total count of filter presets matching filter"""
        if filter_query is None:
            filter_query = {}
        return await self.collection.count_documents(filter_query)

    async def update_filter_preset(self, filter_preset_id: str, update_data: dict) -> bool:
        """Update a filter preset"""
        result = await self.collection.update_one(
            {"_id": ObjectId(filter_preset_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def delete_filter_preset(self, filter_preset_id: str) -> bool:
        """Delete a filter preset"""
        result = await self.collection.delete_one({"_id": ObjectId(filter_preset_id)})
        return result.deleted_count > 0

    async def get_filter_presets_by_operator(self, operator_id: str) -> list[FilterPresetSchema]:
        """Get filter presets for a specific operator"""
        filter_query = {
            "operatorId": operator_id
        }
        sort_by = {"createdAt": -1}  # Sort by creation date, newest first
        cursor = self.collection.find(filter_query).sort(list(sort_by.items()))
        presets = []
        async for doc in cursor:
            presets.append(FilterPresetSchema(**doc))
        return presets

    async def get_filter_presets_count_by_operator(self, operator_id: str) -> int:
        """Get total count of filter presets for a specific operator"""
        filter_query = {
            "operatorId": operator_id
        }
        return await self.collection.count_documents(filter_query)
