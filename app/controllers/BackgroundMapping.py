# from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
# from pydantic import BaseModel, Field
# from typing import Optional
# import logging

# from app.services.BackgroundMapping import BackgroundMappingService
# from app.middleware.JWTVerification import jwt_validator

# # Set up logging
# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/api/v1/mapping", tags=["Data Mapping"])

# class MappingRequest(BaseModel):
#     operator_id: str = Field(..., description="Mandatory operator ID")
#     booking_id: Optional[str] = Field(None, description="Optional booking ID")
#     airbnb_id: Optional[str] = Field(None, description="Optional airbnb ID")
#     pricelabs_id: Optional[str] = Field(None, description="Optional pricelabs ID")

# class MappingResponse(BaseModel):
#     status: str
#     message: str
#     statistics: Optional[dict] = None

# @router.post("/", response_model=MappingResponse)
# async def start_data_mapping(
#     request: MappingRequest,
#     background_tasks: BackgroundTasks,
#     current_user: dict = Depends(jwt_validator)
# ):
#     """
#     Start data mapping task
    
#     This endpoint triggers a background task that will:
#     1. Find existing properties in Property collection based on operator_id and any one of the provided IDs
#     2. Get data from Listings and PricelabsAdminData collections
#     3. Update properties with mapped data
    
#     Args:
#         request: Mapping request with operator_id (mandatory) and at least one of booking_id, airbnb_id, or pricelabs_id
#         background_tasks: FastAPI background tasks handler
#         current_user: Authenticated user from JWT
        
#     Returns:
#         MappingResponse with task status and information
#     """
#     try:
#         logger.info(f"Starting data mapping task for operator: {request.operator_id}")
        
#         # Validate that at least one ID is provided
#         if not any([request.booking_id, request.airbnb_id, request.pricelabs_id]):
#             raise HTTPException(
#                 status_code=400,
#                 detail="At least one ID (booking_id, airbnb_id, or pricelabs_id) must be provided"
#             )
        
#         # Create mapping service instance
#         mapping_service = BackgroundMappingService()
        
#         # Start the background task
#         background_tasks.add_task(
#             mapping_service.execute_mapping,
#             request.operator_id,
#             request.booking_id,
#             request.airbnb_id,
#             request.pricelabs_id
#         )
        
#         logger.info(f"Data mapping task queued for operator: {request.operator_id}")
        
#         return MappingResponse(
#             status="success",
#             message=f"Data mapping task started for operator {request.operator_id}"
#         )
        
#     except Exception as e:
#         logger.error(f"Error starting data mapping task: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to start data mapping task: {str(e)}"
#         )
