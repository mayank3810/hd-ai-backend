"""
Admin-only user management API with speaker profile summaries per user.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_user_management_service
from app.helpers.auth_roles import is_admin_role
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.schemas.User import AdminCreateUserSchema, AdminUpdateUserSchema

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


def _admin_id(jwt_payload: dict) -> str:
    admin_id = jwt_payload.get("user_id") or jwt_payload.get("id") or str(
        jwt_payload.get("_id")
    )
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "data": None,
                "error": "Admin ID not found in JWT token",
                "success": False,
            },
        )
    return admin_id


def _require_admin(jwt_payload: dict) -> None:
    if not is_admin_role(jwt_payload.get("userType")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "data": None,
                "error": "Only admins can access this resource",
                "success": False,
            },
        )


@router.get("", response_model=ServerResponse)
async def list_users_with_profiles(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    service=Depends(get_user_management_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    _require_admin(jwt_payload)
    try:
        data = await service.list_users_with_profiles(page=page, limit=limit)
        if not data["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "data": None,
                    "error": data.get("error", ""),
                    "success": False,
                },
            )
        return Utils.create_response(data["data"], True, "")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/{user_id}", response_model=ServerResponse)
async def get_user_with_profiles(
    user_id: str,
    service=Depends(get_user_management_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    _require_admin(jwt_payload)
    try:
        data = await service.get_user_with_profiles(user_id)
        if not data["success"]:
            code = (
                status.HTTP_404_NOT_FOUND
                if data.get("error") == "User not found"
                else status.HTTP_400_BAD_REQUEST
            )
            raise HTTPException(
                status_code=code,
                detail={
                    "data": None,
                    "error": data.get("error", ""),
                    "success": False,
                },
            )
        return Utils.create_response(data["data"], True, "")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: AdminCreateUserSchema,
    service=Depends(get_user_management_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    _require_admin(jwt_payload)
    admin_id = _admin_id(jwt_payload)
    try:
        data = await service.create_user_by_admin(user_data, admin_id)
        if not data["success"]:
            err = data.get("error", "")
            status_code = (
                status.HTTP_409_CONFLICT
                if "already exists" in err.lower()
                else status.HTTP_400_BAD_REQUEST
            )
            raise HTTPException(
                status_code=status_code,
                detail={"data": None, "error": err, "success": False},
            )
        return Utils.create_response(data["data"], True, "")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.put("/{user_id}", response_model=ServerResponse)
async def update_user(
    user_id: str,
    body: AdminUpdateUserSchema,
    service=Depends(get_user_management_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    _require_admin(jwt_payload)
    try:
        data = await service.update_user_admin(user_id, body)
        if not data["success"]:
            code = (
                status.HTTP_404_NOT_FOUND
                if data.get("error") == "User not found"
                else status.HTTP_400_BAD_REQUEST
            )
            raise HTTPException(
                status_code=code,
                detail={
                    "data": None,
                    "error": data.get("error", ""),
                    "success": False,
                },
            )
        return Utils.create_response(data["data"], True, "")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.delete("/{user_id}", response_model=ServerResponse)
async def delete_user(
    user_id: str,
    service=Depends(get_user_management_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    _require_admin(jwt_payload)
    try:
        data = await service.delete_user(user_id)
        if not data["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "data": None,
                    "error": data.get("error", ""),
                    "success": False,
                },
            )
        return Utils.create_response(data["data"], True, "")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"data": None, "error": str(e), "success": False},
        )
