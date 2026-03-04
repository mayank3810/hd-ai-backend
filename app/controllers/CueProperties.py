from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.CueProperties import CuePropertyCreateSchema, CuePropertyUpdateSchema
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.dependencies import get_cue_properties_service

router = APIRouter(prefix="/api/v1/cue-properties", tags=["Cue Properties"])

@router.post("/create-cue-property", response_model=ServerResponse, status_code=201)
async def create_cue_property(
    cue_property_data: CuePropertyCreateSchema,
    service = Depends(get_cue_properties_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.create_cue_property(cue_property_data)
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

@router.get("/get-cue-properties/{operator_id}", response_model=ServerResponse)
async def get_cue_properties(
    operator_id: str,
    service = Depends(get_cue_properties_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_cue_properties({"operatorId": operator_id})
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

@router.get("/get-cue-property/{cue_property_id}", response_model=ServerResponse)
async def get_cue_property(
    cue_property_id: str,
    service = Depends(get_cue_properties_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_cue_property(cue_property_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Cue property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.put("/update-cue-property/{cue_property_id}", response_model=ServerResponse)
async def update_cue_property(
    cue_property_id: str,
    update_data: CuePropertyUpdateSchema,
    service = Depends(get_cue_properties_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.update_cue_property(cue_property_id, update_data)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Cue property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.delete("/delete-cue-property/{cue_property_id}", response_model=ServerResponse)
async def delete_cue_property(
    cue_property_id: str,
    service = Depends(get_cue_properties_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.delete_cue_property(cue_property_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Cue property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

