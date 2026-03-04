"""
Speaker options: GET speaker topics and GET target audiences.
Separate route for catalog data used in speaker profile flows.
"""
from fastapi import APIRouter, Depends

from app.dependencies import get_speaker_topics_model, get_speaker_target_audience_model
from app.helpers.Utilities import Utils
from app.schemas.ServerResponse import ServerResponse

router = APIRouter(prefix="/api/v1/speaker-options", tags=["Speaker Options"])


@router.get("/topics", response_model=ServerResponse)
async def get_speaker_topics(
    model=Depends(get_speaker_topics_model),
):
    """
    Get all speaker topics (e.g. for dropdowns or profile edit).
    Returns list of { _id, name, slug }.
    """
    topics = await model.get_all()
    return Utils.create_response(topics, True)


@router.get("/target-audiences", response_model=ServerResponse)
async def get_speaker_target_audiences(
    model=Depends(get_speaker_target_audience_model),
):
    """
    Get all speaker target audiences (e.g. for dropdowns or profile edit).
    Returns list of { _id, name, slug }.
    """
    audiences = await model.get_all()
    return Utils.create_response(audiences, True)
