from datetime import datetime, timezone
from app.models.AirbnbListings import AirbnbListingsModel
from bson import ObjectId
from fastapi import HTTPException
from app.models.DataSyncQueue import DataSyncQueueModel
from app.models.Operator import OperatorModel
from datetime import datetime
import base64

class AirbnbService:
    def __init__(self):
        self.airbnb_model = AirbnbListingsModel()
        self.operator_model = OperatorModel()
        self.data_sync_queue_model = DataSyncQueueModel()
        
        
    async def save_airbnb_listings(self, operator_id: str,listings:list) -> dict:
        try:
            airbnb_listings=[]
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            
            self.data_sync_queue_model.collection.find_one_and_update(
                {"operatorId": operator_id},
                {"$set": {"airbnbStatus": "pending","airbnbLastSyncDate": datetime.now(timezone.utc)}}
                ,upsert=True)
            
            black_listig=["M13_EXPERIENCE_UPGRADE_REQUIRED"]
            for listing in listings:
                if listing.get("node", {}).get("listingStatus", {}).get("displayState").get("listOfListingsDisplayState") in black_listig:
                    continue
                decoded_id = base64.b64decode(listing.get("node", {}).get("id") or listing.get("id")).decode('utf-8')
                listing_id = int(decoded_id.split(':')[-1] if ':' in decoded_id else decoded_id)
                
                priclelabsId = listing.get("node", {}).get("descriptions", {}).get("nickname")
                
                filter = {"operatorId": operator_id, "listingId": listing_id}
                
                airbnb_listing={
                    "listingId": listing_id,
                    "priclelabsId": priclelabsId,
                    "operatorId": operator_id,
                    "name": listing.get("node", {}).get("nameOrPlaceholderName"),
                    "scrapedStatus": "PENDING",
                    "ingestionStatus": "PENDING",
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }
                
                existing_listings = await self.airbnb_model.get_airbnb_listings(filter)
                if existing_listings:
                    existing_listings = await self.airbnb_model.collection.find_one_and_update(filter, {"$set": airbnb_listing})
                    continue
                else:
                    inserted_ids = await self.airbnb_model.collection.insert_one(airbnb_listing)
                
           
            return {
                "success": True,
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create airbnb listings: {str(e)}"
            }
            
            