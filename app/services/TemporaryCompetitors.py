from app.models.BookingTemporaryCompetitor import BookingTemporaryCompetitorsModel
from app.models.AirbnbTemporaryCompetitor import AirbnbTemporaryCompetitorsModel
from bson import ObjectId
from fastapi import HTTPException
from datetime import datetime
from pymongo import ReplaceOne

class TemporaryCompetitorsService:
    def __init__(self):
        self.booking_temporary_competitors_model = BookingTemporaryCompetitorsModel()
        self.airbnb_temporary_competitors_model = AirbnbTemporaryCompetitorsModel()
        
    async def save_booking_temporary_competitor(self, operator_id: str, booking_id: str, competitors_data: list[dict]) -> dict:
        try:
            if not competitors_data:
                return {
                    "success": True,
                    "data": {"inserted": 0, "updated": 0, "total": 0}
                }
            
            current_time = datetime.utcnow()
            
            # Prepare bulk operations
            bulk_operations = []
            
            for competitor in competitors_data:
                competitor_property_id = competitor.get("hotelId")
                filter_query = {
                    "operatorId": operator_id,
                    "ownPropertyId": booking_id,
                    "competitorPropetyId": competitor_property_id
                }
                
                payload = {
                    "operatorId": operator_id,
                    "ownPropertyId": booking_id,
                    "competitorPropetyId": competitor_property_id,
                    "name": competitor.get("name"),
                    "distance": competitor.get("distance"),
                    "score": competitor.get("score"),
                    "stars": competitor.get("stars"),
                    "competitorBookingUrl": competitor.get("publicURL"),
                    "createdAt": current_time,
                    "updatedAt": current_time
                }
                
                # Add replace_one operation to bulk operations
                bulk_operations.append(
                    ReplaceOne(
                        filter=filter_query,
                        replacement=payload,
                        upsert=True
                    )
                )
            
            # Execute bulk operations
            result = await self.booking_temporary_competitors_model.collection.bulk_write(bulk_operations)
            
            return {
                "success": True,
                "data": {
                    "inserted": result.upserted_count,
                    "updated": result.modified_count,
                    "total": result.upserted_count + result.modified_count
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create temporary competitors: {str(e)}"
            }
            
            
    async def save_airbnb_temporary_competitor(self, operator_id: str, pricelabs_listing_id: str, competitors_data: list[dict]) -> dict:
        try:
            if not competitors_data:
                return {
                    "success": True,
                    "data": {"inserted": 0, "updated": 0, "total": 0}
                }
            
            current_time = datetime.utcnow()
            
            # Prepare bulk operations
            bulk_operations = []
            
            for competitor in competitors_data:
                listing_id = competitor.get("listing_id")
                filter_query = {
                    "operatorId": operator_id,
                    "ownPricelabsListingId": pricelabs_listing_id,
                    "listing_id": listing_id
                }
                
                payload = {
                    "operatorId": operator_id,
                    "ownPricelabsListingId": pricelabs_listing_id,
                    "base_guests": competitor.get("base_guests"),
                    "bedrooms": competitor.get("bedrooms"),
                    "lat": competitor.get("lat"),
                    "competitorAirbnbUrl": competitor.get("link"),
                    "competitorPropertyId": competitor.get("listing_id"),
                    "listing_title": competitor.get("listing_title"),
                    "lng": competitor.get("lng"),
                    "min_stay": competitor.get("min_stay"),
                    "percentile": competitor.get("percentile"),
                    "picture_url": competitor.get("picture_url"),
                    "price": competitor.get("price"),
                    "review_count": competitor.get("review_count"),
                    "star_rating": competitor.get("star_rating"),
                    "createdAt": current_time,
                    "updatedAt": current_time
                }
                
                # Add replace_one operation to bulk operations
                bulk_operations.append(
                    ReplaceOne(
                        filter=filter_query,
                        replacement=payload,
                        upsert=True
                    )
                )
            
            # Execute bulk operations
            result = await self.airbnb_temporary_competitors_model.collection.bulk_write(bulk_operations)
            
            return {
                "success": True,
                "data": {
                    "inserted": result.upserted_count,
                    "updated": result.modified_count,
                    "total": result.upserted_count + result.modified_count
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create temporary competitors: {str(e)}"
            }
    
    async def delete_booking_temporary_competitor_by_operator_id(self, operator_id: str) -> dict:
        try:
            filter_query = {"operatorId": operator_id}
            result = await self.booking_temporary_competitors_model.collection.delete_many(filter_query)
            
            return {
                "success": True,
                "data": {
                    "deleted_count": result.deleted_count,
                    "operator_id": operator_id
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete booking temporary competitors: {str(e)}"
            }
    
    async def delete_airbnb_temporary_competitor_by_operator_id(self, operator_id: str) -> dict:
        try:
            filter_query = {"operatorId": operator_id}
            result = await self.airbnb_temporary_competitors_model.collection.delete_many(filter_query)
            
            return {
                "success": True,
                "data": {
                    "deleted_count": result.deleted_count,
                    "operator_id": operator_id
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete airbnb temporary competitors: {str(e)}"
            }