"""
Speaker Profile onboarding: step validation and normalization.
3-layer validation pipeline: Basic → Rule-based → AI Semantic.
Stateless: no session or DB. Uses OpenAI when validation_mode requires it.
"""
import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from openai import OpenAI

from app.config.speaker_profile_steps import (
    StepDefinition,
    get_step_by_name,
    get_next_step,
    is_last_step,
    step_to_response,
    get_first_step,
    STEPS,
)


# --- URL validation ---
_URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

# LinkedIn profile URL only: https://www.linkedin.com/in/username or https://linkedin.com/in/username
_LINKEDIN_URL_PATTERN = re.compile(
    r"^https?://(www\.)?linkedin\.com/in/[\w\-]+/?(\?\S*)?$",
    re.IGNORECASE,
)

# YouTube video URL: youtube.com/watch, youtu.be/, youtube.com/embed/, youtube.com/v/, supports query params
_YOUTUBE_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)[\w\-]+(?:\?[^\s]+)?$",
    re.IGNORECASE,
)


def _is_valid_url(s: str) -> bool:
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    return bool(_URL_PATTERN.match(s))


def _is_valid_linkedin_url(s: str) -> bool:
    """True only if URL is a LinkedIn profile (linkedin.com/in/...). Rejects YouTube, etc."""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    return bool(_LINKEDIN_URL_PATTERN.match(s))


def _is_valid_youtube_url(s: str) -> bool:
    """True only if URL is a YouTube video (youtube.com/watch, youtu.be/, etc.)."""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    return bool(_YOUTUBE_URL_PATTERN.match(s))


def _check_gibberish(text: str) -> bool:
    text = text.strip()
    if not text:
        return True
    if len(set(text)) == 1 and len(text) > 5:
        return True
    if len(text) > 8 and len(set(text.lower())) <= 3:
        return True
    return False


# Full name: letters, spaces, hyphen, apostrophe; at least 2 words; each word >= 2 chars; no URLs
_FULL_NAME_REGEX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' \-]+$")

# Email: standard pattern (no AI)
_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
)

# Unicode space-like characters to normalize to ASCII space (e.g. from paste or mobile)
_UNICODE_SPACES = re.compile(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]+")


def _normalize_name_for_validation(name: str) -> str:
    """Strip and normalize Unicode spaces to ASCII space so 'Max\u00a0Doe' passes like 'Max Doe'."""
    if not name or not isinstance(name, str):
        return ""
    name = name.strip()
    name = _UNICODE_SPACES.sub(" ", name)
    return " ".join(name.split())


def validate_email(value: str) -> bool:
    """Regex-only validation for email. No AI."""
    if not value or not isinstance(value, str):
        return False
    s = value.strip()
    if not s or len(s) > 254:
        return False
    return bool(_EMAIL_REGEX.match(s))


def validate_full_name(name: str) -> bool:
    """Strict code-only validation for full_name. No AI."""
    name = _normalize_name_for_validation(name)
    if not name:
        return False
    if "http" in name.lower() or "www." in name.lower():
        return False
    words = name.split()
    if len(words) < 2:
        return False
    for w in words:
        if len(w) < 2:
            return False
    return bool(_FULL_NAME_REGEX.match(name))


