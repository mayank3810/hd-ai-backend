from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from bson import ObjectId
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.schemas.QueueStatus import CreateQueueStatusSchema, QueueStatusSchema
from app.helpers.Utilities import Utils
from app.dependencies import get_queue_status_service

router = APIRouter(prefix="/api/v1/queue", tags=["Queue Status"])

@router.post("/status", response_model=ServerResponse, status_code=201)
async def upsert_queue_status(
    queue_data: CreateQueueStatusSchema,
    service = Depends(get_queue_status_service),
    current_user = Depends(jwt_validator)
):
    """
    Create or update queue status for an operator.
    If the operator already has a queue entry, it will be updated.
    If pricelabs_id is provided and already exists, returns the existing entry.
    """
    try:
        data = await service.upsert_queue_status(queue_data)
        
        if not data["success"]:
            raise HTTPException(
                status_code=400,
                detail={"data": None, "error": data.get("error"), "success": False}
            )
        
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/status", response_model=ServerResponse)
async def get_queue_status(
    operator_id: str = Query(..., description="Operator ID to get queue status for"),
    pricelabs_id: Optional[str] = Query(None, description="Pricelabs property ID"),
    airbnb_id: Optional[str] = Query(None, description="Airbnb property ID"),
    booking_id: Optional[str] = Query(None, description="Booking.com property ID"),
    vrbo_id: Optional[str] = Query(None, description="VRBO property ID"),
    service = Depends(get_queue_status_service),
    current_user = Depends(jwt_validator)
):
    """
    Get queue status for a specific operator and platform IDs.
    Searches by operator_id AND (pricelabs_id OR airbnb_id OR booking_id OR vrbo_id).
    At least one platform ID should be provided for better results.
    """
    try:
        data = await service.get_queue_status_by_operator(
            operator_id, pricelabs_id, airbnb_id, booking_id, vrbo_id
        )
        
        if not data["success"]:
            raise HTTPException(
                status_code=400,
                detail={"data": None, "error": data.get("error"), "success": False}
            )
        
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail={"data": None, "error": str(e), "success": False}
        )

