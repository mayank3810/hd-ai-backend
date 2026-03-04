from typing import Optional, Dict, Any
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from app.schemas.QueueStatus import QueueStatusSchema
from datetime import datetime

class QueueStatusModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Queue"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_queue_entry(self, queue_data: dict) -> QueueStatusSchema:
        """
        Create a new queue entry.
        """
        queue_data["created_at"] = datetime.utcnow()
        queue_data["retry_count"] = 0
        queue_data["max_retries"] = 3
        
        if "status" not in queue_data:
            queue_data["status"] = "pending"
        
        result = await self.collection.insert_one(queue_data)
        queue_data["_id"] = result.inserted_id
        return QueueStatusSchema(**queue_data)

    async def get_queue_by_operator_and_platform_ids(self, operator_id: str, pricelabs_id: Optional[str] = None, 
                                                      airbnb_id: Optional[str] = None, booking_id: Optional[str] = None,
                                                      vrbo_id: Optional[str] = None) -> Optional[QueueStatusSchema]:
        """
        Retrieve queue status by operator ID and any platform ID.
        Searches for: operator_id AND (pricelabs_id OR airbnb_id OR booking_id OR vrbo_id).
        """
        # Build query: operator_id AND any of the platform IDs
        query = {"operator_id": operator_id}
        
        # Add OR condition for platform IDs if any are provided
        platform_conditions = []
        if pricelabs_id:
            platform_conditions.append({"pricelabs_id": pricelabs_id})
        if airbnb_id:
            platform_conditions.append({"airbnb_id": airbnb_id})
        if booking_id:
            platform_conditions.append({"booking_id": booking_id})
        if vrbo_id:
            platform_conditions.append({"vrbo_id": vrbo_id})
        
        if platform_conditions:
            query["$or"] = platform_conditions
        
        document = await self.collection.find_one(query)
        if document:
            return QueueStatusSchema(**document)
        return None

    async def find_existing_queue_entry(self, operator_id: str, queue_data: dict) -> Optional[QueueStatusSchema]:
        """
        Find existing queue entry by operator_id and any platform ID.
        Checks operator_id AND (pricelabs_id OR airbnb_id OR booking_id OR vrbo_id).
        """
        pricelabs_id = queue_data.get("pricelabs_id")
        airbnb_id = queue_data.get("airbnb_id")
        booking_id = queue_data.get("booking_id")
        vrbo_id = queue_data.get("vrbo_id")
        
        # Build query: operator_id AND any of the platform IDs
        query = {"operator_id": operator_id}
        
        # Add OR condition for platform IDs if any are provided
        platform_conditions = []
        if pricelabs_id:
            platform_conditions.append({"pricelabs_id": pricelabs_id})
        if airbnb_id:
            platform_conditions.append({"airbnb_id": airbnb_id})
        if booking_id:
            platform_conditions.append({"booking_id": booking_id})
        if vrbo_id:
            platform_conditions.append({"vrbo_id": vrbo_id})
        
        if platform_conditions:
            query["$or"] = platform_conditions
            
            document = await self.collection.find_one(query)
            if document:
                return QueueStatusSchema(**document)
        
        return None

    async def upsert_queue_status(self, operator_id: str, queue_data: dict) -> QueueStatusSchema:
        """
        Create or update queue status for an operator.
        Checks for existing entry by operator_id AND any platform ID (pricelabs_id, airbnb_id, booking_id, vrbo_id).
        If found, updates the existing entry. Otherwise, creates a new one.
        """
        # Check if entry already exists
        existing = await self.find_existing_queue_entry(operator_id, queue_data)
        
        if existing:
            # Update existing record
            # Remove created_at from update data if present
            queue_data.pop("created_at", None)
            
            # Build update query using the same logic
            query = {"operator_id": operator_id}
            platform_conditions = []
            
            if queue_data.get("pricelabs_id"):
                platform_conditions.append({"pricelabs_id": queue_data.get("pricelabs_id")})
            if queue_data.get("airbnb_id"):
                platform_conditions.append({"airbnb_id": queue_data.get("airbnb_id")})
            if queue_data.get("booking_id"):
                platform_conditions.append({"booking_id": queue_data.get("booking_id")})
            if queue_data.get("vrbo_id"):
                platform_conditions.append({"vrbo_id": queue_data.get("vrbo_id")})
            
            if platform_conditions:
                query["$or"] = platform_conditions
            
            result = await self.collection.update_one(
                query,
                {"$set": queue_data}
            )
            
            if result.modified_count > 0 or result.matched_count > 0:
                # Return updated document
                document = await self.collection.find_one(query)
                if document:
                    return QueueStatusSchema(**document)
            return existing
        else:
            # Create new record
            queue_data["operator_id"] = operator_id
            return await self.create_queue_entry(queue_data)

    async def update_queue_status(self, operator_id: str, status: str, error_message: Optional[str] = None,
                                  started_at: Optional[datetime] = None, completed_at: Optional[datetime] = None) -> bool:
        """
        Update queue entry status.
        """
        update_data = {"status": status}
        
        if error_message:
            update_data["error_message"] = error_message
        if started_at:
            update_data["started_at"] = started_at
        if completed_at:
            update_data["completed_at"] = completed_at
        
        result = await self.collection.update_one(
            {"operator_id": operator_id},
            {"$set": update_data}
        )
        
        return result.modified_count > 0

    async def increment_retry_count(self, operator_id: str) -> bool:
        """
        Increment retry count for a queue entry.
        """
        result = await self.collection.update_one(
            {"operator_id": operator_id},
            {"$inc": {"retry_count": 1}}
        )
        return result.modified_count > 0
