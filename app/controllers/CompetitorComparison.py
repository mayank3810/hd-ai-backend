from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from typing import Literal
from app.dependencies import get_competitor_comparison_service

router = APIRouter(prefix="/api/v1/competitor-comparisons", tags=["Competitor Comparisons"])


@router.get("/get-comparisons", response_model=ServerResponse)
async def get_comparisons_by_operator_id(
    operator_id: str = Query(..., description="Operator ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_comparisons_by_operator_id(operator_id, page, limit)
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

@router.get("/get-property-competitors/{property_id}", response_model=ServerResponse)
async def get_property_with_competitors(
    property_id: str,
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_property_with_competitors_by_id(property_id)
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

# Competitor Review Analysis Endpoints

@router.get("/guest-didnt-like-in-competitor/{property_id}", response_model=ServerResponse)
async def get_guest_didnt_like_in_competitor(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get what guests didn't like about competitors for a specific property"""
    try:
        result = await service.get_competitor_review_analysis_by_type(property_id, operator_id, "DIDNTLIKE", platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/guest-wish-they-had-in-competitor/{property_id}", response_model=ServerResponse)
async def get_guest_wish_they_had_in_competitor(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get what guests wish they had in competitors for a specific property"""
    try:
        result = await service.get_competitor_review_analysis_by_type(property_id, operator_id, "WISHTOHAVE", platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/guest-loved-in-competitor/{property_id}", response_model=ServerResponse)
async def get_guest_loved_in_competitor(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get what guests loved about competitors for a specific property"""
    try:
        result = await service.get_competitor_review_analysis_by_type(property_id, operator_id, "LOVEDTOHAVE", platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/what-to-improve-based-on-competitor/{property_id}", response_model=ServerResponse)
async def get_what_to_improve_based_on_competitor(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get improvement suggestions based on competitor analysis for a specific property"""
    try:
        result = await service.get_improvement_suggestions_based_on_competitor(property_id, operator_id, platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

# Own Property Review Analysis Endpoints

@router.get("/guest-didnt-like-in-my-property/{property_id}", response_model=ServerResponse)
async def get_guest_didnt_like_in_my_property(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get what guests didn't like about your property"""
    try:
        result = await service.get_own_review_analysis_by_type(property_id, operator_id, "DIDNTLIKE", platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/guest-wish-they-had-my-property/{property_id}", response_model=ServerResponse)
async def get_guest_wish_they_had_my_property(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get what guests wish they had in your property"""
    try:
        result = await service.get_own_review_analysis_by_type(property_id, operator_id, "WISHTOHAVE", platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/guest-loved-in-my-property/{property_id}", response_model=ServerResponse)
async def get_guest_loved_in_my_property(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get what guests loved about your property"""
    try:
        result = await service.get_own_review_analysis_by_type(property_id, operator_id, "LOVEDTOHAVE", platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/what-to-improve-based-on-my-reviews/{property_id}", response_model=ServerResponse)
async def get_what_to_improve_based_on_my_reviews(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get improvement suggestions based on your property's reviews"""
    try:
        result = await service.get_improvement_suggestions_based_on_own_reviews(property_id, operator_id, platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/conversion-boosters-and-amenities/{property_id}", response_model=ServerResponse)
async def get_conversion_boosters_and_amenities(
    property_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Source platform"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get conversion boosters (with meta object popped) and top area amenities missing for a specific property and operator"""
    try:
        result = await service.get_conversion_boosters_and_amenities(operator_id, property_id, platform)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Competitor comparison not found for this property and operator" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/ai-photo-analysis", response_model=ServerResponse)
async def get_ai_photo_analysis(
    operator_id: str = Query(..., description="Operator ID"),
    property_id: str = Query(..., description="Property ID"),
    platform: Literal["booking", "airbnb"] = Query("booking", description="Platform: 'booking' or 'airbnb'"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get aiPhotoAnalysis object from database based on operator_id and propertyId for a specific platform"""
    try:
        result = await service.get_ai_photo_analysis(operator_id, property_id, platform)
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

@router.post("/add-to-queue", response_model=ServerResponse)
async def add_to_competitor_comparison_queue(
    property_id: str = Query(..., description="Owner Property ID"),
    operator_id: str = Query(..., description="Operator ID"),
    service = Depends(get_competitor_comparison_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Add a property to the competitor comparison queue"""
    try:
        result = await service.add_to_competitor_comparison_queue(operator_id,property_id)
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
