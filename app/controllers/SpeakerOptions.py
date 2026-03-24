"""
Speaker options: GET/POST/DELETE for topics; GET/POST for target audiences, delivery modes, speaking formats.
Catalog data for speaker profile flows; stored in Mongo with { name, slug, type }.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import (
    get_delivery_modes_model,
    get_speaker_formats_model,
    get_speaker_target_audience_model,
    get_speaker_topics_model,
)
from app.helpers.Utilities import Utils
from app.schemas.ServerResponse import ServerResponse
from app.schemas.SpeakerOptions import SpeakerOptionCreateSchema

router = APIRouter(prefix="/api/v1/speaker-options", tags=["Speaker Options"])


def _create_error_response(detail: str, code: int = 400):
    return HTTPException(
        status_code=code,
        detail={"data": None, "error": detail, "success": False},
    )


@router.get("/topics", response_model=ServerResponse)
async def get_speaker_topics(
    doc_type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Filter by type (e.g. system, custom). Omit to return all.",
    ),
    model=Depends(get_speaker_topics_model),
):
    """
    Get speaker topics from speakerTopics.
    Returns list of { _id, name, slug, type }.
    """
    topics = await model.get_all(doc_type=doc_type)
    return Utils.create_response(topics, True)


@router.post("/topics", response_model=ServerResponse, status_code=201)
async def create_speaker_topic(
    body: SpeakerOptionCreateSchema,
    model=Depends(get_speaker_topics_model),
):
    doc, err = await model.create_one(body.name, body.slug, body.type)
    if err == "duplicate_slug":
        raise _create_error_response("A topic with this slug already exists.", 409)
    if err == "duplicate_name":
        raise _create_error_response("A topic with this name already exists.", 409)
    if err == "invalid_name":
        raise _create_error_response("Invalid name or slug.", 400)
    return Utils.create_response(doc, True)


@router.delete("/topics/{topic_id}", response_model=ServerResponse)
async def delete_speaker_topic(
    topic_id: str,
    model=Depends(get_speaker_topics_model),
):
    """Remove a topic by id. System and legacy (no type) topics cannot be deleted."""
    err = await model.delete_one_non_system(topic_id)
    if err == "invalid_id":
        raise _create_error_response("Invalid topic id.", 400)
    if err == "not_found":
        raise _create_error_response("Topic not found.", 404)
    if err == "system_topic":
        raise _create_error_response("Only non-system topics can be deleted.", 403)
    return Utils.create_response(
        {"_id": topic_id, "message": "Topic deleted successfully"},
        True,
    )


@router.get("/target-audiences", response_model=ServerResponse)
async def get_speaker_target_audiences(
    doc_type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Filter by type (e.g. system, custom). Omit to return all.",
    ),
    model=Depends(get_speaker_target_audience_model),
):
    """
    Get target audiences from speakerTargetAudeince.
    Returns list of { _id, name, slug, type }.
    """
    audiences = await model.get_all(doc_type=doc_type)
    return Utils.create_response(audiences, True)


@router.post("/target-audiences", response_model=ServerResponse, status_code=201)
async def create_speaker_target_audience(
    body: SpeakerOptionCreateSchema,
    model=Depends(get_speaker_target_audience_model),
):
    doc, err = await model.create_one(body.name, body.slug, body.type)
    if err == "duplicate_slug":
        raise _create_error_response("A target audience with this slug already exists.", 409)
    if err == "duplicate_name":
        raise _create_error_response("A target audience with this name already exists.", 409)
    if err == "invalid_name":
        raise _create_error_response("Invalid name or slug.", 400)
    return Utils.create_response(doc, True)


@router.get("/delivery-modes", response_model=ServerResponse)
async def get_delivery_modes(
    doc_type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Filter by type (e.g. system, custom). Omit to return all.",
    ),
    model=Depends(get_delivery_modes_model),
):
    """
    Get delivery modes from deliveryModes.
    Returns list of { _id, name, slug, type }.
    """
    items = await model.get_all(doc_type=doc_type)
    return Utils.create_response(items, True)


@router.post("/delivery-modes", response_model=ServerResponse, status_code=201)
async def create_delivery_mode(
    body: SpeakerOptionCreateSchema,
    model=Depends(get_delivery_modes_model),
):
    doc, err = await model.create_one(body.name, body.slug, body.type)
    if err == "duplicate_slug":
        raise _create_error_response("A delivery mode with this slug already exists.", 409)
    if err == "duplicate_name":
        raise _create_error_response("A delivery mode with this name already exists.", 409)
    if err == "invalid_name":
        raise _create_error_response("Invalid name or slug.", 400)
    return Utils.create_response(doc, True)


@router.get("/speaking-formats", response_model=ServerResponse)
async def get_speaking_formats(
    doc_type: Optional[str] = Query(
        default=None,
        alias="type",
        description="Filter by type (e.g. system, custom). Omit to return all.",
    ),
    model=Depends(get_speaker_formats_model),
):
    """
    Get speaking formats from speakingFormats.
    Returns list of { _id, name, slug, type }.
    """
    items = await model.get_all(doc_type=doc_type)
    return Utils.create_response(items, True)


@router.post("/speaking-formats", response_model=ServerResponse, status_code=201)
async def create_speaking_format(
    body: SpeakerOptionCreateSchema,
    model=Depends(get_speaker_formats_model),
):
    doc, err = await model.create_one(body.name, body.slug, body.type)
    if err == "duplicate_slug":
        raise _create_error_response("A speaking format with this slug already exists.", 409)
    if err == "duplicate_name":
        raise _create_error_response("A speaking format with this name already exists.", 409)
    if err == "invalid_name":
        raise _create_error_response("Invalid name or slug.", 400)
    return Utils.create_response(doc, True)
