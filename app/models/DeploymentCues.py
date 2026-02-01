from app.helpers.Database import MongoDB
from bson import ObjectId
from app.schemas.DeploymentCues import DeploymentCuePropertiesSchema
import os

class DeploymentCuesModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="DeploymentCues"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_deployment_cue(self, deployment_cue_data: dict) -> ObjectId:
        """Create a new deployment cue"""
        result = await self.collection.insert_one(deployment_cue_data)
        return result.inserted_id

    async def get_deployment_cue(self, filter_query: dict) -> DeploymentCuePropertiesSchema:
        """Get a single deployment cue by filter"""
        deployment_cue_doc = await self.collection.find_one(filter_query)
        if deployment_cue_doc:
            return DeploymentCuePropertiesSchema(**deployment_cue_doc)
        return None

    async def get_deployment_cues(self, filter_query: dict = None, skip: int = 0, limit: int = 10, sort_by: dict = None) -> list[DeploymentCuePropertiesSchema]:
        """Get multiple deployment cues with pagination and sorting
        
        Args:
            filter_query: MongoDB filter query
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort_by: MongoDB sort specification, e.g., {"createdAt": -1} for descending order
        """
        if filter_query is None:
            filter_query = {}
        if sort_by is None:
            sort_by = {"_id": -1}  # Default sort by _id (which includes timestamp), newest first
            
        cursor = self.collection.find(filter_query).sort(list(sort_by.items())).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(DeploymentCuePropertiesSchema(**doc))
        return result

    async def get_deployment_cues_count(self, filter_query: dict = None) -> int:
        """Get total count of deployment cues matching filter"""
        if filter_query is None:
            filter_query = {}
        return await self.collection.count_documents(filter_query)

    async def update_deployment_cue(self, deployment_cue_id: str, update_data: dict) -> bool:
        """Update a deployment cue"""
        result = await self.collection.update_one(
            {"_id": ObjectId(deployment_cue_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def update_status(self, deployment_cue_id: str, status: str) -> bool:
        """Update the status of a deployment cue"""
        result = await self.collection.update_one(
            {"_id": ObjectId(deployment_cue_id)},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0

    async def delete_deployment_cue(self, deployment_cue_id: str) -> bool:
        """Delete a deployment cue"""
        result = await self.collection.delete_one({"_id": ObjectId(deployment_cue_id)})
        return result.deleted_count > 0

    async def add_note_to_deployment_cue(self, deployment_cue_id: str, note_data: dict) -> bool:
        """Add a note to a deployment cue"""
        result = await self.collection.update_one(
            {"_id": ObjectId(deployment_cue_id)},
            {"$push": {"notes": note_data}}
        )
        return result.modified_count > 0

    async def add_assigned_user_to_deployment_cue(self, deployment_cue_id: str, user_data: dict) -> bool:
        """Add an assigned user to a deployment cue"""
        result = await self.collection.update_one(
            {"_id": ObjectId(deployment_cue_id)},
            {"$push": {"assignedTo": user_data}}
        )
        return result.modified_count > 0

    async def remove_assigned_user_from_deployment_cue(self, deployment_cue_id: str, user_id: str) -> bool:
        """Remove an assigned user from a deployment cue"""
        result = await self.collection.update_one(
            {"_id": ObjectId(deployment_cue_id)},
            {"$pull": {"assignedTo": {"userId": user_id}}}
        )
        return result.modified_count > 0

    async def search_deployment_cues(self, search_query: str, skip: int = 0, limit: int = 10) -> list[DeploymentCuePropertiesSchema]:
        """Search deployment cues by name, tag, or descriptions"""
        filter_query = {
            "$or": [
                {"name": {"$regex": search_query, "$options": "i"}},
                {"tag": {"$regex": search_query, "$options": "i"}},
                {"description1": {"$regex": search_query, "$options": "i"}},
                {"description2": {"$regex": search_query, "$options": "i"}}
            ]
        }
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(DeploymentCuePropertiesSchema(**doc))
        return result

    async def get_deployment_cues_by_operator(self, operator_id: str, skip: int = 0, limit: int = 10) -> list[DeploymentCuePropertiesSchema]:
        """Get deployment cues by operator ID"""
        filter_query = {"operatorId": operator_id}
        cursor = self.collection.find(filter_query).sort([("_id", -1)]).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(DeploymentCuePropertiesSchema(**doc))
        return result

    async def get_deployment_cues_by_property(self, property_id: str, skip: int = 0, limit: int = 10) -> list[DeploymentCuePropertiesSchema]:
        """Get deployment cues by property ID"""
        filter_query = {"propertyId": property_id}
        cursor = self.collection.find(filter_query).sort([("_id", -1)]).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(DeploymentCuePropertiesSchema(**doc))
        return result

    async def get_deployment_cues_by_status(self, status: str, skip: int = 0, limit: int = 10) -> list[DeploymentCuePropertiesSchema]:
        """Get deployment cues by status"""
        filter_query = {"status": status}
        cursor = self.collection.find(filter_query).sort([("_id", -1)]).skip(skip).limit(limit)
        result = []
        async for doc in cursor:
            result.append(DeploymentCuePropertiesSchema(**doc))
        return result