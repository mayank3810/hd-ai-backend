from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.Operator import CreateOperator, OperatorUpdate
from app.helpers.Utilities import Utils,ServerResponse
from app.middleware.JWTVerification import jwt_validator
from app.dependencies import get_operator_service, get_pricelabs_service

router = APIRouter(prefix="/api/v1/operator", tags=["Operator"])


@router.post("/create", response_model=ServerResponse)
async def create_operator(
    body: CreateOperator,
    service = Depends(get_operator_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = await service.create_operator(body, user_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/list", response_model=ServerResponse)
async def list_operators(
    page: int=1,
    limit: int = 10,
    service = Depends(get_operator_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = await service.list_operators(page, limit,user_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/list/all", response_model=ServerResponse)
async def list_all_operators(
    page: int = 1,
    limit: int = 10,
    service = Depends(get_operator_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    List all operators regardless of user association.
    """
    try:
        data = await service.list_operators(page, limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.delete("/{operator_id}/users/{user_id}", response_model=ServerResponse)
async def remove_user_from_operator(
    operator_id: str,
    user_id: str,
    service = Depends(get_operator_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Remove a user association from an operator.
    """
    try:
        data = await service.remove_user_from_operator(operator_id, user_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/{operator_id}", response_model=ServerResponse)
async def get_operator(
    operator_id: str,
    service = Depends(get_operator_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.get_operator_by_id(operator_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})


@router.put("/update/{operator_id}", response_model=ServerResponse)
async def update_operator(
    operator_id: str,
    body: OperatorUpdate,
        service = Depends(get_operator_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data=await service.update_operator(operator_id, body.model_dump(exclude_unset=True))
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.delete("/delete/{operator_id}", response_model=ServerResponse)
async def delete_operator(
    operator_id: str,
    service = Depends(get_operator_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        await service.delete_operator(operator_id)
        return Utils.create_response({"operator_id": operator_id}, True, "Operator deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})


@router.get("/{operator_id}/pricelabs/listing/{listing_id}", response_model=ServerResponse)
async def get_pricelabs_listing_by_id(
    operator_id: str,
    listing_id: str,
    pricelabs_service = Depends(get_pricelabs_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    """
    Get a PriceLabs listing by ID using the operator's API key.
    
    Args:
        operator_id: The operator ID to get the API key from
        listing_id: The PriceLabs listing ID to fetch
    
    Returns:
        PriceLabs listing data
    """
    try:
        data = await pricelabs_service.get_listing_by_id_from_pricelabs(listing_id, operator_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})