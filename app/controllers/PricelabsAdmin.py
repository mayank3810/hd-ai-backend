
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.schemas.PricelabsAdminData import PricelabsAdminData
from app.helpers.Utilities import Utils,ServerResponse
from app.middleware.JWTVerification import jwt_validator

from app.dependencies import get_pricelabs_admin_service

router = APIRouter(prefix="/api/v1/pricelabs-admin", tags=["Pricelabs Admin"])
@router.get("/save-price-labs-admin-data", response_model=ServerResponse)
async def save_price_labs_admin_data(
    operator_id: str,
    background_tasks: BackgroundTasks,
    service = Depends(get_pricelabs_admin_service),
    _jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.save_price_labs_admin_data(operator_id, background_tasks)
        return Utils.create_response(data.get("data"), data.get("success", False), data.get("error", ""))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/analytics-report", response_model=ServerResponse)
async def create_analytics_report(
    operator_id: str = Query(..., description="Operator ID"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD"),
    service = Depends(get_pricelabs_admin_service),
    _jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.create_analytics_report(operator_id, start_date, end_date)
        return Utils.create_response(data.get("data"), data.get("success", False), data.get("error", ""))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/get-analytics-report/{report_id}", response_model=ServerResponse)
async def get_analytics_report(
    report_id: str,
    service = Depends(get_pricelabs_admin_service),
    _jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.get_analytics_report_by_id(report_id)
        return Utils.create_response(data.get("data"), data.get("success", False), data.get("error", ""))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
