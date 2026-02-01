from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List
from app.helpers.Utilities import Utils,ServerResponse
from app.middleware.JWTVerification import jwt_validator

from app.dependencies import get_airbnb_service

router = APIRouter(prefix="/api/v1/airbnb", tags=["Airbnb"])

class SaveAirbnbListingsRequest(BaseModel):
    operator_id: str = Field(..., description="Operator ID")
    listings: List[dict] = Field(..., description="List of booking listings to save")
    
@router.post("/save-airbnb-listings", response_model=ServerResponse)
async def save_airbnb_listings(
    request: SaveAirbnbListingsRequest,
    background_tasks: BackgroundTasks,
    service = Depends(get_airbnb_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        background_tasks.add_task(
            service.save_airbnb_listings,
            request.operator_id,
            request.listings
        )
        
        return Utils.create_response(
            f"Task queued to save {len(request.listings)} airbnb listing(s) for operator {request.operator_id}",
            True,
            ""
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})