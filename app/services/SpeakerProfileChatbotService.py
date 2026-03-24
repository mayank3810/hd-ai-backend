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
    "testimonial",
    "linkedin_url",
    "past_speaking_examples",
    "video_links",
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

_INVALID_FIXED_LIST_GUIDANCE = (
    "If your choice is not on the list of available options, "
    "you can add it manually to your Speaker Profile following this chat."
)

_FIXED_LIST_USER_DEFERS = (
    "If the user says they will skip, or add or change these selections later from their profile "
    "(or similar), do not insist or repeat the full list: briefly tell them they can update their profile anytime, then move to the next question."
)

_PROFILE_COMPLETION_MESSAGE = (
    "Your speaker profile is complete. You may close this window and review your profile. Thank you!"
)

# Onboarding LLM may only offer catalog rows marked system (plus legacy docs without type).
_CATALOG_TYPE_FOR_LLM = "system"


def _prompt_option_lines(values: List[str], line_prefix: str = "                ") -> str:
    return "\n".join(f"{line_prefix}{v}  " for v in values)


def _prompt_topic_bullet_lines(names: List[str], line_prefix: str = "                ") -> str:
    return "\n".join(f"{line_prefix}• {t}  " for t in names)


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
        "then every optional field (talk_description, testimonial, linkedin_url, past_speaking_examples, video_links) one by one. "
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
    return {
        "type": "function",
        "function": {
            "name": "upsert_speaker_profile",
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "speaker_profile_id": {
                        "type": "string",
                        "description": "For UPDATE: REQUIRED, use value from chat session. For CREATE: omit.",
                    },
                    "email": {"type": "string", "description": "Email"},
                    "full_name": {"type": "string", "description": "Full name"},
                    "topics": {"type": "array", "items": {"type": "string"}, "description": "Call get_allowed_values(value_type='topics') first for valid options. Pass exact values only."},
                    "speaking_formats": {"type": "array", "items": {"type": "string"}, "description": "Call get_allowed_values(value_type='speaking_formats') first for valid options. Pass exact values only."},
                    "delivery_mode": {"type": "array", "items": {"type": "string"}, "description": "Call get_allowed_values(value_type='delivery_mode') first for valid options. Pass exact values only."},
                    "talk_description": {"type": "string"},
                    "target_audiences": {"type": "array", "items": {"type": "string"}, "description": "Call get_allowed_values(value_type='target_audiences') first for valid options. Pass exact values only."},
                    "linkedin_url": {"type": "string", "description": "LinkedIn profile URL when user provided one."},
                    "past_speaking_examples": {
                        "type": "array",
                        "items": _PAST_SPEAKING_ITEM_SCHEMA,
                        "description": (
                            "Past engagements as objects: organization_name, event_name, relevant_topics, "
                            "audience, date_month_year. Call get_allowed_values if needed for topics/audiences elsewhere."
                        ),
                    },
                    "video_links": {"type": "array", "items": {"type": "string"}},
                    "key_takeaways": {"type": "string", "description": "Legacy field; prefer testimonial for new profiles."},
                    "name_salutation": {"type": "string"},
                    "bio": {"type": "string"},
                    "twitter": {"type": "string", "description": "X/Twitter profile URL when user provided one."},
                    "facebook": {"type": "string", "description": "Facebook profile URL when user provided one."},
                    "instagram": {"type": "string", "description": "Instagram profile URL when user provided one."},
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
        topics_csv = ", ".join(catalog["topics"])
        formats_csv = ", ".join(catalog["speaking_formats"])
        delivery_csv = ", ".join(catalog["delivery_mode"])
        audiences_csv = ", ".join(catalog["target_audiences"])

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
                "testimonial",
                "past_speaking_examples",
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

                "Whenever listing options or structured information, strictly format the response as bullet points."       

                "EXISTING PROFILE CONTEXT: "
                "A speaker profile already exists. Current profile data: "
                + profile_json + ". "

                "CRITICAL FUNCTION RULES: "
                "Whenever the user provides ANY valid profile data, immediately call upsert_speaker_profile. "
                "Always pass speaker_profile_id=\"" + str(speaker_profile_id) + "\". "
                "Send ONLY the new or updated fields. "
                "Call after EVERY valid answer. "

                "CONVERSATION RULES: "
                "Ask ONLY ONE question at a time. "
                "Required fields cannot be skipped. "
                "If user avoids answering, politely ask again. "
                "If user provides multiple fields at once, extract and save all. "
                "Adapt questions naturally using chat history and profile_json. "
                "Stay focused ONLY on onboarding. "
                "Never announce that required fields are done or that you are moving to optional questions—just ask the next question with no preceding sentence. "

                "REQUIRED FIELD ORDER (STRICT): "
                "You MUST collect required fields in EXACT order: topics, speaking_formats, delivery_mode, target_audiences. "

                "ALLOWED VALUES come from the database (alphabetical). Current snapshot — "
                "TOPICS (User may choose multiple): "
                + topics_csv
                + ". SPEAKING FORMATS: "
                + formats_csv
                + ". DELIVERY MODE: "
                + delivery_csv
                + ". TARGET AUDIENCES (User may choose multiple): "
                + audiences_csv
                + ". "
                "You may also call get_allowed_values(value_type=...) for the latest lists. "
                "These lists include ONLY system catalog options (type=system); custom catalog rows are not offered here. "

                "VALIDATION RULES: "
                "Accept ONLY values from lists above. "
                "If user gives invalid values for any field that uses a fixed list (topics, speaking formats, delivery mode, target audiences, or any similar enumerated field), politely explain: \""
                + _INVALID_FIXED_LIST_GUIDANCE
                + "\" "
                "Suggest closest valid matches if possible. "
                + _FIXED_LIST_USER_DEFERS
                + " "

                "OPTIONAL FIELDS FLOW: "
                "When ALL required fields are completed, IMMEDIATELY continue by asking the first optional question. "
                "Ask EACH optional field ONE at a time in this exact order: "
                "talk_description, testimonial (testimonials from past speaking—not key takeaways), linkedin_url, past_speaking_examples, video_links. "
                "For talk_description, ask for their talk or expertise (title and overview). "
                "For testimonial, ask if they have testimonials from past speaking they would like to share. "
                "For past_speaking_examples, ask them to include organizations or events, topics, audience types, and timing; "
                "extract each engagement as an object with organization_name, event_name, relevant_topics, audience, date_month_year (month and year). "
                "For the social media step (after testimonial), ask using this wording: "
                "\"* Share your primary, professional social media channel URLs (e.g., LinkedIn, Facebook, X, Instagram, etc.).\" "
                "Parse the user's reply: place each full URL into the correct profile field via upsert_speaker_profile "
                "(linkedin_url, facebook, twitter, instagram). They may give one or several. "

                "CRITICAL BEHAVIOR RULE: "
                "When transitioning from required fields to optional fields, you MUST directly ask the next question with NO transition text. "
                "Your message must contain ONLY the question itself. No prefix. No explanation. No acknowledgment. No filler. "

                "STRICTLY FORBIDDEN: "
                "Do NOT say any sentence that mentions required fields, optional fields, completion, or transition. "
                "Never say phrases like: "
                "'Now that we have all the required fields', "
                "'Let’s move to optional questions', "
                "'Let’s move on', "
                "'Next, I will ask', "
                "'All required fields are done', "
                "'Mandatory fields complete', "
                "'Now the optional part'. "

                "RESPONSE FORMAT RULE: "
                "When it is time for an optional question, output ONLY the question. "
                "Example (correct): 'Please provide a description of your talk, including the title and overview.' "
                "Example (incorrect): 'Now that we’re done, please provide a description of your talk, including the title and overview.' "

                "SKIP HANDLING: "
                "If the user skips or declines an optional field, briefly acknowledge (e.g., 'No problem.') and IMMEDIATELY ask the next optional question. "

                "COMPLETION RULE: "
                "Do NOT call mark_profile_complete until AFTER the final optional question (video_links) has been asked."

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
            _topic_bullets_ml = _prompt_topic_bullet_lines(catalog["topics"])
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
                6. Talk Description (optional)
                7. Target Audience (required)

                Important Conversation Rules

                • Ask ONLY ONE question at a time.
                • Required fields cannot be skipped.
                • If the user avoids answering a required field, politely ask again.
                • If the user provides multiple fields at once, extract and store them.
                • Always guide the user to complete onboarding.

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

                The following fields MUST only contain values from the allowed lists below (system catalog only, type=system).
                Do NOT accept values outside these lists.

                Topics (User may choose multiple)

                Ask the user to select one or more from this list:

{_topics_ml}

                Speaking Format (Choose ONE)

{_formats_ml}

                Delivery Mode (choose one or more from the list)

{_delivery_ml}

                Target Audience (User may choose multiple)

{_audiences_ml}

                For any fixed-list field above, if the user's answer is not on the list, politely explain:

                "{_INVALID_FIXED_LIST_GUIDANCE}"

                If the user prefers to skip or says they will choose or update these later from their profile, do not push the list again:
                briefly say they can add or change these anytime from their profile, then move to the next question.

                Example:

                "What topics do you usually speak about?  
                You can choose one or more from the following:

{_topic_bullets_ml}"

                Talk Description (optional, ask before testimonial)

                When asking for this optional field, use wording like: "Please provide a description of your talk, including the title and overview."

                Testimonial (optional, ask immediately after talk description)

                Ask whether they have any testimonials from past speaking they would like to share; invite them to paste quotes or feedback.

                Social media URLs (optional, after testimonial)

                Ask: "* Share your primary, professional social media channel URLs (e.g., LinkedIn, Facebook, X, Instagram, etc.)."
                Parse replies and call upsert_speaker_profile with linkedin_url, facebook, twitter, and/or instagram (full URLs). If they defer to updating their profile later, acknowledge and continue.

                Past speaking examples (optional)

                Ask them to include organizations or events, relevant topics, and audience types. Extract each engagement as an object with:
                organization_name, event_name, relevant_topics, audience, date_month_year (month and year). Save via upsert_speaker_profile as past_speaking_examples (array of objects).

                Optional fields flow

                After all required fields are collected, you MUST ask each optional field one at a time: talk_description, testimonial, linkedin_url (social URLs question), past_speaking_examples, video_links. You must ask every optional question. If the user skips or declines, acknowledge and move to the next optional question. Only after you have asked the last optional question (user answered or skipped) may you call mark_profile_complete. FORBIDDEN: Never say 'Now that we have all the required fields', 'Let\'s move on to optional questions', 'Let\'s move on to some optional questions', or any sentence that announces required vs optional. When it is time for the next question (e.g. talk description), output ONLY that question—no preceding sentence.

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
                    assistant_content = f"Your profile has been created for {name}" + (f" ({email})!" if email else "!") + f" What would you like to add? You can add: Topics, Speaking formats, Delivery mode, Target audiences, Talk description."
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