def split_input(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    t = text.replace(" and ", ",").replace(" or ", ",")
    parts = [p.strip() for p in t.split(",") if p.strip()]
    return parts


def split_input_topics(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    t = text.replace(" and ", ",").replace(" or ", ",").replace("&", ",").replace("/", ",")
    parts = [p.strip() for p in re.split(r",", t) if p and p.strip()]
    return parts


def _validate_basic(
    step: StepDefinition, answer: Union[str, List[str], List[dict]]
) -> Tuple[Optional[Union[str, List[str], List[dict]]], Optional[str]]:
    if step.required:
        if isinstance(answer, str):
            if not answer or not answer.strip():
                return None, "This field is required."
        elif isinstance(answer, list):
            # Allow list of strings (enum) or list of dicts (topics selection)
            if not answer:
                return None, "At least one value is required."
            if step.validation_mode in ("topics_multiselect", "target_audiences_multiselect"):
                if not any(isinstance(a, dict) and (a.get("_id") or a.get("slug") or a.get("name")) for a in answer):
                    return None, "At least one value is required."
            elif not any(isinstance(a, str) and a.strip() for a in answer):
                return None, "At least one value is required."
        else:
            return None, "Invalid input type."

    # topics_multiselect / target_audiences_multiselect: accept list of objects (selection) or string (text)
    if step.validation_mode in ("topics_multiselect", "target_audiences_multiselect"):
        if isinstance(answer, list):
            return answer, None
        if isinstance(answer, str):
            if step.required and not answer.strip():
                return None, "This field is required."
            return answer.strip(), None
        return None, "Invalid input type."

    if step.validation_type in ("string", "textarea", "url"):
        if isinstance(answer, list):
            answer = answer[0] if answer else ""
        if not isinstance(answer, str):
            return None, f"Expected a string, got {type(answer).__name__}."
        answer = answer.strip()
        if step.required and not answer:
            return None, "This field is required."
        if step.min_length and len(answer) < step.min_length:
            return None, f"Input must be at least {step.min_length} characters."
        if step.max_length and len(answer) > step.max_length:
            return None, f"Input must be no more than {step.max_length} characters."
        return answer, None

    elif step.validation_type in ("array_of_strings", "array_of_urls", "enum"):
        if isinstance(answer, str):
            answer = [answer] if answer.strip() else []
        if not isinstance(answer, list):
            return None, f"Expected a list, got {type(answer).__name__}."
        normalized = [a.strip() for a in answer if isinstance(a, str) and a.strip()]
        if step.required and not normalized:
            return None, "At least one value is required."
        if step.min_length and len(normalized) < step.min_length:
            return None, f"At least {step.min_length} value(s) required."
        return normalized, None

    return None, "Unsupported validation type."


def _validate_rule_based(
    step: StepDefinition,
    normalized_answer: Union[str, List[str]],
    source: str,
) -> Tuple[Optional[Union[str, List[str]]], Optional[str]]:
    if step.validation_mode == "url_only":
        if step.validation_type == "url":
            if step.step_name == "linkedin_url":
                if not _is_valid_linkedin_url(normalized_answer):
                    return None, "Please enter a valid LinkedIn profile URL (e.g. https://www.linkedin.com/in/yourprofile)."
                return normalized_answer, None
            if not _is_valid_url(normalized_answer):
                return None, "Please enter a valid URL."
            return normalized_answer, None
        elif step.validation_type == "array_of_urls":
            if isinstance(normalized_answer, str):
                normalized_answer = split_input(normalized_answer)
            else:
                # User sent one string with comma/and/or - flatten then split into separate URLs
                raw = " ".join(str(x).strip() for x in normalized_answer if str(x).strip())
                normalized_answer = split_input(raw)
            if step.step_name == "video_links":
                # video_links: only YouTube URLs; keep valid ones, INVALID only if none valid
                valid = [u for u in normalized_answer if _is_valid_youtube_url(u)]
                if not valid:
                    return None, "Please enter at least one valid YouTube video URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...)."
                return list(dict.fromkeys(valid)), None
            invalid_urls = [u for u in normalized_answer if not _is_valid_url(u)]
            if invalid_urls:
                return None, f"Invalid URL(s): {', '.join(invalid_urls[:3])}"
            return list(dict.fromkeys(normalized_answer)), None

    # strict_enum_code: pure code, case-insensitive match; split comma-separated; accept all valid values, re-ask only if none valid
    if step.validation_mode == "strict_enum_code":
        if not step.allowed_values:
            return None, "Step has no allowed values."
        allowed_lower = {v.strip().lower(): v for v in step.allowed_values}
        if isinstance(normalized_answer, str):
            parts = [p.strip() for p in normalized_answer.split(",") if p.strip()]
        else:
            parts = [str(a).strip() for a in normalized_answer if str(a).strip()]
        normalized = []
        for a in parts:
            key = a.lower()
            if key in allowed_lower:
                normalized.append(allowed_lower[key])
        if not normalized:
            return None, f"No valid selection. Allowed: {step.allowed_values}"
        return list(dict.fromkeys(normalized)), None

    return normalized_answer, None


def _validation_ai_gibberish_check(
    client: OpenAI,
    step: StepDefinition,
    text: str,
) -> Dict[str, Any]:
    """Return INVALID if text is gibberish/random/keyboard smash; VALID if meaningful."""
    prompt = f"""
Question: {step.question}
User response: {text}

Is this meaningful content (real answer, real topics, real text) or gibberish/random/keyboard smash/nonsense?
- If the user wrote real words, topics, or meaningful content, return VALID.
- If it is random characters, nonsense, "asdf", keyboard mashing, or clearly not a real answer, return INVALID.

Return JSON ONLY: {{ "status": "VALID" | "INVALID", "reason_code": "GIBBERISH" if INVALID else "OK" }}
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. One of: {\"status\": \"VALID\", \"reason_code\": \"OK\"} or {\"status\": \"INVALID\", \"reason_code\": \"GIBBERISH\"}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=10,
        )
        obj = _parse_validation_ai_json(completion.choices[0].message.content or "")
        if not obj:
            return {"status": "INVALID", "reason_code": "GIBBERISH", "normalized_value": None}
        status = obj.get("status")
        if status == "VALID":
            return {"status": "VALID", "reason_code": "OK", "normalized_value": None}
        return {"status": "INVALID", "reason_code": "GIBBERISH", "normalized_value": None}
    except Exception:
        return {"status": "INVALID", "reason_code": "GIBBERISH", "normalized_value": None}


def _parse_validation_ai_json(content: str) -> Optional[Dict[str, Any]]:
    content = (content or "").strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(l for l in lines if l.strip() and not l.strip().startswith("```"))
    try:
        obj = json.loads(content)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# Reason codes from semantic AI that we override to VALID (writing-coach style; not reject reasons)
SEMANTIC_OVERRIDE_REASON_CODES = {"TOO_VAGUE", "NEEDS_MORE_DETAIL", "UNCLEAR", "NOT_SPECIFIC", "COULD_BE_BETTER"}

# All allowed reason_codes for _validation_ai_intent (reject-only + override-to-valid)
_VALIDATION_AI_INTENT_REASON_CODES = [
    "EMPTY", "GIBBERISH", "IRRELEVANT", "SPAM", "UNRELATED", "LOW_EFFORT",
    "TOO_VAGUE", "NEEDS_MORE_DETAIL", "UNCLEAR", "NOT_SPECIFIC", "COULD_BE_BETTER",
]


def _validation_ai_intent(
    client: OpenAI,
    step: StepDefinition,
    user_text: str,
    profile_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    allowed_reason_codes = _VALIDATION_AI_INTENT_REASON_CODES
    context_blurb = ""
    if profile_context:
        context_blurb = f"\nCurrent profile (for context only): {json.dumps(profile_context)}"
    prompt = f"""
You are ValidationAI. You are a semantic sanity check only, not a writing coach.
{context_blurb}
Question field: {step.step_name}
Question: {step.question}
User response: {user_text}

Only mark INVALID if: the content is empty, obvious gibberish, completely irrelevant to the question, or spam.
Do NOT reject for: too broad, too general, too long, too short, lacking specificity, or style issues.
If the answer is meaningful and related to the question, return VALID.

Return JSON ONLY: {{ "status": "VALID" | "INVALID", "reason_code": one of {allowed_reason_codes}, "normalized_value": null }}
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. No extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=10,
        )
        obj = _parse_validation_ai_json(completion.choices[0].message.content or "")
        if not obj:
            return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
        status = obj.get("status")
        reason_code = obj.get("reason_code")
        if status not in ("VALID", "INVALID") or reason_code not in allowed_reason_codes:
            return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
        return {"status": status, "reason_code": reason_code, "normalized_value": None}
    except Exception:
        return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}


