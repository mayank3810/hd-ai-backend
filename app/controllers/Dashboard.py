from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from app.config.dashboard import DASHBOARD_TOTAL_AGENTS
from app.helpers.Utilities import Utils
from app.models.Opportunity import OpportunityModel
from app.models.RecentActivity import RecentActivityModel
from app.models.SpeakerProfile import SpeakerProfileModel
from app.models.User import UserModel
from app.schemas.ServerResponse import ServerResponse

RECENT_ACTIVITY_FALLBACK_LIMIT = 5

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/agents-count", response_model=ServerResponse)
async def get_agents_count():
    """Total agents used in the system (fixed; see app/config/dashboard.py)."""
    try:
        return Utils.create_response({"count": DASHBOARD_TOTAL_AGENTS}, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/users-count", response_model=ServerResponse)
async def get_users_count():
    """Total users in the users collection."""
    try:
        user_model = UserModel()
        count = await user_model.get_documents_count({})
        return Utils.create_response({"count": count}, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/speaker-profiles-count", response_model=ServerResponse)
async def get_speaker_profiles_count():
    """Total documents in speaker_profiles collection."""
    try:
        profile_model = SpeakerProfileModel()
        count = await profile_model.count()
        return Utils.create_response({"count": count}, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/opportunities-count", response_model=ServerResponse)
async def get_opportunities_count():
    """Total opportunities in the Opportunities collection."""
    try:
        opportunity_model = OpportunityModel()
        count = await opportunity_model.count()
        return Utils.create_response({"count": count}, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/recent-activities", response_model=ServerResponse)
async def get_recent_activities():
    """
    Recent activity feed: entries for today (UTC), else yesterday (UTC), else up to 5 most recent.
    """
    try:
        model = RecentActivityModel()
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        today_end = today_start + timedelta(days=1)
        yesterday_start = today_start - timedelta(days=1)

        activities = await model.list_created_between(today_start, today_end)
        source = "today"
        if not activities:
            activities = await model.list_created_between(yesterday_start, today_start)
            source = "yesterday"
        if not activities:
            activities = await model.list_recent(RECENT_ACTIVITY_FALLBACK_LIMIT)
            source = "recent"

        return Utils.create_response({"source": source, "activities": activities}, True)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )
