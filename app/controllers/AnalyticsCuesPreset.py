from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.AnalyticsCuesPreset import AnalyticsCuesPresetCreateSchema
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator

from app.dependencies import get_analytics_cues_preset_service

router = APIRouter(prefix="/api/v1/analytics-cues-presets", tags=["Analytics Cues Presets"])

@router.post("/create-preset", response_model=ServerResponse, status_code=201)
async def create_analytics_cues_preset(
    preset_data: AnalyticsCuesPresetCreateSchema,
    service = Depends(get_analytics_cues_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.create_analytics_cues_preset(preset_data)
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

@router.get("/get-preset-operator", response_model=ServerResponse)
async def get_analytics_cues_presets(
    operator_id: str = Query(..., description="Operator ID"),
    service = Depends(get_analytics_cues_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_analytics_cues_presets_by_operator(operator_id)
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

@router.delete("/delete-preset/{preset_id}", response_model=ServerResponse)
async def delete_analytics_cues_preset(
    preset_id: str,
    operator_id: str = Query(..., description="Operator ID"),
    service = Depends(get_analytics_cues_preset_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.delete_analytics_cues_preset(preset_id, operator_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Analytics cues preset not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

