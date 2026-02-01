from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.FilterPreset import FilterPresetCreateSchema, FilterPresetUpdateSchema
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator

from app.dependencies import get_filter_preset_service

router = APIRouter(prefix="/api/v1/filter-presets", tags=["Filter Presets"])

@router.post("/create-filter-preset", response_model=ServerResponse, status_code=201)
async def create_filter_preset(
    filter_preset_data: FilterPresetCreateSchema,
    service = Depends(get_filter_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Convert to dict - no user_id needed, only operator_id
        filter_preset_dict = filter_preset_data.model_dump()
        
        result = await service.create_filter_preset_with_dict(filter_preset_dict)
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

@router.get("/get-filter-presets", response_model=ServerResponse)
async def get_filter_presets(
    operator_id: str = Query(..., description="Operator ID"),
    service = Depends(get_filter_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Get filter presets by operator_id only - no user_id needed
        result = await service.get_filter_presets_by_operator(operator_id)
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

@router.get("/get-filter-preset/{filter_preset_id}", response_model=ServerResponse)
async def get_filter_preset(
    filter_preset_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    service = Depends(get_filter_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Get filter preset by operator_id only - no user_id needed
        result = await service.get_filter_preset(filter_preset_id, operator_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Filter preset not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.put("/update-filter-preset/{filter_preset_id}", response_model=ServerResponse)
async def update_filter_preset(
    filter_preset_id: str,
    update_data: FilterPresetUpdateSchema,
    operator_id: str = Query(..., description="Operator ID"),
    service = Depends(get_filter_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Update filter preset by operator_id only - no user_id needed
        result = await service.update_filter_preset(filter_preset_id, update_data, operator_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Filter preset not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.delete("/delete-filter-preset/{filter_preset_id}", response_model=ServerResponse)
async def delete_filter_preset(
    filter_preset_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    service = Depends(get_filter_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Delete filter preset by operator_id only - no user_id needed
        result = await service.delete_filter_preset(filter_preset_id, operator_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Filter preset not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )
