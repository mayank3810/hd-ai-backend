"""
Speaker Profile onboarding: POST /init, POST /verify-step, POST /speaker-profile.
Stateless for init and verify-step; JWT required for final save.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.config.speaker_profile_steps import get_first_step, get_next_step, get_step_by_name, is_last_step, step_to_response
from app.middleware.JWTVerification import jwt_validator
from app.models.SpeakerProfile import PROFILE_FIELDS
from app.schemas.SpeakerProfile import (
    VerifyStepRequest,
    SpeakerProfileCreateSchema,
    SpeakerProfileUpdateSchema,
)
from app.services.SpeakerProfileOnboarding import (
    get_init_response,
    validate_step,
    validate_full_profile,
)
from app.services.SpeakerProfileConversation import (
    generate_recovery_message,
    generate_transition_message,
)
from app.dependencies import get_speaker_profile_model, get_speaker_topics_model, get_speaker_target_audience_model
from app.helpers.Utilities import Utils
from app.schemas.ServerResponse import ServerResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/speaker-profile", tags=["Speaker Profile Onboarding"])


@router.get("", response_model=ServerResponse)
async def get_my_speaker_profiles(
    jwt_payload: dict = Depends(jwt_validator),
    model=Depends(get_speaker_profile_model),
):
    """
    Get speaker profile(s) for the current user. Filtered by user_id from JWT.
    Returns a list (newest first); empty list if none.
    """
    try:
        user_id = jwt_payload.get("id") or jwt_payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail={"data": None, "error": "User ID not found in token.", "success": False},
            )
        profiles = await model.get_profiles_by_user_id(str(user_id))
        return Utils.create_response(profiles, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.get("/{profile_id}", response_model=ServerResponse)
async def get_speaker_profile_by_id(
    profile_id: str,
    jwt_payload: dict = Depends(jwt_validator),
    model=Depends(get_speaker_profile_model),
):
    """
    Get a speaker profile by id. Returns the profile only if it belongs to the current user (JWT).
    """
    try:
        user_id = jwt_payload.get("id") or jwt_payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail={"data": None, "error": "User ID not found in token.", "success": False},
            )
        profile = await model.get_profile_by_id_and_user(profile_id, str(user_id))
        if not profile:
            raise HTTPException(
                status_code=404,
                detail={"data": None, "error": "Profile not found.", "success": False},
            )
        return Utils.create_response(profile, True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False},
        )


@router.put("/{profile_id}", response_model=ServerResponse)
async def update_speaker_profile(
    profile_id: str,
    body: SpeakerProfileUpdateSchema,
    jwt_payload: dict = Depends(jwt_validator),
    model=Depends(get_speaker_profile_model),
):
    """
    Update a speaker profile. Only provided fields are updated.
    Profile must belong to the current user (JWT). All profile fields from full_name to preferred_speaking_time can be updated.
    """
    user_id = jwt_payload.get("id") or jwt_payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={"data": None, "error": "User ID not found in token.", "success": False},
        )
    profile = await model.get_profile_by_id_and_user(profile_id, str(user_id))
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"data": None, "error": "Profile not found.", "success": False},
        )
    updates = body.model_dump(exclude_unset=True, by_alias=True)
    if not updates:
        return Utils.create_response(profile, True)
    updated = await model.update_profile(profile_id, updates)
    if not updated:
        raise HTTPException(
            status_code=500,
            detail={"data": None, "error": "Update failed.", "success": False},
        )
    return Utils.create_response(updated, True)


@router.get("/{profile_id}/resume-onboarding")
async def resume_onboarding(
    profile_id: str,
    jwt_payload: dict = Depends(jwt_validator),
    model=Depends(get_speaker_profile_model),
    speaker_topics_model=Depends(get_speaker_topics_model),
    speaker_target_audience_model=Depends(get_speaker_target_audience_model),
):
    """
    Resume onboarding: return stored conversation and current step payload.
    FE renders conversation as chat, shows step as form, then calls POST /verify-step as in create-profile.
    """
    user_id = jwt_payload.get("id") or jwt_payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={"data": None, "error": "User ID not found in token.", "success": False},
        )
    profile = await model.get_profile_by_id_and_user(profile_id, str(user_id))
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"data": None, "error": "Profile not found.", "success": False},
        )
    conversation = profile.get("conversation") or []
    current_step_name = profile.get("current_step")
    if current_step_name:
        step_def = get_step_by_name(current_step_name)
        step_payload = await _step_payload_with_dynamic_allowed(
            step_def, speaker_topics_model, speaker_target_audience_model
        )
        # Generate question for current step like verify-step: use AI transition from last completed step.
        completed_steps = profile.get("completed_steps") or []
        if completed_steps and step_payload:
            last_step_name = completed_steps[-1]
            last_answer = profile.get(last_step_name)
            if last_answer is not None:
                ai_question = generate_transition_message(
                    step_name=last_step_name,
                    normalized_answer=last_answer,
                    next_step=step_payload,
                    is_last_step=False,
                )
                step_payload = {**step_payload, "question": ai_question}
    else:
        step_payload = None
    is_complete = current_step_name is None
    return {
        "profile_id": profile_id,
        "is_complete": is_complete,
        "completed_steps": profile.get("completed_steps") or [],
        "conversation": conversation,
        "next_step": step_payload,
    }


@router.post("/init")
async def init_onboarding():
    """
    Start the flow: return the first step metadata.
    No auth, no session, no DB.
    """
    return get_init_response()


def _profile_context(profile: dict) -> dict:
    """Small summary for context-aware validation (inform, do not strictly gate)."""
    if not profile:
        return {}
    return {k: profile.get(k) for k in PROFILE_FIELDS if profile.get(k) is not None and profile.get(k) != [] and profile.get(k) != ""}


async def _step_payload_with_dynamic_allowed(step_def, speaker_topics_model, speaker_target_audience_model):
    """Build step payload; for topics/target_audiences steps, fetch and inject allowed_values from DB."""
    payload = step_to_response(step_def) if step_def else {}
    if step_def and step_def.step_name == "topics":
        payload["allowed_values"] = await speaker_topics_model.get_all()
    elif step_def and step_def.step_name == "target_audiences":
        payload["allowed_values"] = await speaker_target_audience_model.get_all()
    return payload


def _allowed_values_for_recovery(step_name, step_def, allowed_topics_for_step, allowed_target_audiences_for_step):
    """Return allowed_values for generate_recovery_message based on current step."""
    if step_name == "topics":
        return allowed_topics_for_step
    if step_name == "target_audiences":
        return allowed_target_audiences_for_step
    return step_def.allowed_values if step_def else None


@router.post("/verify-step")
async def verify_step(
    body: VerifyStepRequest,
    jwt_payload: dict = Depends(jwt_validator),
    model=Depends(get_speaker_profile_model),
    speaker_topics_model=Depends(get_speaker_topics_model),
    speaker_target_audience_model=Depends(get_speaker_target_audience_model),
):
    """
    Validate and normalize the answer for the given step; return next step or repeat.
    Progressive save: first valid step (full_name) creates profile and returns profile_id; subsequent steps require profile_id.
    """
    user_id = jwt_payload.get("id") or jwt_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token.")
    step_def = get_step_by_name(body.step)
    validation_mode = step_def.validation_mode if step_def else "unknown"

    # When step is topics or target_audiences, fetch allowed values once (for validation and for repeat/next payloads)
    allowed_topics_for_step = None
    allowed_target_audiences_for_step = None
    if body.step == "topics":
        allowed_topics_for_step = await speaker_topics_model.get_all()
    elif body.step == "target_audiences":
        allowed_target_audiences_for_step = await speaker_target_audience_model.get_all()

    if body.step != "full_name" and not body.profile_id:
        repeat_step = await _step_payload_with_dynamic_allowed(step_def, speaker_topics_model, speaker_target_audience_model)
        assistant_message = generate_recovery_message(
            step_name=body.step,
            user_answer=body.answer,
            reason_code="MISSING_PROFILE_ID",
            retry_count=body.retry_count or 0,
            allowed_values=_allowed_values_for_recovery(body.step, step_def, allowed_topics_for_step, allowed_target_audiences_for_step),
        )
        return {"assistant_message": assistant_message, "repeat_step": repeat_step}

    profile = None
    expected_step_name = get_first_step().step_name
    if body.profile_id:
        profile = await model.get_profile(body.profile_id)
        if profile:
            expected_step_name = profile.get("current_step") or expected_step_name
    profile_context = _profile_context(profile) if profile else None

    result = validate_step(
        step_name=body.step,
        answer=body.answer,
        source=body.source,
        expected_step_name=expected_step_name,
        profile_context=profile_context,
        allowed_topics_for_step=allowed_topics_for_step,
        allowed_target_audiences_for_step=allowed_target_audiences_for_step,
    )

    # Debug logging: verify branch logic
    def _safe_repr(v, max_len=80):
        if v is None:
            return "None"
        s = str(v)
        return s[:max_len] + "..." if len(s) > max_len else s

    logger.info(
        "verify-step: step=%s validation_mode=%s status=%s reason_code=%s normalized=%s",
        body.step,
        validation_mode,
        result.get("status"),
        result.get("reason_code"),
        _safe_repr(result.get("normalized_value")),
    )

    if result.get("status") != "VALID":
        logger.info("verify-step: branch=repeat")
        repeat_step = await _step_payload_with_dynamic_allowed(step_def, speaker_topics_model, speaker_target_audience_model)
        assistant_message = generate_recovery_message(
            step_name=body.step,
            user_answer=body.answer,
            reason_code=result.get("reason_code") or "UNKNOWN",
            retry_count=body.retry_count or 0,
            allowed_values=_allowed_values_for_recovery(body.step, step_def, allowed_topics_for_step, allowed_target_audiences_for_step),
        )
        return {"assistant_message": assistant_message, "repeat_step": repeat_step}

    logger.info("verify-step: branch=success")
    normalized = result.get("normalized_value")
    next_step_def = get_next_step(body.step)
    next_step_name = next_step_def.step_name if next_step_def else None
    is_last = is_last_step(body.step)
    next_step_payload = await _step_payload_with_dynamic_allowed(next_step_def, speaker_topics_model, speaker_target_audience_model) if next_step_def else None
    if is_last:
        next_step_payload = {}
    assistant_message = generate_transition_message(
        step_name=body.step,
        normalized_answer=normalized,
        next_step=next_step_payload,
        is_last_step=is_last,
    )

    # Agent message for the step just completed: first step uses config question; later steps use the AI transition we stored last time.
    agent_message_for_step = (
        profile.get("last_assistant_message") if (profile and body.step != "full_name") else None
    ) or step_def.question

    profile_id = body.profile_id
    if body.step == "full_name" and not body.profile_id:
        doc = await model.create_profile(normalized, user_id=user_id)
        profile_id = str(doc["_id"])
        await model.append_conversation(profile_id, agent_message_for_step, normalized)
        await model.update_last_assistant_message(profile_id, assistant_message)
    elif body.profile_id and profile:
        completed = list(profile.get("completed_steps") or [])
        if body.step not in completed:
            completed.append(body.step)
        await model.append_conversation(profile_id, agent_message_for_step, normalized)
        # past_speaking_examples is stored as array; store the user's answer as [normalized]
        if body.step == "past_speaking_examples":
            step_updates = {body.step: [normalized]}
        else:
            step_updates = {body.step: normalized}
        await model.update_step(
            body.profile_id,
            updates=step_updates,
            next_step_name=next_step_name,
            completed_steps=completed,
            last_assistant_message=assistant_message,
        )
        profile_id = body.profile_id

    return {
        "assistant_message": assistant_message,
        "normalized_answer": normalized,
        "next_step": next_step_payload,
        "is_last_step": is_last,
        "profile_id": profile_id,
    }


@router.post("", status_code=201)
async def save_speaker_profile(
    body: SpeakerProfileCreateSchema,
    jwt_payload: dict = Depends(jwt_validator),
    model=Depends(get_speaker_profile_model),
    speaker_topics_model=Depends(get_speaker_topics_model),
    speaker_target_audience_model=Depends(get_speaker_target_audience_model),
):
    """
    Save the full speaker profile after onboarding. Requires JWT.
    Re-runs full validation pipeline for all fields before saving.
    Deprecated: Progressive save per step is preferred; this endpoint kept for final re-validation, publishing, or workflow extensions.
    """
    user_id = jwt_payload.get("id") or jwt_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token.")
    
    allowed_topics = await speaker_topics_model.get_all()
    allowed_target_audiences = await speaker_target_audience_model.get_all()
    # Re-validate entire profile (authoritative validation)
    validation_errors = validate_full_profile(
        body.model_dump(by_alias=True),
        allowed_topics=allowed_topics,
        allowed_target_audiences=allowed_target_audiences,
    )
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "assistant_message": "We couldn't save your profile—something doesn't look quite right. Please go through the steps again and make sure everything is filled in."
            }
        )
    
    profile_data = body.model_dump(by_alias=True)
    doc = await model.create_speaker_profile(str(user_id), profile_data)
    return {"success": True, "id": str(doc["_id"])}
