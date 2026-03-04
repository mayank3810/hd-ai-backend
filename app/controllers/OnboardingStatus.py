from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from bson import ObjectId
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.schemas.OnboardingStatus import CreateOnboardingStatusSchema, OnboardingStatusSchema
from app.helpers.Utilities import Utils
from app.dependencies import get_onboarding_status_service

router = APIRouter(prefix="/api/v1/onboarding", tags=["Onboarding Status"])

@router.post("/status", response_model=ServerResponse, status_code=201)
async def create_onboarding_status(
    onboarding_data: CreateOnboardingStatusSchema,
    service = Depends(get_onboarding_status_service),
    current_user = Depends(jwt_validator)
):
    """
    Create or update onboarding status for the operator (operator_id based).
    """
    try:
        data = await service.create_onboarding_status(onboarding_data)
        
        if not data["success"]:
            raise HTTPException(
                status_code=400,
                detail={"data": None, "error": data.get("error"), "success": False}
            )
        
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail={"data": None, "error": str(e), "success": False}
        )


