from app.models.BookingListings import BookingListingsModel
from bson import ObjectId
from fastapi import HTTPException
from app.models.Operator import OperatorModel
from datetime import datetime

class BookingService:
    def __init__(self):
        self.booking_model = BookingListingsModel()
        self.operator_model = OperatorModel()
        
    async def save_booking_listings(self, operator_id: str,listings:list) -> dict:
        try:
            booking_listings=[]
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            for listing in listings:
                
                filter = {"operatorId": operator_id, "listingId": listing.get("id")}
                
                payload = {
                    "listingId": listing.get("id"),
                    "operatorId": operator_id,
                    "name": listing.get("name"),
                    "scrapedStatus": "PENDING",
                    "ingestionStatus": "PENDING",
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }
                
                
                existing_listings = await self.booking_model.get_booking_listings(filter)
                
                if existing_listings:
                    existing_listings = await self.booking_model.collection.find_one_and_update(filter, {"$set": payload})
                    continue
                else:
                    inserted_ids = await self.booking_model.collection.insert_one(payload)
                    continue
            
            return {
                "success": True,
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create booking listings: {str(e)}"
            }
            
            