def _validation_ai_topics_normalize(
    client: OpenAI,
    step: StepDefinition,
    items: List[str],
    profile_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    allowed_reason_codes = ["EMPTY", "LOW_EFFORT", "GIBBERISH", "SPAM", "UNRELATED"]
    context_blurb = f"\nCurrent profile (for context only): {json.dumps(profile_context)}" if profile_context else ""
    prompt = f"""
You are ValidationAI for speaker topics. There is no predefined list of allowed topics.
{context_blurb}
Question: {step.question}
Input items (already split from user text): {json.dumps(items)}

Your goal: Decide if the content is meaningful (not gibberish, random, or spam). If yes, return VALID.
- One topic or many is fine. Return VALID if at least one valid topic.
- When VALID: return normalized_value as a JSON array of strings (e.g. ["Environment"] or ["Climate", "Sustainability"]). You may correct spelling and normalize terms; drop only gibberish/meaningless/low-effort items. We already split comma/and/or-separated input in code; you can return the array for saving individually.
- Return INVALID only for: empty, all gibberish, low-effort, spam, or completely unrelated.

Return JSON ONLY: {{ "status": "VALID" | "INVALID", "reason_code": one of {allowed_reason_codes}, "normalized_value": array of strings or null }}
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. When status is VALID, normalized_value must be a JSON array of strings, e.g. [\"Environment\"], even for a single topic."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=15,
        )
        obj = _parse_validation_ai_json(completion.choices[0].message.content or "")
        if not obj:
            return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
        status = obj.get("status")
        reason_code = obj.get("reason_code") or "UNRELATED"
        normalized_value = obj.get("normalized_value")
        if status not in ("VALID", "INVALID"):
            return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
        if status == "VALID":
            if not isinstance(normalized_value, list):
                if isinstance(normalized_value, str) and normalized_value.strip():
                    normalized_value = [normalized_value.strip()]
                else:
                    return {"status": "INVALID", "reason_code": "EMPTY" if normalized_value is None or (isinstance(normalized_value, str) and not normalized_value.strip()) else "AI_UNAVAILABLE", "normalized_value": None}
            cleaned = [str(x).strip() for x in normalized_value if str(x).strip()]
            if not cleaned:
                return {"status": "INVALID", "reason_code": "EMPTY", "normalized_value": None}
            return {"status": "VALID", "reason_code": "OK", "normalized_value": list(dict.fromkeys(cleaned))}
        return {"status": "INVALID", "reason_code": reason_code if reason_code in allowed_reason_codes else "UNRELATED", "normalized_value": None}
    except Exception:
        return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}


def _reason_code_from_basic_error(err: str) -> str:
    e = (err or "").lower()
    if "required" in e or "at least one" in e:
        return "EMPTY"
    if "at least" in e and "characters" in e:
        return "TOO_SHORT"
    if "no more than" in e:
        return "TOO_LONG"
    if "expected" in e:
        return "TYPE_MISMATCH"
    return "BASIC_INVALID"


def _reason_code_from_rule_error(err: str) -> str:
    e = (err or "").lower()
    if "url" in e:
        return "INVALID_URL"
    if "invalid value" in e or "allowed" in e:
        return "ENUM_INVALID"
    return "RULE_INVALID"


def _validation_ai_full_name_check(client: OpenAI, name: str) -> Dict[str, Any]:
    """Return INVALID if name looks like gibberish/random, not a real person's name."""
    prompt = f"""
The user was asked for their full name. They entered: "{name}"

Is this a realistic full name (first and last, real-looking name) or random characters/gibberish/keyboard smash?
- If it looks like a real person's name (e.g. "John Smith", "Marie-Claire O'Brien"), return VALID.
- If it is random letters, nonsense, or clearly not a real name (e.g. "asfas cdfeae", "xyz abc"), return INVALID.

Return JSON ONLY: {{ "status": "VALID" | "INVALID", "reason_code": "INVALID_FULL_NAME" if INVALID else "OK" }}
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. One of: {\"status\": \"VALID\", \"reason_code\": \"OK\"} or {\"status\": \"INVALID\", \"reason_code\": \"INVALID_FULL_NAME\"}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=10,
        )
        obj = _parse_validation_ai_json(completion.choices[0].message.content or "")
        if not obj:
            return {"status": "INVALID", "reason_code": "INVALID_FULL_NAME", "normalized_value": None}
        status = obj.get("status")
        if status == "VALID":
            return {"status": "VALID", "reason_code": "OK", "normalized_value": None}
        return {"status": "INVALID", "reason_code": "INVALID_FULL_NAME", "normalized_value": None}
    except Exception:
        return {"status": "INVALID", "reason_code": "INVALID_FULL_NAME", "normalized_value": None}


def _validation_ai_enum_intent(
    client: OpenAI,
    step: StepDefinition,
    user_text: str,
) -> Dict[str, Any]:
    """Map free-text user input to allowed enum values. Reject only empty, gibberish, spam, unrelated."""
    allowed = step.allowed_values or []
    if not allowed:
        return {"status": "INVALID", "reason_code": "ENUM_INVALID", "normalized_value": None}
    allowed_reason_codes = ["EMPTY", "GIBBERISH", "SPAM", "UNRELATED"]
    prompt = f"""
You are ValidationAI for a single-choice/multi-choice field. Map the user's intent to the allowed options.
Question: {step.question}
Allowed values (return only these when VALID): {json.dumps(allowed)}
User response: {user_text}

Focus on intent only. Accept vague, long, or slightly off answers; normalize to one or more allowed values.
Return INVALID only for: empty, gibberish, spam, or completely unrelated input.
Return JSON ONLY: {{ "status": "VALID" | "INVALID", "reason_code": one of {allowed_reason_codes}, "normalized_value": array of strings from allowed values, or null }}
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. normalized_value must be a subset of the allowed values when VALID."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=10,
        )
        obj = _parse_validation_ai_json(completion.choices[0].message.content or "")
        if not obj:
            return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
        status = obj.get("status")
        reason_code = obj.get("reason_code") or "UNRELATED"
        normalized_value = obj.get("normalized_value")
        if status == "VALID" and isinstance(normalized_value, list):
            allowed_set = {v.strip().lower(): v for v in allowed}
            cleaned = []
            for x in normalized_value:
                key = str(x).strip().lower()
                if key in allowed_set:
                    cleaned.append(allowed_set[key])
            if cleaned:
                return {"status": "VALID", "reason_code": "OK", "normalized_value": list(dict.fromkeys(cleaned))}
        return {"status": "INVALID", "reason_code": reason_code if reason_code in allowed_reason_codes else "UNRELATED", "normalized_value": None}
    except Exception:
        return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}


