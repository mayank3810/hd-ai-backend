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
    email: str = Field(..., min_length=1)
    topics: List[SpeakerTopicItem] = Field(..., min_length=1)  # array of topic objects from speakerTopics
    speaking_formats: List[str] = Field(...)
    delivery_mode: List[str] = Field(...)
    linkedin_url: str = Field(...)  # validated as URL in service or via HttpUrl
    past_speaking_examples: Optional[List[str]] = Field(default=None)  # array; each item added via verify-step
    video_links: List[str] = Field(...)
    talk_description: str = Field(..., min_length=1)
    key_takeaways: str = Field(..., min_length=1)
    target_audiences: List[SpeakerTargetAudienceItem] = Field(..., min_length=1)  # array of audience objects from speakerTargetAudeince
    # Optional fields editable after profile creation (not part of verify-step)
    name_salutation: Optional[str] = Field(default=None, description="E.g. Mr, Dr., Mrs., Ms.")
    bio: Optional[str] = Field(default=None, description="Speaker bio (text area)")
    twitter: Optional[str] = Field(default=None, description="Twitter URL or handle")
    facebook: Optional[str] = Field(default=None, description="Facebook URL")
    address_city: Optional[str] = Field(default=None, description="City")
    address_state: Optional[str] = Field(default=None, description="State/Region")
    address_country: Optional[str] = Field(default=None, description="Country")
    phone_country_code: Optional[str] = Field(default=None, description="Phone country code (e.g. +1, +44, +91)")
    phone_number: Optional[str] = Field(default=None, description="Phone number (without country code)")
    professional_memberships: Optional[str] = Field(default=None, description="Professional memberships or affiliations (text area)")
    preferred_speaking_time: Optional[str] = Field(default=None, description="E.g. 10-, 20-, 30-, 40-minute or one hour")


# --- PUT /speaker-profile/{profile_id} request (partial update; all fields optional) ---

class SpeakerProfileUpdateSchema(BaseModel):
    """Request body for PUT /speaker-profile/{profile_id}. All fields optional; only provided fields are updated."""
    full_name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[str] = Field(default=None, min_length=1)
    topics: Optional[List[SpeakerTopicItem]] = Field(default=None, min_length=1)
    speaking_formats: Optional[List[str]] = Field(default=None)
    delivery_mode: Optional[List[str]] = Field(default=None)
    linkedin_url: Optional[str] = Field(default=None)
    past_speaking_examples: Optional[List[str]] = Field(default=None)
    video_links: Optional[List[str]] = Field(default=None)
    talk_description: Optional[str] = Field(default=None, min_length=1)
    key_takeaways: Optional[str] = Field(default=None, min_length=1)
    target_audiences: Optional[List[SpeakerTargetAudienceItem]] = Field(default=None, min_length=1)
    name_salutation: Optional[str] = None
    bio: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_country: Optional[str] = None
    phone_country_code: Optional[str] = None
    phone_number: Optional[str] = None
    professional_memberships: Optional[str] = None
    preferred_speaking_time: Optional[str] = None

    class Config:
        populate_by_name = True
