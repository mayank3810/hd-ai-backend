"""
Speaker Profile Chatbot Service: LLM-driven create/update via tool calls.
Flow: user message -> LLM -> tool call -> create/update profile -> ChatSession -> return.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.config.speaker_profile_chatbot import (
    MANDATORY_FIELDS,
    MANDATORY_FIELDS_DISPLAY,
    OPTIONAL_FIELDS,
    OPTIONAL_FIELDS_DISPLAY,
)
from app.models.SpeakerProfile import PROFILE_FIELDS

logger = logging.getLogger(__name__)

_EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}"
)

# Steps for profile completion (excl. full_name, email). Required first, then optional.
_CHATBOT_REQUIRED_STEPS = ["topics", "speaking_formats", "delivery_mode", "target_audiences"]
_CHATBOT_OPTIONAL_STEPS = [
    "talk_description",
    "key_takeaways",
    "linkedin_url",
    "past_speaking_examples",
    "video_links",
    "testimonial",
]

_PAST_SPEAKING_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "organization_name": {"type": "string"},
        "event_name": {"type": "string"},
        "relevant_topics": {"type": "string"},
        "audience": {"type": "string"},
        "date_month_year": {"type": "string", "description": "Month and year, e.g. March 2024"},
    },
}

# User-facing question only (no field-by-field template); LLM extracts structure for DB.
_PAST_SPEAKING_CHAT_QUESTION = (
    "Please share any past speaking engagements in your own words—where you spoke, what it was about, "
    "who the audience was, and roughly when. You can use paragraphs or short bullets per event; no form or labeled fields are required."
)

_SOCIAL_URL_FIELD_RULES = (
    "When the user pastes profile URLs, you MUST call upsert_speaker_profile in the same turn and map each URL to exactly one field: "
    "linkedin.com → linkedin_url; twitter.com or x.com → twitter; instagram.com → instagram; facebook.com → facebook. "
    "Use the full URL string. Example: https://www.linkedin.com/in/alex-robinson-analytics → linkedin_url; "
    "https://twitter.com/alexrobinson_ai or https://x.com/... → twitter; https://www.instagram.com/... → instagram; "
    "https://www.facebook.com/... → facebook. Pass only the fields they provided; omit others."
)

_INVALID_FIXED_LIST_GUIDANCE = (
    "Tell the user in one short sentence (second person—use 'you/your', not 'they/their'). "
    "When full_name is in profile_json (or the user gave their name earlier in chat), start with their first name for a conversational tone—"
    "e.g. 'Alex, if your choice isn't on this list, you can add or change it anytime from your speaker profile.' "
    "If you don't have a name, use the same line without a leading name: 'If your choice isn't on this list, you can add or change it anytime from your speaker profile.' "
    "FORBIDDEN when nothing matched the catalog: do NOT say you saved, recorded, added, or stored their wording (e.g. quoting 'train') for this field—nothing from that step was persisted if you omitted the field in upsert. "
    "In the SAME assistant message, add one short follow-up asking whether they would like to continue with the next onboarding question (yes/no)—use clear, professional wording. "
    "In that message do NOT ask the next profile question, do NOT show the next field's catalog bullets, do not paste the catalog again, "
    "do not re-ask the same field with a full option list, and do not insist they pick from the list."
)

# After off-catalog answers: acknowledge + ask to continue; only then show the next field (on yes).
_FIXED_LIST_ADVANCE_AFTER_OFF_LIST = (
    "OFF-LIST OR REFUSED-LIST (fixed catalog fields): If the user's answer does not match any allowed catalog name "
    "(topics, speaking_formats, delivery_mode, or target_audiences), treat that step as DONE for the conversation. "
    "In ONE assistant message (same turn, including after upsert_speaker_profile): (1) the one short 'you/your' profile sentence from the guidance above; "
    "(2) ask whether they would like to continue with the next question—do NOT include the next field's question, intro line, or bullet list in this message. "
    "HARD STOP after (2): same as PARTIAL/MIXED—no 'Now, let's discuss…', no bullets for the next catalog step in this message. "
    "Call upsert_speaker_profile with only fields that matched the catalog; omit fields with zero matches—do not block the flow. "
    "NEXT USER TURN: If they clearly want to continue (yes, sure, ok, yep, continue, let's go, go ahead, etc.), ask ONLY the next field in REQUIRED FIELD ORDER "
    "with that field's options as bullet points per CATALOG CHOICE QUESTIONS—never re-ask the step you closed. "
    "If they clearly want to pause (no, not now, later, not yet, hold on, etc.), reply in one short professional friendly message—"
    "e.g. that no problem, and they can let you know whenever they're ready to continue with the next question. "
    "Do NOT ask the next field's question in that pause reply and do NOT show its catalog bullets. "
    "If their reply is ambiguous, ask one brief clarifying question: continue now or pause? "
    "FORBIDDEN in the off-list acknowledgment message: any next-step catalog question or bullets (topics, formats, delivery, audiences, or optional fields). "
    "FORBIDDEN after off-list topics until they confirm continue: formats, delivery, or audiences questions/bullets. "
    "FORBIDDEN after off-list speaking_formats until they confirm continue: delivery or audiences questions/bullets. "
    "FORBIDDEN after off-list delivery_mode until they confirm continue: audiences or optional questions/bullets. "
    "FORBIDDEN after off-list target_audiences until they confirm continue: optional-field questions. "
    "After they confirm continue, the next field's options must be bullets—not comma-separated run-on lists."
)

# Some selections match the catalog and some do not (e.g. "AI and Agriculture")—same pause as off-list before next question.
_FIXED_LIST_PARTIAL_OR_MIXED_FLOW = (
    "PARTIAL/MIXED CATALOG ANSWERS (topics, speaking_formats, delivery_mode, target_audiences only): "
    "When the user names multiple selections or phrases for the CURRENT catalog step and at least one clearly maps to an allowed catalog option "
    "while at least one other clearly does NOT match any allowed option, call upsert_speaker_profile with ONLY the matched catalog values for that field—"
    "omit non-matching parts; do not invent catalog rows. "
    "That assistant turn is a CATALOG PAUSE TURN: your user-visible reply must contain ONLY these three parts and then END—no fourth part. "
    "(1) Briefly confirm ONLY the exact catalog name(s) you actually passed in upsert_speaker_profile for that field—never claim you saved unmatched wording. "
    "(2) One short sentence: the other topic(s)/selection(s) they mentioned aren't on this list; they can add or update those anytime from their speaker profile "
    "(second person; first name when full_name is known). "
    "(3) Ask whether they would like to continue with the next onboarding question (yes/no). "
    "HARD STOP after (3): do not append anything else—no blank line followed by another topic, no 'Now, let's discuss…', no 'Next…', no 'Please select…', no bullet list for speaking_formats, delivery_mode, target_audiences, or any later field. "
    "WRONG (violates this rule): After topics, saying you noted AI, that LinkedIn outreach and peanuts aren't on the list, then in the SAME message asking for speaking formats with • bullets—that bundles two steps; never do this. "
    "RIGHT: Same content through the profile line, then only the continue question; speaking formats come in the NEXT assistant message after the user says yes. "
    "NEXT USER TURN: Same as OFF-LIST—yes/continue → ask ONLY the next field in order with bullets; no/pause → short friendly deferral, no next question or bullets; ambiguous → one brief clarify. "
    "If EVERYTHING the user named for that step matches the catalog, do NOT use this pause: use CONVERSATIONAL WRAPPER and move to the next field (with bullets)—no redundant 'continue?' prompt. "
    "If NOTHING matches for that step, use ONLY the OFF-LIST flow, not this partial pattern."
)

# Prevent "I've saved your selection as 'train'" when train was never written to the profile.
_FIXED_LIST_USER_FACING_TRUTH = (
    "TRUTHFUL COPY FOR CATALOG FIELDS (topics, speaking_formats, delivery_mode, target_audiences): "
    "What you say to the user MUST match upsert_speaker_profile in the same turn. "
    "NEVER claim you saved, recorded, added, or stored a value for one of these fields using the user's free text (e.g. quoting 'train') "
    "unless that exact string is an allowed catalog name you included in the tool arguments for that field. "
    "If you omitted the field or passed an empty list because nothing matched, say only that their choice isn't on the list and they can update from their profile—do not describe their invalid wording as saved. "
    "For partial/mixed answers, only name persisted catalog matches; for the rest, say not on the list / add from profile—never both 'saved as X' and 'not on the list' for the same X."
)

# Models often compress catalog questions into "A, B, or C?" after seeing compact examples—reinforce bullets.
_CATALOG_OPTIONS_BULLET_FORMAT = (
    "CATALOG CHOICE QUESTIONS (topics, speaking_formats, delivery_mode, target_audiences): Whenever you ask the user to pick from the catalog, "
    "list the choices as bullet points—one option per line using • or - and the EXACT catalog names from get_allowed_values or the snapshot. "
    "Do NOT squeeze options into one sentence with commas or em-dashes (e.g. avoid 'Hybrid, In-person, or Virtual'). "
    "You may add one short intro line before the bullets (e.g. 'What speaking formats do you offer?'). "
    "After the user confirms they want to continue following an off-list OR partial/mixed catalog answer, the NEXT field's options must still be bullets; "
    "those pause turns are only profile-related sentences plus the continue question—no bullets for the next step there. "
    "This is not 'dumping the whole catalog': showing one category's list as bullets is required; forbidden is re-pasting every category when only one step is active."
)

_FIXED_LIST_USER_DEFERS = (
    "If the user says they will skip, or add or change these selections later from their profile "
    "(or similar), do not insist or repeat the full list: briefly tell them they can update their profile anytime "
    "(use first name from full_name when known, e.g. 'Jordan, you can update that anytime from your profile'), then move to the next question."
)

_PROFILE_COMPLETION_MESSAGE = (
    "Your speaker profile is complete. You may close this window and review your profile. Thank you!"
)

# Models often announce "optional fields" to the user; keep onboarding seamless.
_FORBIDDEN_OPTIONAL_FIELDS_TRANSITION_USER_TEXT = (
    "USER-FACING FORBIDDEN: Never announce that you are moving to or starting optional content. "
    "Do NOT say (or close variants of): "
    "Now let's move on to the optional fields; let us move on to the optional fields; "
    "moving on to optional fields; next we'll cover optional fields; the optional fields section; "
    "time for optional fields; optional questions next; we'll ask some optional questions; "
    "the optional part of your profile; or any transition that names optional fields, optional questions, or optional sections. "
    "Jump straight to the next concrete question with CONVERSATIONAL WRAPPER—never label a step as required, optional, or mandatory to the user."
)

# Warmer than bare Q&A; prescribed question strings stay verbatim after the opener.
_CONVERSATIONAL_ACK_BEFORE_QUESTION = (
    "CONVERSATIONAL WRAPPER (default): When you are moving on to ask a NEW profile field and this is NOT a catalog pause turn, begin with ONE short sentence—"
    "acknowledge their last answer, react warmly, or add one helpful line on why the next field matters (second person, professional, ≤25 words). "
    "Then ask the next question in the same message. Do not alter wording where instructions require EXACT or verbatim text—paste that question exactly after your opener (blank line between is fine). "
    "For catalog steps, opener → then your short intro line for that field → then bullet list (per CATALOG CHOICE QUESTIONS). "
    "CRITICAL OVERRIDE — CATALOG PAUSE TURN (off-list OR partial/mixed for topics, speaking_formats, delivery_mode, target_audiences): "
    "Ignore the default wrapper for that same assistant message. The entire user-facing reply is ONLY what OFF-LIST or PARTIAL/MIXED requires, ending with the yes/no continue question—then STOP. "
    "Do not chain a second question in that message: no 'Now, let's discuss…', 'Next…', or any request to pick speaking formats / delivery / audiences / optional fields, and no • bullets for a future step. "
    "After the user confirms they want to continue, the FOLLOWING assistant message may use the normal wrapper plus the next field's question and bullets. "
    "Still use ONLY the exact completion message after mark_profile_complete—no preamble there."
)

# Onboarding LLM may only offer catalog rows marked system (plus legacy docs without type).
_CATALOG_TYPE_FOR_LLM = "system"


def _prompt_option_lines(values: List[str], line_prefix: str = "                ") -> str:
    return "\n".join(f"{line_prefix}{v}  " for v in values)


def _prompt_topic_bullet_lines(names: List[str], line_prefix: str = "                ") -> str:
    return "\n".join(f"{line_prefix}• {t}  " for t in names)


def _format_catalog_allowed_values_bullets(catalog: Dict[str, List[str]], line_prefix: str = "                ") -> str:
    """Multi-line bullet block for ALLOWED VALUES in the system prompt."""
    def section(title: str, key: str) -> str:
        names = catalog.get(key) or []
        body = _prompt_topic_bullet_lines(names, line_prefix) if names else f"{line_prefix}• (none)"
        return f"{title}\n{body}"

    return "\n\n".join(
        [
            section("TOPICS (User may choose multiple):", "topics"),
            section("SPEAKING FORMATS:", "speaking_formats"),
            section("DELIVERY MODE:", "delivery_mode"),
            section("TARGET AUDIENCES (User may choose multiple):", "target_audiences"),
        ]
    )


def _build_get_allowed_values_tool() -> dict:
    """Tool for LLM to fetch valid options for topics, speaking_formats, delivery_mode, target_audiences."""
    return {
        "type": "function",
        "function": {
            "name": "get_allowed_values",
            "description": "Fetch allowed values for topics, speaking_formats, delivery_mode, or target_audiences from the system catalog only (type=system). Call before asking or validating these fields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value_type": {
                        "type": "string",
                        "enum": ["topics", "speaking_formats", "delivery_mode", "target_audiences"],
                        "description": "Which field's allowed values to fetch.",
                    },
                },
                "required": ["value_type"],
            },
        },
    }


def _build_mark_profile_complete_tool(speaker_profile_id: Optional[str] = None) -> dict:
    """Tool for LLM to mark profile complete only after ALL questions (required + optional) are asked."""
    desc = (
        "Call this ONLY when you have asked for ALL profile fields: "
        "first every required field (topics, speaking_formats, delivery_mode, target_audiences), "
        "then every optional field (talk_description, key_takeaways, linkedin_url, past_speaking_examples, video_links, testimonial) one by one. "
        "You MUST ask each optional question; if the user skips or declines, acknowledge and move to the next optional question. "
        "After you have asked the last optional question and the user has either answered or skipped it, call this once to mark the profile complete. "
        "Do NOT call this when only required fields are done—you must ask all optional questions first (user may skip, but you must ask and move on)."
    )
    return {
        "type": "function",
        "function": {
            "name": "mark_profile_complete",
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "speaker_profile_id": {
                        "type": "string",
                        "description": "Required. The speaker profile id from the chat session.",
                    },
                },
                "required": ["speaker_profile_id"],
            },
        },
    }


def _build_upsert_tool(speaker_profile_id_from_session: Optional[str] = None):
    """Build tool def. When speaker_profile_id_from_session is set, emphasize UPDATE with that id."""
    if speaker_profile_id_from_session:
        desc = (
            f"Update speaker profile. speaker_profile_id is REQUIRED: use \"{speaker_profile_id_from_session}\". "
            "Call this whenever the user provides ANY profile data to add or change (name, email, topics, linkedin_url, etc.). "
            "Pass speaker_profile_id and the fields to update."
        )
    else:
        desc = (
            "Create new speaker profile. Call this ONLY when the user provides an email address. "
            "Email is REQUIRED for profile creation. If the user has not provided email, do NOT call this - instead ask them for their email. "
            "Extract email and optionally full_name from the user message. Omit speaker_profile_id for create."
        )
    upsert_desc = (
        desc
        + " "
        + _SOCIAL_URL_FIELD_RULES
        + " For past_speaking_examples, extract structured objects from the user's natural language; never ask them to fill a labeled form."
        + " For topics, speaking_formats, delivery_mode, target_audiences: never tell the user you saved a value unless it is an exact catalog match you passed in this call."
    )
    return {
        "type": "function",
        "function": {
            "name": "upsert_speaker_profile",
            "description": upsert_desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "speaker_profile_id": {
                        "type": "string",
                        "description": "For UPDATE: REQUIRED, use value from chat session. For CREATE: omit.",
                    },
                    "email": {"type": "string", "description": "Email"},
                    "full_name": {"type": "string", "description": "Full name"},
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Only catalog names from get_allowed_values(value_type='topics'). "
                            "If the user's wording matches nothing, omit topics entirely; follow OFF-LIST flow (profile sentence + ask to continue)—"
                            "only after they agree, ask speaking_formats with bullets—never re-ask topics in the same turn as the off-list ack. "
                            "If some named topics match the catalog and some do not, pass only matches; use PARTIAL/MIXED flow "
                            "(confirm saved + unmatched can be updated from profile + ask to continue)—do not ask speaking_formats in that same message."
                        ),
                    },
                    "speaking_formats": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Catalog names from get_allowed_values(value_type='speaking_formats') only. "
                            "Zero matches → omit field; follow OFF-LIST flow first—only after user confirms continue, ask delivery_mode with bullets. "
                            "Partial match (some formats match, some do not) → save only matches; PARTIAL/MIXED flow before delivery_mode question."
                        ),
                    },
                    "delivery_mode": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Catalog names from get_allowed_values(value_type='delivery_mode') only. "
                            "Zero matches → omit field; follow OFF-LIST flow first—only after user confirms continue, ask target_audiences with bullets. "
                            "Partial match → save only matches; PARTIAL/MIXED flow before target_audiences question."
                        ),
                    },
                    "talk_description": {"type": "string"},
                    "target_audiences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Catalog names from get_allowed_values(value_type='target_audiences') only. "
                            "Zero matches → omit field; follow OFF-LIST flow first—only after user confirms continue, ask talk_description (optional flow). "
                            "Partial match → save only matches; PARTIAL/MIXED flow before optional talk_description. "
                            "In user-facing text, never claim you saved a string that you did not pass here as an exact catalog name."
                        ),
                    },
                    "linkedin_url": {"type": "string", "description": "Full LinkedIn profile URL only (linkedin.com)."},
                    "past_speaking_examples": {
                        "type": "array",
                        "items": _PAST_SPEAKING_ITEM_SCHEMA,
                        "description": (
                            "INTERNAL only: after the user writes free-form past engagements, extract one object per engagement "
                            "(organization_name, event_name, relevant_topics, audience, date_month_year). "
                            "Do not read these keys aloud to the user."
                        ),
                    },
                    "video_links": {"type": "array", "items": {"type": "string"}},
                    "key_takeaways": {
                        "type": "string",
                        "description": "Main points or learnings audiences get from their talks; save when user answers the key-takeaways question.",
                    },
                    "name_salutation": {"type": "string"},
                    "bio": {"type": "string"},
                    "twitter": {"type": "string", "description": "Full X/Twitter profile URL (twitter.com or x.com)."},
                    "facebook": {"type": "string", "description": "Full Facebook profile URL (facebook.com)."},
                    "instagram": {"type": "string", "description": "Full Instagram profile URL (instagram.com)."},
                    "address_city": {"type": "string"},
                    "address_state": {"type": "string"},
                    "address_country": {"type": "string"},
                    "phone_country_code": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "professional_memberships": {"type": "array", "items": {"type": "string"}},
                    "preferred_speaking_time": {"type": "string"},
                    "testimonial": {"type": "string"},
                },
            },
        },
    }


def _filter_enum_values(values: List[str], allowed: List[str]) -> List[str]:
    if not values:
        return []
    allowed_lower = {a.strip().lower(): a for a in allowed}
    out = []
    seen = set()
    for v in values:
        v = (v or "").strip()
        if not v:
            continue
        key = v.lower()
        if key in allowed_lower and key not in seen:
            seen.add(key)
            out.append(allowed_lower[key])
    return out


def _normalize_past_speaking_examples(raw: Any) -> List[dict]:
    """Coerce tool output to list of structured past speaking dicts."""
    out: List[dict] = []
    if not isinstance(raw, list):
        return out
    for x in raw:
        if isinstance(x, dict):
            row = {
                "organization_name": str(x.get("organization_name") or "").strip(),
                "event_name": str(x.get("event_name") or "").strip(),
                "relevant_topics": str(x.get("relevant_topics") or "").strip(),
                "audience": str(x.get("audience") or "").strip(),
                "date_month_year": str(x.get("date_month_year") or x.get("date") or "").strip(),
            }
            if any(row.values()):
                out.append(row)
        elif isinstance(x, str) and x.strip():
            out.append({
                "organization_name": "",
                "event_name": "",
                "relevant_topics": x.strip(),
                "audience": "",
                "date_month_year": "",
            })
    return out


class SpeakerProfileChatbotService:
    def __init__(
        self,
        speaker_profile_model,
        speaker_topics_model,
        speaker_target_audience_model,
        delivery_modes_model,
        speaking_formats_model,
        chat_session_model,
    ):
        self.profile_model = speaker_profile_model
        self.topics_model = speaker_topics_model
        self.audience_model = speaker_target_audience_model
        self.delivery_modes_model = delivery_modes_model
        self.speaking_formats_model = speaking_formats_model
        self.chat_session_model = chat_session_model
        self._catalog_name_lists: Optional[Dict[str, List[str]]] = None

    async def _load_catalog_name_lists(self) -> Dict[str, List[str]]:
        async def sorted_names(model) -> List[str]:
            rows = await model.get_all(doc_type=_CATALOG_TYPE_FOR_LLM)
            names = [str(r.get("name") or "").strip() for r in rows if r and r.get("name")]
            return sorted(set(names), key=str.lower)

        return {
            "topics": await sorted_names(self.topics_model),
            "speaking_formats": await sorted_names(self.speaking_formats_model),
            "delivery_mode": await sorted_names(self.delivery_modes_model),
            "target_audiences": await sorted_names(self.audience_model),
        }

    def _catalog_labels(self) -> Dict[str, List[str]]:
        return self._catalog_name_lists or {
            "topics": [],
            "speaking_formats": [],
            "delivery_mode": [],
            "target_audiences": [],
        }

    async def _resolve_topics(self, topic_names: List[str]) -> List[dict]:
        if not topic_names:
            return []
        allowed = self._catalog_labels().get("topics") or []
        if not allowed:
            allowed = [
                str(r.get("name") or "").strip()
                for r in await self.topics_model.get_all(doc_type=_CATALOG_TYPE_FOR_LLM)
                if r.get("name")
            ]
        filtered = _filter_enum_values(topic_names, allowed)
        if not filtered:
            return []
        return await self.topics_model.get_many_by_names(filtered)

    async def _resolve_target_audiences(self, audience_names: List[str]) -> List[dict]:
        if not audience_names:
            return []
        allowed = self._catalog_labels().get("target_audiences") or []
        if not allowed:
            allowed = [
                str(r.get("name") or "").strip()
                for r in await self.audience_model.get_all(doc_type=_CATALOG_TYPE_FOR_LLM)
                if r.get("name")
            ]
        filtered = _filter_enum_values(audience_names, allowed)
        if not filtered:
            return []
        return await self.audience_model.get_many_by_names(filtered)

    async def _build_profile_doc(self, tool_args: dict) -> dict:
        doc = {}
        email = (tool_args.get("email") or "").strip().lower()
        if email:
            doc["email"] = email
        full_name = (tool_args.get("full_name") or "").strip()
        if full_name:
            doc["full_name"] = full_name
        topics_raw = tool_args.get("topics")
        if topics_raw and isinstance(topics_raw, list):
            resolved = await self._resolve_topics([str(t).strip() for t in topics_raw])
            if resolved:
                doc["topics"] = resolved
        labels = self._catalog_labels()
        sf_allowed = labels.get("speaking_formats") or [
            str(r.get("name") or "").strip()
            for r in await self.speaking_formats_model.get_all(doc_type=_CATALOG_TYPE_FOR_LLM)
            if r.get("name")
        ]
        dm_allowed = labels.get("delivery_mode") or [
            str(r.get("name") or "").strip()
            for r in await self.delivery_modes_model.get_all(doc_type=_CATALOG_TYPE_FOR_LLM)
            if r.get("name")
        ]
        speaking_formats = _filter_enum_values(
            [str(x).strip() for x in tool_args.get("speaking_formats", []) if x],
            sf_allowed,
        )
        if speaking_formats:
            doc["speaking_formats"] = speaking_formats
        delivery_mode = _filter_enum_values(
            [str(x).strip() for x in tool_args.get("delivery_mode", []) if x],
            dm_allowed,
        )
        if delivery_mode:
            doc["delivery_mode"] = delivery_mode
        talk_desc = (tool_args.get("talk_description") or "").strip()
        if talk_desc:
            doc["talk_description"] = talk_desc
        audiences_raw = tool_args.get("target_audiences")
        if audiences_raw and isinstance(audiences_raw, list):
            resolved = await self._resolve_target_audiences([str(a).strip() for a in audiences_raw if a])
            if resolved:
                doc["target_audiences"] = resolved
        linkedin = (tool_args.get("linkedin_url") or "").strip()
        if linkedin:
            doc["linkedin_url"] = linkedin
        past = _normalize_past_speaking_examples(tool_args.get("past_speaking_examples"))
        if past:
            doc["past_speaking_examples"] = past
        video = tool_args.get("video_links")
        if isinstance(video, list):
            doc["video_links"] = [str(x).strip() for x in video if x]
        kt = (tool_args.get("key_takeaways") or "").strip()
        if kt:
            doc["key_takeaways"] = kt
        for k in ["name_salutation", "bio", "twitter", "facebook", "instagram", "address_city", "address_state", "address_country", "phone_country_code", "phone_number", "preferred_speaking_time", "testimonial"]:
            v = tool_args.get(k)
            if v is not None and isinstance(v, str):
                doc[k] = v.strip() or None
        pm = tool_args.get("professional_memberships")
        if isinstance(pm, list):
            doc["professional_memberships"] = [str(x).strip() for x in pm if x]
        return doc

    def _merge_for_update(self, existing: dict, profile_doc: dict) -> dict:
        merged = {k: v for k, v in existing.items() if k in PROFILE_FIELDS and k not in ("_id", "createdAt", "updatedAt")}
        for k, v in profile_doc.items():
            if k not in PROFILE_FIELDS or k == "_id":
                continue
            if v is not None and v != "" and v != []:
                merged[k] = v
        return merged

    def _get_fields_to_add_message(self, profile: Optional[dict] = None) -> str:
        """Return list of parameters user can add, as readable text."""
        remaining_mandatory = []
        for f in MANDATORY_FIELDS:
            if f in ("full_name", "email"):
                continue
            if not profile or not bool(profile.get(f)):
                remaining_mandatory.append(MANDATORY_FIELDS_DISPLAY.get(f, f))
        optional_labels = [OPTIONAL_FIELDS_DISPLAY.get(f, f) for f in OPTIONAL_FIELDS]
        parts = []
        if remaining_mandatory:
            parts.append("Required: " + ", ".join(remaining_mandatory))
        if optional_labels:
            parts.append("Optional: " + ", ".join(optional_labels))
        return ". ".join(parts) if parts else "additional profile details"

    def _all_mandatory_filled(self, profile: dict) -> bool:
        """Check if all MANDATORY_FIELDS are filled in the profile."""
        return all(bool(profile.get(f)) for f in MANDATORY_FIELDS)

    async def _set_profile_completed(self, speaker_profile_id: str) -> Optional[dict]:
        """Set isCompleted=True on the profile. Called only when mark_profile_complete tool is invoked."""
        return await self.profile_model.update_profile(
            speaker_profile_id,
            {"isCompleted": True},
        )

    async def _execute_upsert(
        self,
        args: dict,
        speaker_profile_id: Optional[str],
        user_id: Optional[str],
    ) -> dict:
        """Create or update by speaker_profile_id (when provided) or by email."""
        profile_doc = await self._build_profile_doc(args)
        if speaker_profile_id:
            profile = await self.profile_model.get_profile(speaker_profile_id)
            if not profile:
                return {"action": "error", "profile": None}
            merged = self._merge_for_update(profile, profile_doc)
            if not merged:
                updated = profile
            else:
                updates = dict(merged)
                updated = await self.profile_model.update_profile(speaker_profile_id, updates)
                if not updated:
                    return {"action": "error", "profile": None}
            # isCompleted is set only when LLM calls mark_profile_complete (after all questions done)
            return {"action": "updated", "profile": updated}
        # Create - email is required
        email = (args.get("email") or "").strip().lower()
        if not email:
            return {"action": "email_required", "profile": None}
        full_name = (args.get("full_name") or "").strip()
        profile_doc["email"] = email
        profile_doc["full_name"] = full_name or email.split("@")[0]  # Use email prefix if no name
        created = await self.profile_model.create_chatbot_profile(profile_doc, user_id)
        # isCompleted is set only when LLM calls mark_profile_complete (after all questions done)
        return {"action": "created", "profile": created}

    async def process_chat(
        self,
        message: str,
        chat_session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Flow:
        - No session_id: If message has no email, LLM asks for email; create ChatSession (no profile).
          If message has email, LLM creates profile via tool; create ChatSession with speaker_profile_id.
        - With session_id, no profile: Same - ask for email or create profile when email provided.
          If profile created, update session with speaker_profile_id.
        - With session_id + profile: LLM upserts via tool using speaker_profile_id.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "assistant_message": "Service is temporarily unavailable.",
                "action": None,
                "speaker_profile_id": None,
                "chat_session_id": chat_session_id,
                "profile_snapshot": None,
            }

        client = OpenAI(api_key=api_key)
        self._catalog_name_lists = await self._load_catalog_name_lists()
        catalog = self._catalog_name_lists
        catalog_allowed_bullets = _format_catalog_allowed_values_bullets(catalog)

        session = None
        speaker_profile_id = None
        profile = None
        history: List[Dict[str, Any]] = []

        if chat_session_id:
            session = await self.chat_session_model.get_by_id(chat_session_id)
            if session:
                speaker_profile_id = (session.get("speaker_profile_id") or "").strip() or None
                if speaker_profile_id:
                    profile = await self.profile_model.get_profile(speaker_profile_id)
                    if profile:
                        profile["_id"] = str(profile["_id"])
                conv = session.get("conversation") or []
                history = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in conv]

        messages = [*history, {"role": "user", "content": message or ""}]

        # Build system prompt
        if speaker_profile_id and profile:
            def _ser(o):
                if hasattr(o, "isoformat"):
                    return o.isoformat()
                if isinstance(o, dict):
                    return {k: _ser(v) for k, v in o.items()}
                if isinstance(o, list):
                    return [_ser(x) for x in o]
                return str(o) if hasattr(o, "hex") else o

            # Only include key profile fields so the LLM knows what data exists in the database
            profile_snapshot_fields = (
                "full_name",
                "email",
                "topics",
                "target_audiences",
                "speaking_formats",
                "delivery_mode",
                "talk_description",
                "key_takeaways",
                "linkedin_url",
                "twitter",
                "facebook",
                "instagram",
                "past_speaking_examples",
                "video_links",
                "testimonial",
            )
            profile_json = json.dumps({k: _ser(profile.get(k)) for k in profile_snapshot_fields if profile.get(k) is not None}, default=str)
            system = (
                "You are an expert onboarding assistant for the Human Driven AI platform. "

                "Your ONLY job is to onboard speakers by collecting and completing their profile through conversational chat. "
                "Do NOT help with anything outside onboarding. "
                "Do NOT offer help with unrelated topics. "
                "Do NOT say phrases like 'I can help with anything else', 'let me know if you need anything', or similar. "
                "If a user asks something unrelated to onboarding, politely redirect them back to completing their speaker profile. "
                "Always stay focused strictly on onboarding."

                "Tone: Strictly Friendly, conversational, and professional. "

                "Whenever listing options or structured information, strictly format the response as bullet points. "
                + _CATALOG_OPTIONS_BULLET_FORMAT
                + " "
                + _FIXED_LIST_USER_FACING_TRUTH
                + " "

                "EXISTING PROFILE CONTEXT: "
                "A speaker profile already exists. Current profile data: "
                + profile_json + ". "

                "CRITICAL FUNCTION RULES: "
                "Whenever the user provides ANY valid profile data, immediately call upsert_speaker_profile. "
                "Always pass speaker_profile_id=\"" + str(speaker_profile_id) + "\". "
                "Send ONLY the new or updated fields. "
                "Call after EVERY valid answer. "

                "CONVERSATION RULES: "
                "Ask for only ONE new profile field per turn (one main question), optionally preceded by one short ack sentence per CONVERSATIONAL WRAPPER—do not bundle two different fields in one turn. "
                "Catalog pause turns (off-list or partial/mixed) are NOT a turn that asks a new field—they only acknowledge and ask whether to continue; the next field is asked only after the user agrees. "
                "Required fields cannot be skipped EXCEPT for catalog fields (topics, speaking_formats, delivery_mode, target_audiences): "
                "if the user's answer matches no catalog option or they refuse the list, that counts as having addressed that step—use the OFF-LIST flow (profile sentence + ask if they want to continue); only after they agree, ask the next field in order; never re-ask that same catalog question in the off-list acknowledgment turn. "
                "If their answer is PARTIAL/MIXED (some catalog matches plus at least one clear non-catalog item for the same step), save only matches, use the PARTIAL/MIXED flow (confirm + profile note for unmatched + ask to continue)—same pause as off-list; only after they agree, ask the next field. "
                "If the user evades with an empty or unrelated non-answer, politely ask again. "
                "If user provides multiple fields at once, extract and save all. "
                "Adapt questions naturally using chat history and profile_json. "
                "Stay focused ONLY on onboarding. "
                "Never announce that required fields are done or that you are moving to optional questions—use the CONVERSATIONAL WRAPPER instead of process-speak. "
                + _FORBIDDEN_OPTIONAL_FIELDS_TRANSITION_USER_TEXT
                + " "
                + _CONVERSATIONAL_ACK_BEFORE_QUESTION
                + " "

                "REQUIRED FIELD ORDER (STRICT): "
                "You MUST collect required fields in EXACT order: topics, speaking_formats, delivery_mode, target_audiences. "

                "ALLOWED VALUES come from the database (alphabetical). Current snapshot (use bullet layout below when presenting options to the user):\n"
                + catalog_allowed_bullets
                + "\n\n"
                "You may also call get_allowed_values(value_type=...) for the latest lists. "
                "These lists include ONLY system catalog options (type=system); custom catalog rows are not offered here. "

                "VALIDATION RULES (fixed-list fields): "
                "Prefer values from the lists above when the user picks from them. "
                "If the user's answer is not on the list (or they refuse the list), use this response pattern in ONE short turn: "
                + repr(_INVALID_FIXED_LIST_GUIDANCE)
                + " "
                "PARTIAL/MIXED fixed-list answers: "
                + _FIXED_LIST_PARTIAL_OR_MIXED_FLOW
                + " "
                "FORBIDDEN after an off-list OR partial/mixed pause message: in that SAME assistant message, also asking the next field or showing the next field's bullets; repeating the closed step with a full option list; "
                "or pasting all four categories (topics+formats+delivery+audiences) in one message when only one step is active; or asking them to pick from the list a second time for the step you just closed. "
                "Allowed and required: when actively asking a catalog step (not an off-list or partial/mixed pause turn), show that step's options as bullet points (see CATALOG CHOICE QUESTIONS). "
                "Optional: you may offer at most one closest catalog name in a short phrase—without reprinting all options. "
                "Call upsert_speaker_profile only with valid list values you could match; if none, omit that field (OFF-LIST flow); if some match, pass only those (PARTIAL/MIXED flow when anything they named did not match); in both cases wait for continue before the next field's question. "
                + _FIXED_LIST_USER_DEFERS
                + " "
                + _FIXED_LIST_ADVANCE_AFTER_OFF_LIST
                + " "

                "OPTIONAL FIELDS FLOW: "
                "When ALL required fields are completed, IMMEDIATELY continue by asking the first optional question. "
                "Ask EACH optional field ONE at a time in this exact order: "
                "talk_description, key_takeaways, linkedin_url, past_speaking_examples, video_links, testimonial (last optional—testimonials from past speaking). "
                "For talk_description, ask for their talk or expertise (title and overview). "
                "For key_takeaways, ask using EXACTLY: \"What key takeaways would you like to highlight from your talks?\" "
                "Save the reply via upsert_speaker_profile as key_takeaways. "
                "For the social media step (after key_takeaways), ask using this wording: "
                "Share your primary, professional social media channel URLs (e.g., LinkedIn, Facebook, X, Instagram, etc.). "
                + _SOCIAL_URL_FIELD_RULES
                + " Call upsert_speaker_profile in the same assistant turn when they provide URLs. "
                "For past_speaking_examples (after social URLs), ask using EXACTLY this wording as the full message—no checklist, no headings like Organization name or Event name: "
                + repr(_PAST_SPEAKING_CHAT_QUESTION)
                + " "
                "FORBIDDEN for past_speaking: asking users to structure answers with per-field labels or 'each engagement must include'. "
                "After they reply in natural language, call upsert_speaker_profile with past_speaking_examples as an array of objects "
                "(organization_name, event_name, relevant_topics, audience, date_month_year)—extract best effort; do not echo those key names to the user. "
                "Then ask for video_links (YouTube/Vimeo-style URLs or skip). Last optional: testimonial—invite quotes or feedback from past speaking. "

                "STRICTLY FORBIDDEN: "
                "Do NOT say any sentence that mentions required fields, optional fields, completion, or transition. "
                "Never say phrases like: "
                "'Now that we have all the required fields', "
                "'Let’s move to optional questions', "
                "'Now let's move on to the optional fields', "
                "'Let's move on to optional fields', "
                "'moving on to optional fields', "
                "'Let’s move on', "
                "'Next, I will ask', "
                "'All required fields are done', "
                "'Mandatory fields complete', "
                "'Now the optional part', "
                "or asking for speaking formats, delivery mode, or target audiences (including 'Now, let's discuss the speaking formats' with bullets) in the SAME assistant message as an off-list or partial/mixed reply for the prior catalog step. "

                "RESPONSE FORMAT RULE: "
                "Use CONVERSATIONAL WRAPPER when asking a new field—EXCEPT on catalog pause turns (off-list or partial/mixed): those replies end after the continue question with no next-field question or bullets in the same message. "
                "Otherwise: one short ack/helpful sentence, then the question. "
                "When it is time for an optional free-text question, keep the question phrase itself unchanged from instructions (e.g. talk description wording, exact key_takeaways line). "
                "When it is time for a required catalog question (topics, speaking_formats, delivery_mode, target_audiences), "
                "format choices as bullet lists per CATALOG CHOICE QUESTIONS—not comma-separated inline lists. "
                "Example optional (good): 'Thanks—that helps.\\n\\nPlease provide a description of your talk, including the title and overview.' "
                "Example optional (bad—process meta): 'Now that we’re done with required fields, please provide a description…' "

                "SKIP HANDLING: "
                "If the user skips or declines an optional field, briefly acknowledge (e.g., 'No problem.') and IMMEDIATELY ask the next optional question. "

                "COMPLETION RULE: "
                "Do NOT call mark_profile_complete until AFTER the final optional question (testimonial) has been asked."

                "PROFILE COMPLETION: "
                "Only after you have ASKED for ALL fields (every required and every optional)—with each optional either answered or skipped (you moved to next)—call the tool mark_profile_complete with speaker_profile_id. "
                "Then respond with ONLY this exact completion message (no extra words): "
                + repr(_PROFILE_COMPLETION_MESSAGE)
                + " "
                "Do NOT add any offer to help further, e.g. do NOT say 'How can I assist you?', 'Let me know if you need anything', 'What else can I help with?', or similar. End with the completion message only. "

                "PROFILE QUESTIONS: "
                "If user asks about their profile, answer using profile_json only. "
                )
        else:
            _topics_ml = _prompt_option_lines(catalog["topics"])
            _formats_ml = _prompt_option_lines(catalog["speaking_formats"])
            _delivery_ml = _prompt_option_lines(catalog["delivery_mode"])
            _audiences_ml = _prompt_option_lines(catalog["target_audiences"])
            system = f"""
                You are an expert onboarding assistant for the Human Driven AI platform.

                "Your ONLY job is to onboard speakers by collecting and completing their profile through conversational chat. "
                "Do NOT help with anything outside onboarding. "
                "Do NOT offer help with unrelated topics. "
                "Do NOT say phrases like 'I can help with anything else', 'let me know if you need anything', or similar. "
                "If a user asks something unrelated to onboarding, politely redirect them back to completing their speaker profile. "
                "Always stay focused strictly on onboarding."

                Your tone should be:
                Friendly, conversational, and professional.

                You must collect the following information step-by-step.

                REQUIRED FIELDS
                1. Email (required – MUST be collected first)
                2. Full Name (required)
                3. Topics (required)
                4. Speaking Format (required)
                5. Delivery Mode (required)
                6. Target Audience (required)

                After all required fields above, ask optional fields one at a time in this order:
                talk_description, key_takeaways, social URLs (linkedin_url step), past_speaking_examples, video_links, testimonial (last).

                Important Conversation Rules

                • One new profile field per turn (one main question); you may add one short ack sentence before it (see CONVERSATIONAL WRAPPER)—except catalog pause turns (off-list or partial/mixed): those messages end after the continue question with no next-field question or bullets.
                • Required fields cannot be skipped EXCEPT: for catalog fields, if the user's answer matches nothing on the list or they refuse the list, use the OFF-LIST flow (profile sentence + ask to continue); if some items match and some do not, use PARTIAL/MIXED flow (confirm matches + profile note for unmatched + ask to continue); only after they agree, ask the next field—do not bundle the next question in those pause messages.
                • If the user avoids answering with an empty evasion, politely ask again.
                • If the user provides multiple fields at once, extract and store them.
                • Always guide the user to complete onboarding.

                {_FORBIDDEN_OPTIONAL_FIELDS_TRANSITION_USER_TEXT}

                {_CONVERSATIONAL_ACK_BEFORE_QUESTION}

                {_CATALOG_OPTIONS_BULLET_FORMAT}

                {_FIXED_LIST_USER_FACING_TRUTH}

                Email Rules

                • Email must be collected first.
                • Validate that it looks like a valid email address.
                • Once email is received, immediately call the function `upsert_speaker_profile` to create the profile.

                Data Saving

                Use the function `upsert_speaker_profile` whenever new data is collected.

                Call it:
                • Immediately after email is collected
                • After every additional field is captured

                Fixed Choice Fields

                Store in upsert_speaker_profile only exact matches from the allowed lists below (system catalog only, type=system).
                If the user names something not on the list, omit that field in upsert and use the OFF-LIST flow before the next field—never re-ask topics in the same message as the off-list profile sentence.
                If they name a mix (some on-list, some not), save only matches and use the PARTIAL/MIXED flow—never ask the next catalog step in that same message.

                Topics (User may choose multiple)

                Ask the user to select one or more from this list:

