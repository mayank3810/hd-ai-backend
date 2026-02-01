from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List
from app.helpers.Utilities import Utils,ServerResponse
from app.middleware.JWTVerification import jwt_validator
from app.dependencies import get_temporary_competitor_service

router = APIRouter(prefix="/api/v1/temporary-competitor", tags=["Temporary Competitor"])

class SaveBookingTemporaryCompetitorRequest(BaseModel):
    operator_id: str = Field(..., description="Operator ID")
    booking_id: str = Field(..., description="Booking ID")
    competitors_data: List[dict] = Field(..., description="List of booking temporary competitors to save")
    
class SaveAirbnbTemporaryCompetitorRequest(BaseModel):
    operator_id: str = Field(..., description="Operator ID")
    pricelabs_listing_id: str = Field(..., description="Pricelabs Listing ID")
    competitors_data: List[dict] = Field(..., description="List of airbnb temporary competitors to save")
    
@router.post("/save-booking-temporary-competitor", response_model=ServerResponse)
async def save_booking_temporary_competitor(
    request: SaveBookingTemporaryCompetitorRequest,
    service = Depends(get_temporary_competitor_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.save_booking_temporary_competitor(request.operator_id, request.booking_id, request.competitors_data)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.post("/save-airbnb-temporary-competitor", response_model=ServerResponse)
async def save_airbnb_temporary_competitor(
    request: SaveAirbnbTemporaryCompetitorRequest,
    service = Depends(get_temporary_competitor_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.save_airbnb_temporary_competitor(request.operator_id, request.pricelabs_listing_id, request.competitors_data)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.delete("/delete-booking-temporary-competitor/{operator_id}", response_model=ServerResponse)
async def delete_booking_temporary_competitor(
    operator_id: str,
    service = Depends(get_temporary_competitor_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.delete_booking_temporary_competitor_by_operator_id(operator_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.delete("/delete-airbnb-temporary-competitor/{operator_id}", response_model=ServerResponse)
async def delete_airbnb_temporary_competitor(
    operator_id: str,
    service = Depends(get_temporary_competitor_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.delete_airbnb_temporary_competitor_by_operator_id(operator_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})