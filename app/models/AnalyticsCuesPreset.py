from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.AnalyticsCuesPreset import AnalyticsCuesPresetSchema
import os

class AnalyticsCuesPresetModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="AnalyticsCuesPresets"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_analytics_cues_preset(self, preset_data: dict) -> str:
        """Create a new analytics cues preset"""
        result = await self.collection.insert_one(preset_data)
        return str(result.inserted_id)

    async def get_analytics_cues_preset(self, filter_query: dict) -> AnalyticsCuesPresetSchema:
        """Get a single analytics cues preset by filter"""
        preset_doc = await self.collection.find_one(filter_query)
        if preset_doc:
            return AnalyticsCuesPresetSchema(**preset_doc)
        return None

    async def get_analytics_cues_presets(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[AnalyticsCuesPresetSchema]:
        """Get multiple analytics cues presets with pagination and sorting
        
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
            presets.append(AnalyticsCuesPresetSchema(**doc))
        return presets

    async def get_analytics_cues_presets_count(self, filter_query: dict = None) -> int:
        """Get total count of analytics cues presets matching filter"""
        if filter_query is None:
            filter_query = {}
        return await self.collection.count_documents(filter_query)

    async def delete_analytics_cues_preset(self, preset_id: str) -> bool:
        """Delete an analytics cues preset"""
        result = await self.collection.delete_one({"_id": ObjectId(preset_id)})
        return result.deleted_count > 0

    async def get_analytics_cues_presets_by_operator(self, operator_id: str, limit: int = 5) -> list[AnalyticsCuesPresetSchema]:
        """Get analytics cues presets for a specific operator with limit"""
        filter_query = {
            "operatorId": operator_id
        }
        sort_by = {"createdAt": -1}  # Sort by creation date, newest first
        cursor = self.collection.find(filter_query).sort(list(sort_by.items())).limit(limit)
        presets = []
        async for doc in cursor:
            presets.append(AnalyticsCuesPresetSchema(**doc))
        return presets

