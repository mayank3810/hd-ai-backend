from fastapi import APIRouter, Depends,HTTPException
from fastapi.responses import JSONResponse
from app.middleware.JWTVerification import jwt_validator
from app.schemas.User import ResetPassword, UpdateUserSchema
from app.services.Auth import AuthService
from app.schemas.ServerResponse import ServerResponse
from app.schemas.User import GetUserSchema, UserSchema,CreateUserSchema,ForgotPasswordRequest, AdminUpdateUserSchema, ApproveUserSchema
from app.helpers.Utilities import Utils
from app.dependencies import get_auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/signin", response_model=ServerResponse)
async def signin_user(body: GetUserSchema,  service: AuthService = Depends(get_auth_service)):
    try:
        data = await service.get_user(body.email,body.password)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False}) 
    
@router.post("/signup", response_model=ServerResponse)
async def signup(user_data: CreateUserSchema, auth_service: AuthService = Depends(get_auth_service)):
    try:
        data = await auth_service.signup(user_data)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})   
    
@router.post("/forgot-password", response_model=ServerResponse)
async def forgot_password(body:ForgotPasswordRequest, service:AuthService = Depends(get_auth_service)):
    try:
        data = await service.send_otp_email(body.email)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False}) 

@router.post("/reset-password", response_model=ServerResponse)
async def reset_password(password_data:ResetPassword, service:AuthService = Depends(get_auth_service)):
    try:
        data = await service.verify_otp_reset_password(password_data.email, password_data.otp, password_data.new_password)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False}) 

@router.get("/users/get-all-users", response_model=ServerResponse)
async def get_all_users(
    page: int=1,
    limit: int=10,
    service: AuthService = Depends(get_auth_service),
    jwt_payload: dict = Depends(jwt_validator)
    
):
    try:
        data = await service.get_all_users(page=page, limit=limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.get("/users/get-user-by-id/{user_id}", response_model=ServerResponse)
async def get_user_by_id(
    user_id: str,
    service: AuthService = Depends(get_auth_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.get_user_by_id(user_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.delete("/users/delete-user/{user_id}", response_model=ServerResponse)
async def delete_user(user_id: str, service: AuthService = Depends(get_auth_service),    jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.delete_user(user_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.put("/users/update-user/{user_id}", response_model=ServerResponse, )
async def update_user(user_id: str,body: AdminUpdateUserSchema,service: AuthService = Depends(get_auth_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        update_data = body.dict(exclude_unset=True)
        data = await service.update_user(user_id, update_data)
        return Utils.create_response(data.get("data"), data.get("success"), data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.put("/users/approve-user/{user_id}", response_model=ServerResponse)
async def approve_user(
    user_id: str,
    body: ApproveUserSchema,
    service: AuthService = Depends(get_auth_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.approve_user(user_id, body.isApproved)
        return Utils.create_response(data.get("data"), data.get("success"), data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

