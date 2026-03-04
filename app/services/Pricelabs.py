from app.models.PricelabsListings import PricelabsListingsModel
from bson import ObjectId
from fastapi import HTTPException
from app.models.Operator import OperatorModel
from datetime import datetime
from app.helpers.PricelabsHelper import PricelabsHelper

class PricelabsService:
    def __init__(self):
        self.pricelabs_model = PricelabsListingsModel()
        self.operator_model = OperatorModel()
    async def save_pricelabs_listings(self, operator_id: str) -> dict:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")
            
            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            pricelabs_cfg = getattr(operator, "priceLabs", None)
            if not pricelabs_cfg or not pricelabs_cfg.apiKey:
                return {
                    "success": False,
                    "data": None,
                    "error": "Operator not found or PriceLabs API key not configured"
                }
            
            # Use PricelabsHelper for API calls
            price_labs_helper = PricelabsHelper(pricelabs_cfg.apiKey)
            
            # Call API twice: once for all listings, once for synced listings only
            all_listings_response = price_labs_helper.get_all_listings(only_syncing_listings=False)
            synced_listings_response = price_labs_helper.get_all_listings(only_syncing_listings=True)
            
            # Process responses
            all_listings = all_listings_response.get("listings", [])
            synced_listings = synced_listings_response.get("listings", [])
            
            if not all_listings:
                return {
                    "success": False,
                    "data": None,
                    "error": "No listings found in PriceLabs API response"
                }
            
            # Create synced listing IDs set for O(1) lookup
            synced_listing_ids = {listing["id"] for listing in synced_listings}
            
            # Process listings with optimized data structure
            pricelabs_listings = []
            current_time = datetime.utcnow()
            
            # Use set for O(1) duplicate checking
            processed_listing_ids = set()
            
            for listing in all_listings:
                listing_id = listing["id"]
                
                # Skip duplicates
                if listing_id in processed_listing_ids:
                    continue
                
                # Determine sync status
                sync_status = listing_id in synced_listing_ids
                
                # Build listing data with minimal object creation
                listing_data = {
                    "listingId": listing_id,
                    "pms":listing.get("pms"),
                    "operatorId": operator_id,
                    "latitude": listing.get("latitude"),
                    "longitude": listing.get("longitude"),
                    "name": listing.get("name"),
                    "country": listing.get("country"),
                    "cityName": listing.get("city_name"),
                    "status": "PENDING",
                    "syncStatus": sync_status,
                    "createdAt": current_time,
                    "updatedAt": current_time
                }
                
                pricelabs_listings.append(listing_data)
                processed_listing_ids.add(listing_id)
            
            # Insert new listings
            existing_pricelabs_listings = await self.pricelabs_model.get_pricelabs_listings({"operatorId": operator_id})
            if existing_pricelabs_listings:
                await self.pricelabs_model.delete_pricelabs_listings(operator_id)
            inserted_ids = await self.pricelabs_model.create_pricelabs_listings(pricelabs_listings)
            
            return {
                "success": True,
                "data": {
                    "inserted_ids": inserted_ids,
                    "pricelabs_listings":pricelabs_listings,
                    "total_listings": len(pricelabs_listings),
                    "synced_listings": len(synced_listing_ids),
                    "inserted_count": len(inserted_ids)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to create pricelabs listings: {str(e)}"
            }
            
            


    async def get_pricelabs_data(self, page: int = 1, limit: int = 10,operator_id:str=None) -> dict:
        try:
            limit=limit
            total = await self.pricelabs_model.collection.count_documents({"operatorId":operator_id})
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            pricelabs_data = await self.pricelabs_model.get_pricelabs_listings_with_pagination({"operatorId":operator_id}, number_to_skip, limit)
            return {
                "success": True,
                "data": {
                    "pricelabs_data": pricelabs_data,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to list pricelabs listings: {str(e)}"
            }

    async def get_pricelabs_listing_by_id(self, operator_id: str) -> dict:
        try:
            pricelabs_listing = await self.pricelabs_model.get_pricelabs_listings({"operatorId": (operator_id)})
            if not pricelabs_listing:
                raise HTTPException(status_code=404, detail="Pricelabs listing not found")
            return {
                "success": True,
                "data": pricelabs_listing.model_dump()
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to get pricelabs listing: {str(e)}"
            }

    async def update_pricelabs_listings(self, operator_id: str, data: dict) -> dict:
        try:
            updated = await self.pricelabs_model.update_pricelabs_listings(operator_id, data)
            if not updated:
                raise HTTPException(status_code=404, detail="Pricelabs listing not found or not updated")
            return {
                "success": True,
                "data": "Pricelabs listing updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update pricelabs listing: {str(e)}"
            }

    async def delete_pricelabs_listings(self, operator_id: str) -> dict:
        try:
            data = await self.pricelabs_model.delete_pricelabs_listings(operator_id)
            return {
                "success": True,
                "data":  "Pricelabs listings deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete pricelabs listings: {str(e)}"
            }
