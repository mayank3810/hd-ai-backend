"""
Single source of truth for Speaker Profile onboarding steps.
Order of STEPS list defines step sequence (next_step, is_last_step).
"""
from typing import List, Optional, Any
from pydantic import BaseModel


class StepDefinition(BaseModel):
    """One onboarding step definition."""
    step_name: str
    form_type: str  # e.g. "text", "textarea", "url", "multiselect", "array"
    question: str
    required: bool = True
    multi_select: bool = False
    allowed_values: Optional[List[str]] = None  # for enum / multiselect steps
    validation_type: str  # internal: string, url, array_of_strings, array_of_urls, enum, textarea
    validation_mode: str = "semantic_text_ai"  # code_full_name, url_only, strict_enum_code, semantic_text_ai, textarea_accept
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    split_on_conjunctions: bool = False  # for topics, target_audiences, past_speaking_examples
    uses_ai: bool = False  # true for AI-backed steps


# Canonical allowed values for enum steps (used for selection + text normalization)
SPEAKING_FORMATS = ["Keynote", "Panel Discussion", "Workshop", "Solo Talk"]
DELIVERY_MODES = ["In-Person", "Virtual", "Hybrid"]


STEPS: List[StepDefinition] = [
    StepDefinition(
        step_name="full_name",
        form_type="text",
        question="Welcome to Human Driven AI.<br>I will help you to create an account and find matching speaking opportunities<br>Please tell me what is your name",
        required=True,
        multi_select=False,
        allowed_values=None,
        validation_type="string",
        validation_mode="code_full_name",
        min_length=2,
        max_length=100,
        split_on_conjunctions=False,
        uses_ai=False,
    ),
    StepDefinition(
        step_name="email",
        form_type="text",
        question="What is your email address?",
        required=True,
        multi_select=False,
        allowed_values=None,
        validation_type="string",
        validation_mode="email_regex",
        min_length=5,
        max_length=254,
        split_on_conjunctions=False,
        uses_ai=True,
    ),
    StepDefinition(
        step_name="topics",
        form_type="multiselect",
        question="What topics do you speak about? (at least one)",
        required=True,
        multi_select=True,
        allowed_values=None,
        validation_type="enum",
        validation_mode="topics_multiselect",
        split_on_conjunctions=False,
        uses_ai=False,
    ),
    StepDefinition(
        step_name="speaking_formats",
        form_type="multiselect",
        question="What speaking formats do you offer?",
        required=True,
        multi_select=True,
        allowed_values=SPEAKING_FORMATS,
        validation_type="enum",
        validation_mode="strict_enum_code",
        split_on_conjunctions=False,
        uses_ai=False,
    ),
    StepDefinition(
        step_name="delivery_mode",
        form_type="multiselect",
        question="How do you deliver?",
        required=True,
        multi_select=True,
        allowed_values=DELIVERY_MODES,
        validation_type="enum",
        validation_mode="strict_enum_code",
        split_on_conjunctions=False,
        uses_ai=False,
    ),
    StepDefinition(
        step_name="linkedin_url",
        form_type="url",
        question="What is your LinkedIn profile URL?",
        required=True,
        multi_select=False,
        allowed_values=None,
        validation_type="url",
        validation_mode="url_only",
        split_on_conjunctions=False,
        uses_ai=False,
    ),
    StepDefinition(
        step_name="past_speaking_examples",
        form_type="textarea",
        question="Past speaking examples or events",
        required=False,
        multi_select=False,
        allowed_values=None,
        validation_type="textarea",
        validation_mode="textarea_accept",
        split_on_conjunctions=True,
        uses_ai=False,
    ),
    StepDefinition(
        step_name="video_links",
        form_type="array",
        question="Links to your speaking videos",
        required=True,
        multi_select=False,
        allowed_values=None,
        validation_type="array_of_urls",
        validation_mode="url_only",
        split_on_conjunctions=False,
        uses_ai=False,
    ),
    StepDefinition(
        step_name="talk_description",
        form_type="textarea",
        question="Describe your talk or expertise",
        required=True,
        multi_select=False,
        allowed_values=None,
        validation_type="textarea",
        validation_mode="semantic_text_ai",
        min_length=20,
        max_length=2000,
        split_on_conjunctions=False,
        uses_ai=True,
    ),
    StepDefinition(
        step_name="key_takeaways",
        form_type="textarea",
        question="What are the key takeaways for your audience?",
        required=True,
        multi_select=False,
        allowed_values=None,
        validation_type="textarea",
        validation_mode="semantic_text_ai",
        min_length=20,
        max_length=1000,
        split_on_conjunctions=False,
        uses_ai=True,
    ),
    StepDefinition(
        step_name="target_audiences",
        form_type="multiselect",
        question="Who is your target audience?",
        required=True,
        multi_select=True,
        allowed_values=None,
        validation_type="enum",
        validation_mode="target_audiences_multiselect",
        split_on_conjunctions=False,
        uses_ai=False,
    ),
]


def get_first_step() -> StepDefinition:
    """Return the first step (for POST /init)."""
    return STEPS[0]


def get_step_by_name(step_name: str) -> Optional[StepDefinition]:
    """Return step definition by step_name, or None if not found."""
    for s in STEPS:
        if s.step_name == step_name:
            return s
    return None


def get_next_step(step_name: str) -> Optional[StepDefinition]:
    """Return the next step after step_name, or None if step_name is last."""
    for i, s in enumerate(STEPS):
        if s.step_name == step_name:
            if i + 1 < len(STEPS):
                return STEPS[i + 1]
            return None
    return None


def is_last_step(step_name: str) -> bool:
    """Return True if step_name is the last step."""
    return len(STEPS) > 0 and STEPS[-1].step_name == step_name


def step_to_response(step: StepDefinition) -> dict:
    """Convert StepDefinition to API response shape. multi_select and allowed_values only for multiselect steps."""
    out: dict = {
        "step_name": step.step_name,
        "form_type": step.form_type,
        "question": step.question,
    }
    if step.form_type == "multiselect" or step.multi_select:
        out["multi_select"] = step.multi_select
        if step.allowed_values is not None:
            out["allowed_values"] = step.allowed_values
    return out