def _validation_ai_enum_intent_topics(
    client: OpenAI,
    step: StepDefinition,
    user_text: str,
    allowed_topics: List[dict],
) -> Dict[str, Any]:
    """Map free-text user input to allowed topics (by name). Returns list of full topic objects."""
    if not allowed_topics:
        return {"status": "INVALID", "reason_code": "ENUM_INVALID", "normalized_value": None}
    allowed_names = [t.get("name", "").strip() for t in allowed_topics if t.get("name")]
    name_to_topic = {t.get("name", "").strip().lower(): t for t in allowed_topics if t.get("name")}
    if not name_to_topic:
        return {"status": "INVALID", "reason_code": "ENUM_INVALID", "normalized_value": None}
    allowed_reason_codes = ["EMPTY", "GIBBERISH", "SPAM", "UNRELATED"]
    prompt = f"""
You are ValidationAI for a multi-choice field. Map the user's intent to the allowed topic options.
Question: {step.question}
Allowed values (return only these names when VALID): {json.dumps(allowed_names)}
User response: {user_text}

Focus on intent only. Accept vague, long, or slightly off answers; normalize to one or more allowed topic names.
Return INVALID only for: empty, gibberish, spam, or completely unrelated input.
Return JSON ONLY: {{ "status": "VALID" | "INVALID", "reason_code": one of {allowed_reason_codes}, "normalized_value": array of topic names from allowed list, or null }}
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. normalized_value must be a subset of the allowed topic names when VALID."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=10,
        )
        obj = _parse_validation_ai_json(completion.choices[0].message.content or "")
        if not obj:
            return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
        status = obj.get("status")
        reason_code = obj.get("reason_code") or "UNRELATED"
        normalized_value = obj.get("normalized_value")
        if status == "VALID" and isinstance(normalized_value, list):
            seen = set()
            out = []
            for x in normalized_value:
                key = str(x).strip().lower()
                if key in name_to_topic and key not in seen:
                    seen.add(key)
                    out.append(name_to_topic[key])
            if out:
                return {"status": "VALID", "reason_code": "OK", "normalized_value": out}
        return {"status": "INVALID", "reason_code": reason_code if reason_code in allowed_reason_codes else "UNRELATED", "normalized_value": None}
    except Exception:
        return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}


def _validation_ai_enum_intent_target_audiences(
    client: OpenAI,
    step: StepDefinition,
    user_text: str,
    allowed_audiences: List[dict],
) -> Dict[str, Any]:
    """Map free-text user input to allowed target audiences (by name). Returns list of full audience objects."""
    if not allowed_audiences:
        return {"status": "INVALID", "reason_code": "ENUM_INVALID", "normalized_value": None}
    allowed_names = [a.get("name", "").strip() for a in allowed_audiences if a.get("name")]
    name_to_audience = {a.get("name", "").strip().lower(): a for a in allowed_audiences if a.get("name")}
    if not name_to_audience:
        return {"status": "INVALID", "reason_code": "ENUM_INVALID", "normalized_value": None}
    allowed_reason_codes = ["EMPTY", "GIBBERISH", "SPAM", "UNRELATED"]
    prompt = f"""
