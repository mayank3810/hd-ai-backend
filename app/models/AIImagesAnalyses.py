import os
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB


class AIImagesAnalysesModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="AIImagesAnalyses"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_analysis(self, data: dict) -> ObjectId:
        """Create a new AI image analysis"""
        # Add timestamp if not present
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def upsert_analysis(self, doc_id: str, llm_data: dict) -> ObjectId:
        """Upsert an AI image analysis"""
        filter_query = {"doc_id": doc_id}
        
        # Add timestamp if not present
        if "ts" not in llm_data:
            llm_data["ts"] = datetime.utcnow()
        
        update_data = {
            "$set": {
                "llm": llm_data,
                "updated_at": datetime.utcnow()
            }
        }
        
        result = await self.collection.find_one_and_update(
            filter_query,
            update_data,
            upsert=True,
            return_document=True
        )
        return result["_id"]

    async def get_analysis(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific analysis by doc_id"""
        document = await self.collection.find_one({"doc_id": doc_id})
        return document

    async def list_analyses(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List analyses with pagination"""
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("created_at", -1)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def delete_analysis(self, doc_id: str) -> bool:
        """Delete a specific analysis"""
        result = await self.collection.delete_one({"doc_id": doc_id})
        return result.deleted_count > 0

    async def get_analyses_by_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all analyses for a specific batch"""
        cursor = self.collection.find({"batch_id": batch_id})
        result = []
        async for doc in cursor:
            result.append(doc)
        return result
