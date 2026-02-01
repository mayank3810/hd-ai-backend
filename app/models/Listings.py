import os
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB
from app.schemas.Listings import Listing
from app.schemas.PyObjectId import PyObjectId


class ListingModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Listings"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_listing(self, listing: dict) -> PyObjectId:   
        result = await self.collection.insert_one(listing)
        return result.inserted_id

    async def list_listings(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[dict]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("created_at", -1)
        result = []
        async for doc in cursor:
            result.append(doc)
        return result

    async def get_listing(self, filters: dict) -> Optional[Listing]:
        document = await self.collection.find_one(filters)
        if document:
            return Listing(**document)
        return None

    async def get_listing_by_id(self, listing_id: str) -> Optional[Listing]:
        document = await self.collection.find_one({"_id": ObjectId(listing_id)})
        if document:
            return Listing(**document)
        return None

    async def update_listing(self, listing_id: str, data: dict) -> bool:
        data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(listing_id)},
            {"$set": data}
        )
        return result.modified_count > 0

    async def delete_listing(self, listing_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(listing_id)})
        return result.deleted_count > 0
    
    async def find_existing_listing(self, operator_id: str, booking_id: str = None, airbnb_id: str = None, pricelabs_id: str = None) -> Optional[Listing]:
        """
        Find existing listing for operator_id with any of the provided external IDs
        """
        # Build query to find listing with same operator_id and any of the external IDs
        query = {"operatorId": operator_id}
        
        # Add OR conditions for any of the external IDs if provided
        or_conditions = []
        if booking_id:
            or_conditions.append({"bookingId": booking_id})
        if airbnb_id:
            or_conditions.append({"airbnbId": airbnb_id})
        if pricelabs_id:
            or_conditions.append({"pricelabsId": pricelabs_id})
        
        if or_conditions:
            query["$or"] = or_conditions
        
        document = await self.collection.find_one(query)
        if document:
            return Listing(**document)
        return None
    
    async def find_existing_listing_no_schema(self, operator_id: str, booking_id: str = None, airbnb_id: str = None, pricelabs_id: str = None) -> Optional[dict]:
        """
        Find existing listing for operator_id with any of the provided external IDs
        """
        # Build query to find listing with same operator_id and any of the external IDs
        query = {"operatorId": operator_id}
        
        # Add OR conditions for any of the external IDs if provided
        or_conditions = []
        if booking_id:
            or_conditions.append({"bookingId": booking_id})
        if airbnb_id:
            or_conditions.append({"airbnbId": airbnb_id})
        if pricelabs_id:
            or_conditions.append({"pricelabsId": pricelabs_id})
        
        if or_conditions:
            query["$or"] = or_conditions
        
        document = await self.collection.find_one(query)
        if document:
            return document
        return None
    
    async def update_existing_listing(self, listing_id: str, update_data: dict) -> bool:
        """
        Update an existing listing with new data
        """
        update_data["updatedAt"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(listing_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