You are ValidationAI for a multi-choice field. Map the user's intent to the allowed target audience options.
Question: {step.question}
Allowed values (return only these names when VALID): {json.dumps(allowed_names)}
User response: {user_text}

Focus on intent only. Accept vague, long, or slightly off answers; normalize to one or more allowed audience names.
Return INVALID only for: empty, gibberish, spam, or completely unrelated input.
Return JSON ONLY: {{ "status": "VALID" | "INVALID", "reason_code": one of {allowed_reason_codes}, "normalized_value": array of audience names from allowed list, or null }}
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY JSON. normalized_value must be a subset of the allowed audience names when VALID."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            timeout=10,
        )
        obj = _parse_validation_ai_json(completion.choices[0].message.content or "")
        if not obj:
            return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
        status = obj.get("status")
        reason_code = obj.get("reason_code") or "UNRELATED"
        normalized_value = obj.get("normalized_value")
        if status == "VALID" and isinstance(normalized_value, list):
            seen = set()
            out = []
            for x in normalized_value:
                key = str(x).strip().lower()
                if key in name_to_audience and key not in seen:
                    seen.add(key)
                    out.append(name_to_audience[key])
            if out:
                return {"status": "VALID", "reason_code": "OK", "normalized_value": out}
        return {"status": "INVALID", "reason_code": reason_code if reason_code in allowed_reason_codes else "UNRELATED", "normalized_value": None}
    except Exception:
        return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}


