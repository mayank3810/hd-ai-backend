"""
Pydantic schemas for Speaker Profile onboarding: init, verify-step, and final save.
"""
from pydantic import BaseModel, Field
from typing import Any, List, Literal, Optional, Union


# --- Topic item (from speakerTopics collection; stored in profile.topics) ---

class SpeakerTopicItem(BaseModel):
    """One topic option or selected topic (_id, name, slug). API/DB use '_id'; Pydantic field is 'id'."""
    id: str = Field(..., alias="_id")
    name: str = ""
    slug: str = ""

    class Config:
        populate_by_name = True


# --- Target audience item (from speakerTargetAudeince collection; stored in profile.target_audiences) ---

class SpeakerTargetAudienceItem(BaseModel):
    """One target audience option or selected audience (_id, name, slug). API/DB use '_id'; Pydantic field is 'id'."""
    id: str = Field(..., alias="_id")
    name: str = ""
    slug: str = ""

    class Config:
        populate_by_name = True


# --- POST /init response (first step metadata) ---

class InitStepResponse(BaseModel):
    """First step returned by POST /init."""
    step_name: str
    form_type: str
    question: str
    allowed_values: Optional[List[Any]] = None  # List[str] for enum steps; List[SpeakerTopicItem] for topics
    multi_select: bool = False


# --- POST /verify-step request ---

class VerifyStepRequest(BaseModel):
    """Request body for POST /verify-step."""
    step: str = Field(..., description="Current step name")
    answer: Union[str, List[str], List[dict]] = Field(..., description="User answer (string, list of strings, or for topics selection: list of topic objects)")
    source: Literal["selection", "text"] = Field(..., description="'selection' or 'text'")
    retry_count: int = Field(0, ge=0, description="How many times user has retried this step")
    profile_id: Optional[str] = Field(None, description="Set after first valid step (full_name); required for subsequent steps")
    user_id: Optional[str] = Field(None, description="Logged-in user id; when present, linked to profile on create (full_name step)")


# --- POST /verify-step response (chat-style) ---

class NextStepPayload(BaseModel):
    """Next step metadata (next_step or repeat_step)."""
    step_name: str
    form_type: str
    question: str
    allowed_values: Optional[List[Any]] = None  # List[str] for enum steps; list of topic objects for topics step
    multi_select: bool = False


# Success: assistant_message, normalized_answer, next_step, is_last_step, optional profile_id
class VerifyStepSuccessResponse(BaseModel):
    """Chat-style success response."""
    assistant_message: str
    normalized_answer: Union[str, List[str], List[dict]]  # list of topic objects when step is topics
    next_step: dict  # NextStepPayload shape
    is_last_step: bool
    profile_id: Optional[str] = None  # Present after first valid step; FE should store and send on subsequent steps


# Failure: assistant_message, repeat_step (conversational tone, no technical errors)
class VerifyStepInvalidResponse(BaseModel):
    """Chat-style validation failure; same step is repeated."""
    assistant_message: str
    repeat_step: dict  # NextStepPayload shape


# --- POST /speaker-profile request (full profile body) ---

class SpeakerProfileCreateSchema(BaseModel):
    """Full speaker profile payload for POST /speaker-profile."""
    full_name: str = Field(..., min_length=1)
    topics: List[SpeakerTopicItem] = Field(..., min_length=1)  # array of topic objects from speakerTopics
    speaking_formats: List[str] = Field(...)
    delivery_mode: List[str] = Field(...)
    linkedin_url: str = Field(...)  # validated as URL in service or via HttpUrl
    past_speaking_examples: Optional[str] = Field(default=None)
    video_links: List[str] = Field(...)
    talk_description: str = Field(..., min_length=1)
    key_takeaways: str = Field(..., min_length=1)
    target_audiences: List[SpeakerTargetAudienceItem] = Field(..., min_length=1)  # array of audience objects from speakerTargetAudeince
