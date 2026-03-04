import os
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB


class ImageAnalysisCheckpointsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="ImageAnalysisCheckpoints"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_checkpoint(self, data: dict) -> ObjectId:
        """Create a new image analysis checkpoint"""
        # Add timestamp if not present
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def upsert_checkpoint(self, batch_id: str, image_id: str, side: str, data: dict) -> ObjectId:
        """Upsert an image analysis checkpoint"""
        filter_query = {
            "batch_id": batch_id,
            "image_id": image_id,
            "side": side
        }
        
        # Add timestamp if not present
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            filter_query,
            {"$set": data},
            upsert=True,
            return_document=True
        )
        return result["_id"]

    async def get_checkpoint(self, batch_id: str, image_id: str, side: str) -> Optional[Dict[str, Any]]:
        """Get a specific checkpoint"""
        document = await self.collection.find_one({
            "batch_id": batch_id,
            "image_id": image_id,
            "side": side
        })
        return document

    async def get_checkpoints_by_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all checkpoints for a specific batch"""
        cursor = self.collection.find({"batch_id": batch_id})
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def list_checkpoints(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List checkpoints with pagination"""
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("created_at", -1)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def delete_checkpoint(self, batch_id: str, image_id: str, side: str) -> bool:
        """Delete a specific checkpoint"""
        result = await self.collection.delete_one({
            "batch_id": batch_id,
            "image_id": image_id,
            "side": side
        })
        return result.deleted_count > 0

    async def delete_checkpoints_by_batch(self, batch_id: str) -> int:
        """Delete all checkpoints for a specific batch"""
        result = await self.collection.delete_many({"batch_id": batch_id})
        return result.deleted_count
    
    async def update_quality_analysis(self, batch_id: str, image_id: str, side: str, quality_data: dict) -> bool:
        """Update quality analysis data for a specific checkpoint"""
        filter_query = {
            "batch_id": batch_id,
            "image_id": image_id,
            "side": side
        }
        
        update_data = {
            "$set": {
                "quality": quality_data,
                "quality_updated_at": datetime.utcnow()
            }
        }
        
        result = await self.collection.update_one(filter_query, update_data)
        return result.modified_count > 0
    
    async def get_non_duplicate_checkpoints(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all non-duplicate checkpoints for a specific batch"""
        cursor = self.collection.find({
            "batch_id": batch_id,
            "$or": [
                {"is_duplicate": {"$exists": False}},
                {"is_duplicate": False}
            ]
        })
        result = []
        async for doc in cursor:
            result.append(doc)
        return result