def validate_step(
    step_name: str,
    answer: Union[str, List[str], List[dict]],
    source: str,
    expected_step_name: Optional[str] = None,
    profile_context: Optional[Dict[str, Any]] = None,
    allowed_topics_for_step: Optional[List[dict]] = None,
    allowed_target_audiences_for_step: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    step = get_step_by_name(step_name)
    if not step:
        return {"status": "INVALID", "reason_code": "UNKNOWN_STEP", "normalized_value": None}
    if expected_step_name and step_name != expected_step_name:
        return {"status": "INVALID", "reason_code": "OUT_OF_ORDER", "normalized_value": None}

    normalized, err = _validate_basic(step, answer)
    if err:
        return {"status": "INVALID", "reason_code": _reason_code_from_basic_error(err), "normalized_value": None}

    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key) if api_key else None

    # code_full_name: format check + optional AI check for gibberish/random
    if step.validation_mode == "code_full_name":
        text = normalized if isinstance(normalized, str) else " ".join(normalized)
        if not validate_full_name(text):
            return {"status": "INVALID", "reason_code": "INVALID_FULL_NAME", "normalized_value": None}
        if client:
            ai_res = _validation_ai_full_name_check(client, text)
            if ai_res.get("status") == "INVALID":
                return {"status": "INVALID", "reason_code": "INVALID_FULL_NAME", "normalized_value": None}
        return {"status": "VALID", "reason_code": "OK", "normalized_value": _normalize_name_for_validation(text)}

    # email_regex: regex-only validation, no AI
    if step.validation_mode == "email_regex":
        text = (normalized if isinstance(normalized, str) else " ".join(str(x).strip() for x in normalized if str(x).strip())).strip()
        if not validate_email(text):
            return {"status": "INVALID", "reason_code": "INVALID_EMAIL", "normalized_value": None}
        return {"status": "VALID", "reason_code": "OK", "normalized_value": text.strip().lower()}

    # topics_multiselect: allowed values from DB (allowed_topics_for_step)
    if step.validation_mode == "topics_multiselect" and allowed_topics_for_step is not None:
        if source == "selection":
            # answer is list of topic objects; validate by _id/slug and return full topic objects
            if not isinstance(normalized, list) or not normalized:
                return {"status": "INVALID", "reason_code": "EMPTY", "normalized_value": None}
            by_id = {str(t.get("_id", "")).strip(): t for t in allowed_topics_for_step}
            by_slug = {str(t.get("slug", "")).strip().lower(): t for t in allowed_topics_for_step}
            out = []
            for sel in normalized:
                if not isinstance(sel, dict):
                    continue
                sid = str(sel.get("_id", "")).strip()
                sslug = str(sel.get("slug", "")).strip().lower()
                if sid and sid in by_id:
                    out.append(by_id[sid])
                elif sslug and sslug in by_slug:
                    out.append(by_slug[sslug])
            if not out:
                return {"status": "INVALID", "reason_code": "ENUM_INVALID", "normalized_value": None}
            # Dedupe by _id while preserving order
            seen_ids = set()
            deduped = []
            for t in out:
                tid = t.get("_id")
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    deduped.append(t)
            return {"status": "VALID", "reason_code": "OK", "normalized_value": deduped}
        else:
            # source == "text": AI maps user text to topic names, then we map to full topic objects
            text = normalized if isinstance(normalized, str) else " ".join(str(x).strip() for x in normalized if str(x).strip())
            if not text.strip():
                return {"status": "INVALID", "reason_code": "EMPTY", "normalized_value": None}
            if not client:
                return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
            ai_res = _validation_ai_enum_intent_topics(client, step, text, allowed_topics_for_step)
            return ai_res

    # target_audiences_multiselect: allowed values from DB (allowed_target_audiences_for_step)
    if step.validation_mode == "target_audiences_multiselect" and allowed_target_audiences_for_step is not None:
        if source == "selection":
            if not isinstance(normalized, list) or not normalized:
                return {"status": "INVALID", "reason_code": "EMPTY", "normalized_value": None}
            by_id = {str(t.get("_id", "")).strip(): t for t in allowed_target_audiences_for_step}
            by_slug = {str(t.get("slug", "")).strip().lower(): t for t in allowed_target_audiences_for_step}
            out = []
            for sel in normalized:
                if not isinstance(sel, dict):
                    continue
                sid = str(sel.get("_id", "")).strip()
                sslug = str(sel.get("slug", "")).strip().lower()
                if sid and sid in by_id:
                    out.append(by_id[sid])
                elif sslug and sslug in by_slug:
                    out.append(by_slug[sslug])
            if not out:
                return {"status": "INVALID", "reason_code": "ENUM_INVALID", "normalized_value": None}
            seen_ids = set()
            deduped = []
            for t in out:
                tid = t.get("_id")
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    deduped.append(t)
            return {"status": "VALID", "reason_code": "OK", "normalized_value": deduped}
        else:
            text = normalized if isinstance(normalized, str) else " ".join(str(x).strip() for x in normalized if str(x).strip())
            if not text.strip():
                return {"status": "INVALID", "reason_code": "EMPTY", "normalized_value": None}
            if not client:
                return {"status": "INVALID", "reason_code": "AI_UNAVAILABLE", "normalized_value": None}
            ai_res = _validation_ai_enum_intent_target_audiences(client, step, text, allowed_target_audiences_for_step)
            return ai_res

    normalized, err = _validate_rule_based(step, normalized, source)
    if err:
        if step.validation_mode == "strict_enum_code" and source == "text" and step.allowed_values:
            # Pass user's raw answer text directly to AI for intent matching
            text = answer.strip() if isinstance(answer, str) else " ".join(str(x).strip() for x in answer if str(x).strip())
            if text.strip():
                api_key = os.getenv("OPENAI_API_KEY")
                client = OpenAI(api_key=api_key) if api_key else None
                if client:
                    ai_res = _validation_ai_enum_intent(client, step, text)
                    if ai_res.get("status") == "VALID":
                        return ai_res
                    return {"status": "INVALID", "reason_code": ai_res.get("reason_code") or "ENUM_INVALID", "normalized_value": None}
        return {"status": "INVALID", "reason_code": _reason_code_from_rule_error(err), "normalized_value": None}

    # textarea_accept: code gibberish check + AI gibberish check when available; then accept
    if step.validation_mode == "textarea_accept":
        text = normalized if isinstance(normalized, str) else " ".join(str(x).strip() for x in normalized if str(x).strip())
        if step.required and not text.strip():
            return {"status": "INVALID", "reason_code": "EMPTY", "normalized_value": None}
        if _check_gibberish(text):
            return {"status": "INVALID", "reason_code": "GIBBERISH", "normalized_value": None}
        if client:
            ai_res = _validation_ai_gibberish_check(client, step, text)
            if ai_res.get("status") == "INVALID":
                return {"status": "INVALID", "reason_code": "GIBBERISH", "normalized_value": None}
        if step.split_on_conjunctions:
            parts = split_input_topics(text)
            text = ", ".join(parts) if parts else text
        return {"status": "VALID", "reason_code": "OK", "normalized_value": text}

    # No AI available for AI-backed step: accept input and continue (AI is helper, not gatekeeper)
    if step.uses_ai and not client:
        return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}

    try:
        if step.validation_mode == "semantic_text_ai":
            text = normalized if isinstance(normalized, str) else " ".join(normalized)
            # Optional field: empty is valid
            if not step.required and not text.strip():
                out = [] if step.validation_type in ("array_of_strings", "array_of_urls") else ""
                return {"status": "VALID", "reason_code": "OK", "normalized_value": out}
            if _check_gibberish(text):
                return {"status": "INVALID", "reason_code": "GIBBERISH", "normalized_value": None}
            if not client:
                return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}
            try:
                ai = _validation_ai_intent(client, step, text, profile_context=profile_context)
                if ai.get("reason_code") == "AI_UNAVAILABLE":
                    return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}
                if ai.get("status") == "VALID":
                    return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}
                reason_code = ai.get("reason_code") or "UNRELATED"
                if reason_code in SEMANTIC_OVERRIDE_REASON_CODES:
                    return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}
                return {"status": "INVALID", "reason_code": reason_code, "normalized_value": None}
            except Exception:
                return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}
    except Exception:
        return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}

    return {"status": "VALID", "reason_code": "OK", "normalized_value": normalized}


