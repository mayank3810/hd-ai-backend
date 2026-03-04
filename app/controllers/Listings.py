from enum import Enum
from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Depends, Header, status,Query,BackgroundTasks
from pydantic import ValidationError
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.schemas.Listings import CreateListing
from app.dependencies import get_listings_service

router = APIRouter(prefix="/api/v1/listings", tags=["Listings"])




@router.post("/scrape-listing", response_model=ServerResponse)
async def save_listing(
    body: CreateListing,
    background_tasks: BackgroundTasks,
    service = Depends(get_listings_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        background_tasks.add_task(service.save_listing, body)
        data = {
            "success": True,
            "data": {
                "message": "Scrapping listings"
            }
        }
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/get-property-urls", response_model=ServerResponse)
async def get_property_urls(
    operator_id: str = Query(..., description="Operator ID to filter properties"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    service = Depends(get_listings_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get property URLs sorted by creation date (newest first)"""
    try:
        result = await service.get_property_urls(operator_id, page, limit)
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.post("/scrape-and-map-listing", response_model=ServerResponse)
async def scrape_and_map_listing(
    id: str,
    service = Depends(get_listings_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Combined endpoint for scraping and mapping listings
    
    This endpoint performs both scraping and mapping operations in sequence:
    1. Updates property status to 'scraping_in_progress'
    2. Performs scraping operation
    3. If scraping succeeds, updates status to 'mapping_in_progress'
    4. Performs mapping operation
    5. Updates status to 'completed' on success, or appropriate error status on failure
    
    Status flow: pending -> scraping_in_progress -> mapping_in_progress -> completed
    Error statuses: error_in_scraping, error_in_mapping
    """
    try:
        result = await service.update_property_status(id)
        if not result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail={"data": None, "error": result["error"], "success": False}
                )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/get-booking-listings-by-operator-id", response_model=ServerResponse)
async def get_booking_listings_by_operator_id(
    operator_id: str = Query(..., description="Operator ID to filter properties"),
    service = Depends(get_listings_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_booking_listings_by_operator_id(operator_id)
        return Utils.create_response(result["data"], result["success"], result.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.post("/upload-excel-for-listing", response_model=ServerResponse)
async def upload_excel_for_listing(
    operator_id: str = Form(...),
    file: UploadFile = File(...),
    service = Depends(get_listings_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Upload an excel file for listing import queue
    
    This endpoint:
    1. Uploads the excel file to Azure Storage
    2. Saves the file URL and metadata to ExcelImportsForListing collection
    3. Creates a queue entry with status, operator_id, user_id, and creation timestamp
    """
    try:
        user_id = jwt_payload.get("user_id")
        result = await service.upload_excel_for_listing(file, operator_id, user_id)
        return Utils.create_response(result["data"], result["success"], result.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})