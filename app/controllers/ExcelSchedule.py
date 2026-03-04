from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.schemas.ExcelSchedule import ExcelScheduleCreateSchema
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator

from app.dependencies import get_excel_schedule_service

router = APIRouter(prefix="/api/v1/excel-schedule", tags=["Excel Schedule"])

@router.post("/create", response_model=ServerResponse, status_code=201)
async def create_excel_schedule(
    schedule_data: ExcelScheduleCreateSchema,
    background_tasks: BackgroundTasks,
    service = Depends(get_excel_schedule_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Create Excel file in background"""
    try:
        result = await service.create_excel_schedule(schedule_data, background_tasks)
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

@router.get("/get/{schedule_id}", response_model=ServerResponse)
async def get_excel_schedule(
    schedule_id: str,
    service = Depends(get_excel_schedule_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """Get Excel schedule by ID"""
    try:
        result = await service.get_excel_schedule(schedule_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Excel schedule not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