def get_init_response() -> dict:
    from app.services.SpeakerProfileConversation import generate_welcome_message
    first = get_first_step()
    payload = step_to_response(first)
    # Generate AI welcome message that includes the first step question
    welcome_message = generate_welcome_message(first.question)
    payload["question"] = welcome_message
    payload["assistant_message"] = welcome_message
    return payload


def get_expected_next_step(current_step_name: Optional[str] = None) -> Optional[str]:
    if current_step_name is None:
        return STEPS[0].step_name if STEPS else None
    for i, s in enumerate(STEPS):
        if s.step_name == current_step_name:
            if i + 1 < len(STEPS):
                return STEPS[i + 1].step_name
            return None
    return None


def validate_full_profile(
    profile_data: dict,
    allowed_topics: Optional[List[dict]] = None,
    allowed_target_audiences: Optional[List[dict]] = None,
) -> List[str]:
    errors = []
    field_mapping = {
        "full_name": ("full_name", "text"),
        "email": ("email", "text"),
        "topics": ("topics", "selection"),
        "speaking_formats": ("speaking_formats", "selection"),
        "delivery_mode": ("delivery_mode", "selection"),
        "linkedin_url": ("linkedin_url", "text"),
        "past_speaking_examples": ("past_speaking_examples", "text"),
        "video_links": ("video_links", "text"),
        "talk_description": ("talk_description", "text"),
        "key_takeaways": ("key_takeaways", "text"),
        "target_audiences": ("target_audiences", "selection"),
    }
    for step_def in STEPS:
        field_name = step_def.step_name
        if field_name not in field_mapping:
            continue
        value_key, default_source = field_mapping[field_name]
        value = profile_data.get(value_key)
        if not step_def.required and (value is None or value == [] or value == ""):
            continue
        source = default_source
        if step_def.validation_mode == "topics_multiselect":
            source = "selection" if isinstance(value, list) and value and isinstance(value[0], dict) else "text"
        elif step_def.validation_mode == "target_audiences_multiselect":
            source = "selection" if isinstance(value, list) and value and isinstance(value[0], dict) else "text"
        elif step_def.validation_mode == "strict_enum_code" and step_def.allowed_values:
            if isinstance(value, list):
                all_in_allowed = all(
                    str(v).strip().lower() in [a.lower() for a in step_def.allowed_values]
                    for v in value if v
                )
                source = "selection" if all_in_allowed else "text"
            elif isinstance(value, str):
                source = "selection" if value.strip().lower() in [a.lower() for a in step_def.allowed_values] else "text"
        res = validate_step(
            step_name=field_name,
            answer=value,
            source=source,
            profile_context=profile_data,
            allowed_topics_for_step=allowed_topics if field_name == "topics" else None,
            allowed_target_audiences_for_step=allowed_target_audiences if field_name == "target_audiences" else None,
        )
        if res.get("status") != "VALID":
            errors.append(field_name)
    return errors
