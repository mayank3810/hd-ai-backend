from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from typing import List
from app.dependencies import get_image_caption_service

router = APIRouter(prefix="/api/v1/image-captions", tags=["Image Captions"])

@router.post("/get-caption", response_model=ServerResponse)
async def get_image_caption(
    operator_id: str = Query(..., description="Operator ID"),
    property_id: str = Query(..., description="Property ID"),
    source: str = Query(..., description="Source platform (airbnb, booking, vrbo)"),
    image_url: str = Query(..., description="Image URL"),
    image_id: str = Query(..., description="Image ID"),
    service = Depends(get_image_caption_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get image caption by URL, generate if not exists, and save to CompetitorComparison"""
    try:
        result = await service.get_or_generate_caption_for_competitor(
            operator_id=operator_id,
            property_id=property_id,
            source=source,
            image_url=image_url,
            image_id=image_id
        )
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

# @router.get("/bulk-captions", response_model=ServerResponse)
# async def get_bulk_image_captions(
#     image_urls: List[str] = Query(..., description="List of image URLs to get captions for"),
#     service = Depends(get_image_caption_service),
#     jwt_payload: dict = Depends(jwt_validator)
# ):
#     """Get captions for multiple image URLs from the database"""
#     try:
#         result = await service.get_bulk_captions(image_urls)
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

@router.get("/captions-by-source", response_model=ServerResponse)
async def get_image_captions_by_source(
    operator_id: str = Query(..., description="Operator ID"),
    property_id: str = Query(..., description="Property ID"),
    source: str = Query(..., description="Source platform (airbnb, booking, vrbo)"),
    service = Depends(get_image_caption_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Return all image captions' ids and urls for a given operator, property and source"""
    try:
        result = await service.get_image_captions_by_source(
            operator_id=operator_id,
            property_id=property_id,
            source=source
        )
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
