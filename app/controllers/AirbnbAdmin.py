from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.helpers.Utilities import Utils, ServerResponse
from app.middleware.JWTVerification import jwt_validator
from app.dependencies import get_airbnb_admin_service

router = APIRouter(prefix="/api/v1/airbnb-admin", tags=["Airbnb Admin"])



@router.get("/listings", response_model=ServerResponse)
async def list_airbnb_host_listings(
    operator_id: str,
    service = Depends(get_airbnb_admin_service),
    # jwt_payload: dict = Depends(jwt_validator),
):
    try:
        result = await service.list_host_listings(
            operator_id=operator_id)
        return Utils.create_response(result["data"], result["success"], result.get("error", ""))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.post("/scrape-all-listings", response_model=ServerResponse)
async def scrape_all_listings(
    operator_id: str,
    max_listings: int = None,
    background_tasks: BackgroundTasks = None,
    service = Depends(get_airbnb_admin_service)):
    """
    Scrape pricing data for all listings from Airbnb multicalendar page.
    This endpoint runs the scraping process in the background.
    """
    try:
        if background_tasks:
            # Start scraping in background
            background_tasks.add_task(
                service.scrape_all_listings_pricing_data,
                operator_id,
                max_listings
            )
            
            return Utils.create_response(
                {
                    "message": "Airbnb scraping process started in background",
                    "operator_id": operator_id,
                    "max_listings": max_listings
                },
                True,
                ""
            )
        else:
            # Run scraping synchronously
            result = await service.scrape_all_listings_pricing_data(operator_id, max_listings)
            return Utils.create_response(
                result["data"],
                result["success"],
                result.get("error", "")
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/scrape-all-listings-sync", response_model=ServerResponse)
async def scrape_all_listings_sync(
    operator_id: str,
    max_listings: int = None,
    service = Depends(get_airbnb_admin_service)):
    """
    Scrape pricing data for all listings from Airbnb multicalendar page.
    This endpoint runs the scraping process synchronously and returns results.
    """
    try:
        result = await service.scrape_all_listings_pricing_data(operator_id, max_listings)
        return Utils.create_response(
            result["data"],
            result["success"],
            result.get("error", "")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


