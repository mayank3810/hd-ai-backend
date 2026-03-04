
from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.BookingAdminData import BookingAdminData
from app.helpers.Utilities import Utils,ServerResponse
from app.middleware.JWTVerification import jwt_validator

from app.dependencies import get_booking_admin_service

router = APIRouter(prefix="/api/v1/booking-admin", tags=["Booking Admin"])


@router.get("/save-properties", response_model=ServerResponse)
async def save_booking_admin_data(
    operator_id: str,
    service = Depends(get_booking_admin_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.save_booking_admin_data(operator_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.put("/update-booking-admin-data", response_model=ServerResponse)
async def update_booking_admin_data(
    body: BookingAdminData,
    operator_id: str,
    service = Depends(get_booking_admin_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.update_booking_admin_data(operator_id, body.model_dump(exclude_unset=True))
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.get("/get_adult_child_config", response_model=ServerResponse)
async def get_adult_child_config(
    operator_id: str,
    property_id: str = Query(..., alias="propertyId"),
    service = Depends(get_booking_admin_service),
    # jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.get_adult_child_config(operator_id,property_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
    

@router.post("/map-and-save-booking-admin-data", response_model=ServerResponse)
async def map_and_save_booking_admin_data(
    operator_id: str,
    admin_data: dict,
    service = Depends(get_booking_admin_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.map_and_save_booking_admin_data(operator_id, admin_data)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
