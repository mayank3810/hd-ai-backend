from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.schemas.Property import PropertyCreateSchema, PropertyUpdateSchema, MinimalPropertyCreateSchema
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.dependencies import get_property_service

router = APIRouter(prefix="/api/v1/properties", tags=["Properties"])

@router.post("/create-property", response_model=ServerResponse, status_code=201)
async def create_property(
    property_data: MinimalPropertyCreateSchema,
    service = Depends(get_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Convert MinimalPropertyCreateSchema to full PropertyCreateSchema with default values
        property_dict = property_data.model_dump()
        full_property_data = PropertyCreateSchema(**property_dict)
        
        result = await service.create_property(full_property_data)
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

@router.get("/get-properties", response_model=ServerResponse)
async def get_properties(
    operator_id: str = Query(..., description="Filter properties by operator ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("_id", description="Field to sort by: _id, Listing_Name, Occupancy.NM, Occupancy.TM"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    service = Depends(get_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        query = {}
        if operator_id:
            query["operator_id"] = operator_id
            
        # Set sort order (-1 for descending, 1 for ascending)
        sort_direction = -1 if sort_order.lower() == "desc" else 1
        
        # Validate sort field and create sort_by dict
        valid_sort_fields = ["_id", "Listing_Name", "Occupancy.NM", "Occupancy.TM"]
        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=400,
                detail={"data": None, "error": f"Invalid sort field. Must be one of: {valid_sort_fields}", "success": False}
            )
        
        sort_by_dict = {sort_by: sort_direction}
        
        result = await service.get_properties_projected(page, limit, query, sort_by_dict)
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

@router.get("/get-property/{property_id}", response_model=ServerResponse)
async def get_property(
    property_id: str,
    operator_id: str,
    service = Depends(get_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.get_property(property_id, operator_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.put("/update-property/{property_id}", response_model=ServerResponse)
async def update_property(
    property_id: str,
    update_data: PropertyUpdateSchema,
    service = Depends(get_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.update_property(property_id, update_data)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": result["error"], "success": False}
        )

@router.delete("/delete-property/{property_id}", response_model=ServerResponse)
async def delete_property(
    property_id: str,
    operator_id: str,
    service = Depends(get_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.delete_property(property_id, operator_id)
        if not result["success"]:
            raise HTTPException(
                status_code=404 if result["error"] == "Property not found" else 400,
                detail={"data": None, "error": result["error"], "success": False}
            )
        return Utils.create_response(result["data"], True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/search-properties", response_model=ServerResponse)
async def search_properties(
    search_query: str = Query(..., description="Search query for listing name"),
    operator_id: str = Query(..., description="Filter by operator ID"),
    service = Depends(get_property_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        result = await service.search_properties(search_query, operator_id)
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

@router.get("/filter-properties", response_model=ServerResponse)
async def filter_properties(
    jwt_payload: dict = Depends(jwt_validator),
    # Basic Filters
    operator_id: str = Query(..., description="Operator ID filter"),
    area: str = Query(None, description="Area filter"),
    room_type: str = Query(None, description="Room type filter"),
    adr_min: float = Query(None, description="Minimum ADR (TM)"),
    adr_max: float = Query(None, description="Maximum ADR (TM)"),
    revpar_min: float = Query(None, description="Minimum RevPAR (TM)"),
    revpar_max: float = Query(None, description="Maximum RevPAR (TM)"),
    mpi_min: float = Query(None, description="Minimum MPI"),
    mpi_max: float = Query(None, description="Maximum MPI"),
    min_rate_threshold_min: float = Query(None, description="Minimum Rate Threshold"),
    min_rate_threshold_max: float = Query(None, description="Maximum Rate Threshold"),

    # Occupancy Filters
    occ_tm_min: float = Query(None, description="Minimum Occupancy TM"),
    occ_tm_max: float = Query(None, description="Maximum Occupancy TM"),
    occ_nm_min: float = Query(None, description="Minimum Occupancy NM"),
    occ_nm_max: float = Query(None, description="Maximum Occupancy NM"),
    occ_7days_min: float = Query(None, description="Minimum 7 Days Occupancy"),
    occ_7days_max: float = Query(None, description="Maximum 7 Days Occupancy"),
    occ_30days_min: float = Query(None, description="Minimum 30 Days Occupancy"),
    occ_30days_max: float = Query(None, description="Maximum 30 Days Occupancy"),
    pickup_7days_min: float = Query(None, description="Minimum 7 Days Pickup"),
    pickup_7days_max: float = Query(None, description="Maximum 7 Days Pickup"),
    pickup_14days_min: float = Query(None, description="Minimum 14 Days Pickup"),
    pickup_14days_max: float = Query(None, description="Maximum 14 Days Pickup"),
    pickup_30days_min: float = Query(None, description="Minimum 30 Days Pickup"),
    pickup_30days_max: float = Query(None, description="Maximum 30 Days Pickup"),

    # Performance Filters
    stly_occ_min: float = Query(None, description="Minimum STLY Occupancy Variance"),
    stly_occ_max: float = Query(None, description="Maximum STLY Occupancy Variance"),
    stly_adr_min: float = Query(None, description="Minimum STLY ADR Variance"),
    stly_adr_max: float = Query(None, description="Maximum STLY ADR Variance"),
    stly_revpar_min: float = Query(None, description="Minimum STLY RevPAR Variance"),
    stly_revpar_max: float = Query(None, description="Maximum STLY RevPAR Variance"),
    stlm_occ_min: float = Query(None, description="Minimum STLM Occupancy Variance"),
    stlm_occ_max: float = Query(None, description="Maximum STLM Occupancy Variance"),
    stlm_adr_min: float = Query(None, description="Minimum STLM ADR Variance"),
    stlm_adr_max: float = Query(None, description="Maximum STLM ADR Variance"),
    stlm_revpar_min: float = Query(None, description="Minimum STLM RevPAR Variance"),
    stlm_revpar_max: float = Query(None, description="Maximum STLM RevPAR Variance"),

    # Platform Features
    booking_genius: bool = Query(None, description="Booking.com Genius Program"),
    booking_mobile: bool = Query(None, description="Booking.com Mobile Deals"),
    booking_preferred: bool = Query(None, description="Booking.com Preferred Partner"),
    booking_weekly: bool = Query(None, description="Booking.com Weekly Discounts"),
    booking_monthly: bool = Query(None, description="Booking.com Monthly Discounts"),
    booking_lastminute: bool = Query(None, description="Booking.com Last Minute Discount"),
    
    airbnb_weekly: bool = Query(None, description="Airbnb Weekly Discounts"),
    airbnb_monthly: bool = Query(None, description="Airbnb Monthly Discounts"),
    airbnb_member: bool = Query(None, description="Airbnb Member Discount"),
    airbnb_lastminute: bool = Query(None, description="Airbnb Last Minute Discount"),
    
    vrbo_weekly: bool = Query(None, description="VRBO Weekly Discounts"),
    vrbo_monthly: bool = Query(None, description="VRBO Monthly Discounts"),

    # Review Filters
    booking_review_min: float = Query(None, description="Minimum Booking.com Review Score"),
    booking_review_max: float = Query(None, description="Maximum Booking.com Review Score"),
    booking_total_reviews_min: int = Query(None, description="Minimum Booking.com Total Reviews"),
    booking_total_reviews_max: int = Query(None, description="Maximum Booking.com Total Reviews"),
    
    airbnb_review_min: float = Query(None, description="Minimum Airbnb Review Score"),
    airbnb_review_max: float = Query(None, description="Maximum Airbnb Review Score"),
    airbnb_total_reviews_min: int = Query(None, description="Minimum Airbnb Total Reviews"),
    airbnb_total_reviews_max: int = Query(None, description="Maximum Airbnb Total Reviews"),
    
    vrbo_review_min: float = Query(None, description="Minimum VRBO Review Score"),
    vrbo_review_max: float = Query(None, description="Maximum VRBO Review Score"),
    vrbo_total_reviews_min: int = Query(None, description="Minimum VRBO Total Reviews"),
    vrbo_total_reviews_max: int = Query(None, description="Maximum VRBO Total Reviews"),

    # Property IDs filter
    property_ids: List[str] = Query(None, description="Array of property IDs to filter"),

    # Pagination
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    service = Depends(get_property_service)
):
    try:
        filters = {
            # Basic Filters
            "operator_id": operator_id,
            "area": area,
            "room_type": room_type,
            "adr_range": {"min": adr_min, "max": adr_max},
            "revpar_range": {"min": revpar_min, "max": revpar_max},
            "mpi_range": {"min": mpi_min, "max": mpi_max},
            "min_rate_threshold": {"min": min_rate_threshold_min, "max": min_rate_threshold_max},

            # Occupancy Filters
            "occupancy": {
                "tm": {"min": occ_tm_min, "max": occ_tm_max},
                "nm": {"min": occ_nm_min, "max": occ_nm_max},
                "7_days": {"min": occ_7days_min, "max": occ_7days_max},
                "30_days": {"min": occ_30days_min, "max": occ_30days_max}
            },
            "pickup": {
                "7_days": {"min": pickup_7days_min, "max": pickup_7days_max},
                "14_days": {"min": pickup_14days_min, "max": pickup_14days_max},
                "30_days": {"min": pickup_30days_min, "max": pickup_30days_max}
            },

            # Performance Filters
            "stly_var": {
                "occupancy": {"min": stly_occ_min, "max": stly_occ_max},
                "adr": {"min": stly_adr_min, "max": stly_adr_max},
                "revpar": {"min": stly_revpar_min, "max": stly_revpar_max}
            },
            "stlm_var": {
                "occupancy": {"min": stlm_occ_min, "max": stlm_occ_max},
                "adr": {"min": stlm_adr_min, "max": stlm_adr_max},
                "revpar": {"min": stlm_revpar_min, "max": stlm_revpar_max}
            },

            # Platform Features
            "booking_features": {
                "genius": booking_genius,
                "mobile": booking_mobile,
                "preferred": booking_preferred,
                "weekly": booking_weekly,
                "monthly": booking_monthly,
                "lastminute": booking_lastminute
            },
            "airbnb_features": {
                "weekly": airbnb_weekly,
                "monthly": airbnb_monthly,
                "member": airbnb_member,
                "lastminute": airbnb_lastminute
            },
            "vrbo_features": {
                "weekly": vrbo_weekly,
                "monthly": vrbo_monthly
            },

            # Review Filters
            "reviews": {
                "booking": {
                    "score": {"min": booking_review_min, "max": booking_review_max},
                    "total": {"min": booking_total_reviews_min, "max": booking_total_reviews_max}
                },
                "airbnb": {
                    "score": {"min": airbnb_review_min, "max": airbnb_review_max},
                    "total": {"min": airbnb_total_reviews_min, "max": airbnb_total_reviews_max}
                },
                "vrbo": {
                    "score": {"min": vrbo_review_min, "max": vrbo_review_max},
                    "total": {"min": vrbo_total_reviews_min, "max": vrbo_total_reviews_max}
                }
            }
        }

        result = await service.filter_properties(filters, page, limit, property_ids)
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
