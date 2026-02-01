from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.helpers.Utilities import Utils,ServerResponse
from app.middleware.JWTVerification import jwt_validator

from app.dependencies import get_pricelabs_service

router = APIRouter(prefix="/api/v1/pricelabs", tags=["Pricelabs"])
    
# @router.get("/list-pricelabs-listings", response_model=ServerResponse)
# async def list_pricelabs_listings(
#     operator_id: str,
#     service = Depends(get_pricelabs_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         data = await service.list_pricelabs_data(operator_id)
#         return Utils.create_response(data["data"], data["success"], data.get("error", ""))
#     except Exception as e:
#         raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get("/save-pricelabs-listings", response_model=ServerResponse)
async def save_pricelabs_listings(
    operator_id: str,
    service = Depends(get_pricelabs_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.save_pricelabs_listings(operator_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
# @router.get("/save-data-specific-overides", response_model=ServerResponse)
# async def save_data_specific_overides(
#     operator_id: str,
#     pricelabs_listing_id: str,
#     service = Depends(get_pricelabs_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         data = await service.save_data_specific_overides(operator_id, pricelabs_listing_id)
#         return Utils.create_response(data["data"], data["success"], data.get("error", ""))
#     except Exception as e:
#         raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
    
# @router.get("/save-rate-plans", response_model=ServerResponse)
# async def save_rate_plans(
#     operator_id: str,
#     pricelabs_listing_id: str,
#     service = Depends(get_pricelabs_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         data = await service.save_rate_plans(operator_id, pricelabs_listing_id)
#         return Utils.create_response(data["data"], data["success"], data.get("error", ""))
#     except Exception as e:
#         raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

# @router.get("/save-neighborhood-data", response_model=ServerResponse)
# async def save_neighborhood_data(
#     operator_id: str,
#     pricelabs_listing_id: str,
#     service = Depends(get_pricelabs_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         data = await service.save_neighborhood_data(operator_id, pricelabs_listing_id)
#         return Utils.create_response(data["data"], data["success"], data.get("error", ""))
#     except Exception as e:
#         raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

# @router.get("/reservation-data", response_model=ServerResponse)
# async def reservation_data(
#     operator_id: str,
#     pricelabs_listing_id: str,
#     service = Depends(get_pricelabs_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         data = await service.fetch_reservation_data(
#             operator_id=operator_id,
#             pricelabs_listing_id=pricelabs_listing_id,
#         )
#         return Utils.create_response(data["data"], data["success"], data.get("error", ""))
#     except Exception as e:
#         raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
    
    
