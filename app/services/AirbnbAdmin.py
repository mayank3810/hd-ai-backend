from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import HTTPException

from app.helpers.AirbnbAdmin import AirbnbAdmin
from app.models.Operator import OperatorModel
from app.models.AirbnbAdminDataModel import AirbnbAdminDataModel
import uuid


class AirbnbAdminService:
    """
    Service to retrieve Airbnb host dashboard listings using the persisted
    GraphQL query UnifiedListOfListingsQuery. Requires a valid Operator with
    stored Airbnb cookies.
    """

    def __init__(self) -> None:
        self.operator_model = OperatorModel()
        self.airbnb_admin_data_model = AirbnbAdminDataModel()

    async def list_host_listings(
        self,
        operator_id: str
    ) -> Dict[str, Any]:
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")

            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")

            airbnb_cfg = getattr(operator, "airbnb", None)
            if not airbnb_cfg or not airbnb_cfg.cookies:
                raise HTTPException(status_code=400, detail="Airbnb connection not configured for operator")
            
            airbnb_helper = AirbnbAdmin(cookies=airbnb_cfg.cookies, headless=True)
            try:
                await airbnb_helper.initialize(operator_id=operator_id)
                response = await airbnb_helper.save_listing_data(operator_id=operator_id)
                
                
                
                if response is None:
                    return {
                        "success": False,
                        "data": None,
                        "error": "Failed to authenticate with Airbnb - cookies may be expired or invalid",
                    }
                
                return {
                    "success": True,
                    "data": response
                }
            finally:
                await airbnb_helper.close()
        except HTTPException:
            # Re-raise HTTP exceptions to preserve status codes
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to fetch Airbnb host listings: {str(e)}",
            }

    async def scrape_all_listings_pricing_data(
        self,
        operator_id: str,
        max_listings: int = None
    ) -> Dict[str, Any]:
        """
        Scrape pricing data for all listings from Airbnb multicalendar page.
        
        Args:
            operator_id: The operator ID
            max_listings: Maximum number of listings to process (None for all)
            
        Returns:
            Dict containing all captured pricing data and metadata
        """
        try:
            if not ObjectId.is_valid(operator_id):
                raise HTTPException(status_code=400, detail="Invalid Operator ID")

            operator = await self.operator_model.get_operator({"_id": ObjectId(operator_id)})
            if not operator:
                raise HTTPException(status_code=404, detail="Operator not found")

            airbnb_cfg = getattr(operator, "airbnb", None)
            if not airbnb_cfg or not airbnb_cfg.cookies:
                raise HTTPException(status_code=400, detail="Airbnb connection not configured for operator")
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            airbnb_helper = AirbnbAdmin(cookies=airbnb_cfg.cookies, headless=True)
            try:
                await airbnb_helper.initialize(operator_id=operator_id)
                response = await airbnb_helper.save_listing_data(operator_id=operator_id)
                
                if response is None:
                    return {
                        "success": False,
                        "data": None,
                        "error": "Failed to authenticate with Airbnb - cookies may be expired or invalid",
                    }
                
                # Perform scraping
                scraping_result = await airbnb_helper.scrape_all_listings_pricing_data(max_listings)
                
                if not scraping_result["success"]:
                    return scraping_result
                
                # Prepare data for storage
                scraping_data = {
                    "session_id": session_id,
                    "operator_id": operator_id,
                    "listings_processed": scraping_result["data"]["listings_processed"],
                    "captured_responses": scraping_result["data"]["captured_responses"],
                    "listings_data": scraping_result["data"]["listings_data"],
                    "timestamp": scraping_result["data"]["timestamp"],
                    "success": True,
                    "error": None,
                    "max_listings": max_listings
                }
                
                # # Save to database using existing model
                # try:
                #     await self.airbnb_admin_data_model.save_airbnb_admin_data({
                #         "session_id": session_id,
                #         "operator_id": operator_id,
                #         "scraping_data": scraping_data,
                #         "createdAt": scraping_result["data"]["timestamp"],
                #         "updatedAt": scraping_result["data"]["timestamp"]
                #     })
                #     print(f"💾 Saved scraping session {session_id} to database")
                # except Exception as e:
                #     print(f"⚠️ Failed to save to database: {str(e)}")
                
                return {
                    "success": True,
                    "data": scraping_data,
                    "error": None
                }
                
            finally:
                await airbnb_helper.close()
                
        except HTTPException:
            # Re-raise HTTP exceptions to preserve status codes
            raise
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to scrape Airbnb listings: {str(e)}",
            }


