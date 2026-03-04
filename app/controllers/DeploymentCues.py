from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.DeploymentCues import (
    DeploymentCueCreateSchema, 
    DeploymentCueUpdateSchema,
    AddNoteSchema,
    AssignUserSchema
)
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.dependencies import get_deployment_cues_service

router = APIRouter(prefix="/api/v1/deployment-cues", tags=["Deployment Cues"])

@router.post("/create", response_model=ServerResponse, status_code=201)
async def create_deployment_cue(
    deployment_cue_data: DeploymentCueCreateSchema,
    service = Depends(get_deployment_cues_service), 
    jwt_payload: dict = Depends(jwt_validator)
):
    """Create a new deployment cue"""
    try:
        result = await service.create_deployment_cue(deployment_cue_data)
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

@router.get("/get-deployment-cues", response_model=ServerResponse)
async def get_deployment_cues(
    operator_id: str = Query(None, description="Filter deployment cues by operator ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_order: str = Query("desc", description="Sort order for creation date (asc/desc)"),
    service = Depends(get_deployment_cues_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get all deployment cues with pagination and sorting"""
    try:
        query = {}
        if operator_id:
            query["operatorId"] = operator_id
            
        # Set sort order (-1 for descending, 1 for ascending)
        sort_by = {"_id": -1 if sort_order.lower() == "desc" else 1}
        
        result = await service.get_deployment_cues(page, limit, query, sort_by)
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
@router.put("/update/{deployment_cue_id}", response_model=ServerResponse)
async def update_deployment_cue(
    deployment_cue_id: str,
    update_data: DeploymentCueUpdateSchema,
    service = Depends(get_deployment_cues_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Update a deployment cue"""
    try:
        result = await service.update_deployment_cue(deployment_cue_id, update_data)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Deployment cue not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.delete("/delete/{deployment_cue_id}", response_model=ServerResponse)
async def delete_deployment_cue(
    deployment_cue_id: str,
    service = Depends(get_deployment_cues_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Delete a deployment cue"""
    try:
        result = await service.delete_deployment_cue(deployment_cue_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Deployment cue not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )
