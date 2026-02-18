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
from app.dependencies import get_speaker_profile_model

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/speaker-profile", tags=["Speaker Profile Onboarding"])


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


@router.post("/verify-step")
async def verify_step(body: VerifyStepRequest, model=Depends(get_speaker_profile_model)):
    """
    Validate and normalize the answer for the given step; return next step or repeat.
    Progressive save: first valid step (full_name) creates profile and returns profile_id; subsequent steps require profile_id.
    """
    step_def = get_step_by_name(body.step)
    validation_mode = step_def.validation_mode if step_def else "unknown"

    if body.step != "full_name" and not body.profile_id:
        repeat_step = step_to_response(step_def) if step_def else {}
        assistant_message = generate_recovery_message(
            step_name=body.step,
            user_answer=body.answer,
            reason_code="MISSING_PROFILE_ID",
            retry_count=body.retry_count or 0,
            allowed_values=step_def.allowed_values if step_def else None,
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
        repeat_step = step_to_response(step_def) if step_def else {}
        assistant_message = generate_recovery_message(
            step_name=body.step,
            user_answer=body.answer,
            reason_code=result.get("reason_code") or "UNKNOWN",
            retry_count=body.retry_count or 0,
            allowed_values=step_def.allowed_values if step_def else None,
        )
        return {"assistant_message": assistant_message, "repeat_step": repeat_step}

    logger.info("verify-step: branch=success")
    normalized = result.get("normalized_value")
    next_step_def = get_next_step(body.step)
    next_step_name = next_step_def.step_name if next_step_def else None
    is_last = is_last_step(body.step)
    next_step_payload = step_to_response(next_step_def) if next_step_def else None
    if is_last:
        next_step_payload = {}
    assistant_message = generate_transition_message(
        step_name=body.step,
        normalized_answer=normalized,
        next_step=next_step_payload,
        is_last_step=is_last,
    )

    profile_id = body.profile_id
    if body.step == "full_name" and not body.profile_id:
        doc = await model.create_profile(normalized)
        profile_id = str(doc["_id"])
    elif body.profile_id and profile:
        completed = list(profile.get("completed_steps") or [])
        if body.step not in completed:
            completed.append(body.step)
        await model.update_step(
            body.profile_id,
            updates={body.step: normalized},
            next_step_name=next_step_name,
            completed_steps=completed,
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
):
    """
    Save the full speaker profile after onboarding. Requires JWT.
    Re-runs full validation pipeline for all fields before saving.
    Deprecated: Progressive save per step is preferred; this endpoint kept for final re-validation, publishing, or workflow extensions.
    """
    user_id = jwt_payload.get("id") or jwt_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token.")
    
    # Re-validate entire profile (authoritative validation)
    validation_errors = validate_full_profile(body.model_dump())
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "assistant_message": "We couldn't save your profile—something doesn't look quite right. Please go through the steps again and make sure everything is filled in."
            }
        )
    
    profile_data = body.model_dump()
    doc = await model.create_speaker_profile(str(user_id), profile_data)
    return {"success": True, "id": str(doc["_id"])}
