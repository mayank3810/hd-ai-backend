from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.CompetitorProperty import CompetitorPropertyCreateSchema, CompetitorPropertyUpdateSchema
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from typing import Union, List
from app.dependencies import get_competitor_property_service

router = APIRouter(prefix="/api/v1/competitor-properties", tags=["Competitor Properties"])

@router.post("/create-competitor", response_model=ServerResponse, status_code=201)
async def create_competitor_property(
    competitor_property_data: List[CompetitorPropertyCreateSchema],
    service = Depends(get_competitor_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Handle array of competitors
        result = await service.create_multiple_competitor_properties(competitor_property_data)
        
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

@router.delete("/delete-competitor/{competitor_property_id}", response_model=ServerResponse)
async def delete_competitor_property(
    competitor_property_id: str,
    service = Depends(get_competitor_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.delete_competitor_property(competitor_property_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/get-competitors-by-property/{property_id}", response_model=ServerResponse)
async def get_competitors_by_property_id(
    property_id: str,
    service = Depends(get_competitor_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_competitors_by_property_id(property_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

# @router.get("/get-competitor-properties-by-operator-id", response_model=ServerResponse)
# async def get_competitor_properties_by_operator_id(
#     operator_id: str = Query(..., description="Operator ID"),
#     page: int = Query(1, ge=1),
#     limit: int = Query(10, ge=1, le=100),
#     service = Depends(get_competitor_property_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         result = await service.get_competitor_properties_by_operator_id(operator_id, page, limit)
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=400,
#                 detail={"data": None, "error": result["error"], "success": False}
#             )
#         return Utils.create_response(result["data"], True)
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail={"data": None, "error": str(e), "success": False}
#         )

# @router.put("/update-competitor-property/{competitor_property_id}", response_model=ServerResponse)
# async def update_competitor_property(
#     competitor_property_id: str,
#     update_data: CompetitorPropertyUpdateSchema,
#     service = Depends(get_competitor_property_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         result = await service.update_competitor_property(competitor_property_id, update_data)
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=404 if result["error"] == "Competitor property not found" else 400,
#                 detail={"data": None, "error": result["error"], "success": False}
#             )
#         return Utils.create_response(result["data"], True)
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail={"data": None, "error": str(e), "success": False}
#         )

 ### Need to update
# @router.put("/update-photo-counts/{competitor_property_id}", response_model=ServerResponse)
# async def update_photo_counts(
#     competitor_property_id: str,
#     num_photos: int = Query(..., ge=0, description="Total number of photos"),
#     captioned_count: int = Query(..., ge=0, description="Number of photos with captions"),
#     missing_caption_count: int = Query(..., ge=0, description="Number of photos without captions"),
#     service = Depends(get_competitor_property_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     try:
#         result = await service.update_photo_counts(competitor_property_id, num_photos, captioned_count, missing_caption_count)
#         if not result["success"]:
#             raise HTTPException(
#                 status_code=404 if result["error"] == "Competitor property not found" else 400,
#                 detail={"data": None, "error": result["error"], "success": False}
#             )
#         return Utils.create_response(result["data"], True)
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail={"data": None, "error": str(e), "success": False}
#         )