{_topics_ml}

                Speaking Format (Choose ONE)

{_formats_ml}

                Delivery Mode (choose one or more from the list)

{_delivery_ml}

                Target Audience (User may choose multiple)

{_audiences_ml}

                For any fixed-list field above, if the user's answer is not on the list, use one brief reply:

                "{_INVALID_FIXED_LIST_GUIDANCE}"

                If the user prefers to skip or update later from their profile, do not push the list: acknowledge and go to the next question.

                FORBIDDEN: After that explanation, do NOT immediately re-ask the same field with a full list (topics, formats, delivery, or audiences), and do NOT paste all four category lists in one message when only one step is active.

                CORRECT pattern after any off-list fixed-field answer: one short "you/your" sentence (profile update later), then ask whether they want to continue with the next question—no next-field question or bullets in that same message. After they say yes, ask the next required field with that field's options as bullet points only—not comma-separated inline lists.

                CORRECT pattern after a PARTIAL/MIXED answer: confirm saved catalog match(es); one line that the unmatched wording can be added or updated from their speaker profile; ask whether to continue—then STOP (no speaking formats question or • bullets in that same message). WRONG: adding 'Now, let's discuss speaking formats' with a bullet list below.

                {_FIXED_LIST_ADVANCE_AFTER_OFF_LIST}

                {_FIXED_LIST_PARTIAL_OR_MIXED_FLOW}

                Talk Description (optional, first optional after required fields)

                When asking for this optional field, use wording like: "Please provide a description of your talk, including the title and overview."

                Key takeaways (optional, immediately after talk description)

                Ask using EXACTLY: "What key takeaways would you like to highlight from your talks?" Save via upsert_speaker_profile as key_takeaways.

                Social media URLs (optional, after key takeaways)

                Ask: "* Share your primary, professional social media channel URLs (e.g., LinkedIn, Facebook, X, Instagram, etc.)."
                {_SOCIAL_URL_FIELD_RULES} Call upsert_speaker_profile in the same turn when they provide URLs. If they defer to updating their profile later, acknowledge and continue.

                Past speaking examples (optional, after social URLs)

                Ask using EXACTLY this wording (verbatim): {_PAST_SPEAKING_CHAT_QUESTION}

                FORBIDDEN: do not ask for labeled fields (Organization name, Event name, etc.) or a rigid template.

                After natural-language replies, extract engagements and call upsert_speaker_profile with past_speaking_examples (array of objects). Do not read schema key names aloud to the user.

                Video links (optional, after past speaking)

                Ask for links to speaking videos (e.g. YouTube or Vimeo) or accept skip.

                Testimonial (optional, LAST optional question before completion)

                Ask whether they have any testimonials from past speaking they would like to share; invite them to paste quotes or feedback.

                Optional fields flow

                After all required fields are collected, you MUST ask each optional field one at a time: talk_description, key_takeaways, linkedin_url (social URLs question), past_speaking_examples, video_links, testimonial (last). You must ask every optional question. If the user skips or declines, acknowledge and move to the next optional question. Only after you have asked the last optional question (testimonial—user answered or skipped) may you call mark_profile_complete. FORBIDDEN: Never say 'Now that we have all the required fields', 'Let\'s move on to optional questions', 'Let\'s move on to some optional questions', 'Now let\'s move on to the optional fields', 'moving on to optional fields', or any sentence that announces required vs optional or optional fields as a section. For each next question, use CONVERSATIONAL WRAPPER (short ack or helpful line, then the question—verbatim where specified).

                Completion

                Only after you have asked all questions for all fields (required + optional; each optional either answered or skipped—you moved on), say ONLY this exact completion message with no additions: {_PROFILE_COMPLETION_MESSAGE} Do NOT add 'How can I assist you?', 'Let me know if you need anything', or similar.
                """
        tools = [_build_upsert_tool(speaker_profile_id), _build_get_allowed_values_tool()]
        if speaker_profile_id:
            tools.append(_build_mark_profile_complete_tool(speaker_profile_id))
        chat_messages = [{"role": "system", "content": system}, *messages]
        tool_results = []
        profile_marked_complete = False
        for _ in range(3):
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=chat_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.25,
                timeout=30,
            )
            msg = completion.choices[0].message
            if not msg:
                break
            asst = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                asst["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                    for tc in msg.tool_calls
                ]
            chat_messages.append(asst)
            tcs = msg.tool_calls or []
            if not tcs:
                break
            for tc in tcs:
                try:
                    tc_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tc_args = {}
                if tc.function.name == "get_allowed_values":
                    vt = (tc_args.get("value_type") or "").strip().lower()
                    cmap = self._catalog_name_lists or {}
                    allowed = cmap.get(vt, [])
                    chat_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({"allowed_values": allowed}),
                    })
                    continue
                if tc.function.name == "mark_profile_complete":
                    spid = (tc_args.get("speaker_profile_id") or "").strip() or speaker_profile_id
                    if spid and self._all_mandatory_filled(profile or {}):
                        await self._set_profile_completed(spid)
                        profile_marked_complete = True
                        if profile:
                            profile["isCompleted"] = True
                    chat_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({
                            "success": True,
                            "user_message_must_be_exactly": _PROFILE_COMPLETION_MESSAGE,
                        }),
                    })
                    continue
                if tc.function.name != "upsert_speaker_profile":
                    continue
                spid = (tc_args.get("speaker_profile_id") or "").strip() or None
                result = await self._execute_upsert(tc_args, spid or speaker_profile_id, user_id)
                tool_results.append(result)
                if result.get("profile"):
                    profile = result["profile"]
                    profile["_id"] = str(profile["_id"])
                chat_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"action": result.get("action"), "profile_id": str(profile.get("_id", "")) if profile else ""}),
                })

        action = None
        if tool_results:
            action = tool_results[-1].get("action")
            if profile is None and tool_results[-1].get("profile"):
                profile = tool_results[-1]["profile"]
                profile["_id"] = str(profile["_id"])

        assistant_content = ""
        last = chat_messages[-1] if chat_messages else {}
        if isinstance(last, dict) and last.get("role") == "assistant":
            assistant_content = (last.get("content") or "").strip()
        if not assistant_content or last.get("role") == "tool":
            if action == "email_required":
                assistant_content = "How can I assist you today to create a speaker profile? I'll need your email address to get started."
            elif action == "created" and profile:
                name = (profile.get("full_name") or "").strip() or "you"
                email = (profile.get("email") or "").strip() or ""
                prompt = f"Briefly tell the user their profile was created for {name}" + (f" ({email})" if email else "") + ". Then naturally ask for the first required field (topics - what topics they speak about) in a conversational way, reframed - do not ask the question verbatim."
                try:
                    s = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=chat_messages + [{"role": "user", "content": prompt}],
                        temperature=0.5,
                        timeout=15,
                    )
                    assistant_content = (s.choices[0].message.content or "").strip()
                except Exception:
                    pass
                if not assistant_content:
                    assistant_content = f"Your profile has been created for {name}" + (f" ({email})!" if email else "!") + f" What would you like to add? You can add: Topics, Speaking formats, Delivery mode, Target audiences, Talk description, Key takeaways, and more."
            else:
                prompt = "Briefly tell the user what was done." if action == "created" else ("Briefly tell the user what was updated." if action == "updated" else "How can I assist you today to create a speaker profile? I'll need your email address to get started.")
                if not assistant_content:
                    try:
                        s = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=chat_messages + [{"role": "user", "content": prompt}],
                            temperature=0.5,
                            timeout=15,
                        )
                        assistant_content = (s.choices[0].message.content or "").strip()
                    except Exception:
                        pass
                if not assistant_content:
                    if profile_marked_complete:
                        assistant_content = _PROFILE_COMPLETION_MESSAGE
                    else:
                        assistant_content = "Your profile has been created!" if action == "created" else ("Your profile has been updated." if action == "updated" else "How can I assist you today to create a speaker profile? I'll need your email address to get started.")

        if profile_marked_complete:
            assistant_content = _PROFILE_COMPLETION_MESSAGE

        # ChatSession: create if new, else append
        chunk = [{"role": "user", "content": message or ""}, {"role": "assistant", "content": assistant_content}]
        if session:
            await self.chat_session_model.append_messages(chat_session_id, chunk)
            chat_session_id_out = chat_session_id
            # If profile was just created and session had no speaker_profile_id, update session
            if profile and action == "created":
                existing_spid = (session.get("speaker_profile_id") or "").strip()
                if not existing_spid and profile.get("_id"):
                    await self.chat_session_model.update_speaker_profile_id(
                        chat_session_id, str(profile["_id"])
                    )
        else:
            spid_for_session = profile.get("_id") if profile else ""
            new_sess = await self.chat_session_model.create_session(speaker_profile_id=spid_for_session, messages=chunk)
            chat_session_id_out = new_sess["_id"]

        # Set action = "completed" only when profile was explicitly marked complete (all questions done)
        if profile_marked_complete:
            action = "completed"

        self._catalog_name_lists = None
        return {
            "assistant_message": assistant_content,
            "action": action,
            "speaker_profile_id": profile.get("_id") if profile else None,
            "chat_session_id": chat_session_id_out,
            "profile_snapshot": profile,
        }
