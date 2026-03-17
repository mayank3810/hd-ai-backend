"""Controller for Opportunities - list, delete, match-by-speaker (background job), and get matched."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.dependencies import get_opportunity_service

router = APIRouter(prefix="/api/v1/opportunities", tags=["Opportunities"])


@router.get("/", response_model=ServerResponse)
async def list_opportunities(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    service=Depends(get_opportunity_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    """List opportunities with pagination."""
    try:
        result = await service.list_opportunities(page=page, limit=limit)
        return Utils.create_response(result, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/match-by-speaker", response_model=ServerResponse)
async def match_opportunities_by_speaker(
    background_tasks: BackgroundTasks,
    speaker_profile_id: str = Query(..., description="Speaker profile ID"),
    service=Depends(get_opportunity_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    """
    Start a background job to match opportunities for this speaker and save to matchedOpportunities.
    Returns immediately with message; use GET /opportunities/matched?speaker_profile_id=... to fetch results.
    """
    try:
        background_tasks.add_task(service.run_matching_and_save, speaker_profile_id)
        return Utils.create_response(
            {
                "message": "Matching started",
                "speaker_profile_id": speaker_profile_id,
            },
            True,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/matched", response_model=ServerResponse)
async def get_matched_opportunities_by_speaker(
    speaker_profile_id: str = Query(..., description="Speaker profile ID"),
    service=Depends(get_opportunity_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    """
    Get matched opportunities for a speaker from the matchedOpportunities collection.
    Returns full opportunity documents whose ids are in the saved opportunities array for this speaker.
    """
    try:
        opportunities = await service.get_matched_opportunities_by_speaker_id(speaker_profile_id)
        return Utils.create_response({"opportunities": opportunities}, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.delete("/{opportunity_id}", response_model=ServerResponse)
async def delete_opportunity(
    opportunity_id: str,
    service=Depends(get_opportunity_service),
    jwt_payload: dict = Depends(jwt_validator),
):
    """Delete an opportunity by ID."""
    try:
        deleted = await service.delete_opportunity(opportunity_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={"data": None, "error": "Opportunity not found", "success": False},
            )
        return Utils.create_response({"message": "Opportunity deleted successfully"}, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )
