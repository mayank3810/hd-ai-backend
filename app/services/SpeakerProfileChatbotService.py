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
    TOPICS,
    SPEAKING_FORMATS,
    DELIVERY_MODE,
    TARGET_AUDIENCES,
    MANDATORY_FIELDS,
    MANDATORY_FIELDS_DISPLAY,
    OPTIONAL_FIELDS,
    OPTIONAL_FIELDS_DISPLAY,
)
from app.config.speaker_profile_steps import STEPS
from app.models.SpeakerProfile import PROFILE_FIELDS

logger = logging.getLogger(__name__)

_EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}"
)

# Steps for profile completion (excl. full_name, email). Required first, then optional.
_CHATBOT_REQUIRED_STEPS = ["topics", "speaking_formats", "delivery_mode", "talk_description", "target_audiences"]
_CHATBOT_OPTIONAL_STEPS = ["linkedin_url", "past_speaking_examples", "video_links", "key_takeaways"]

_ALLOWED_VALUES_MAP = {
    "topics": TOPICS,
    "speaking_formats": SPEAKING_FORMATS,
    "delivery_mode": DELIVERY_MODE,
    "target_audiences": TARGET_AUDIENCES,
}


def _get_steps_context() -> str:
    """Build context for LLM: step order, questions (for reframing), required vs optional."""
    lines = []
    for s in STEPS:
        if s.step_name in ("full_name", "email"):
            continue
        req = "required" if s.required else "optional (user can skip)"
        q = (s.question or "").replace("<br>", " ").strip()
        lines.append(f"- {s.step_name} ({req}): reference question: \"{q}\"")
    return "\n".join(lines) if lines else ""


def _build_get_allowed_values_tool() -> dict:
    """Tool for LLM to fetch valid options for topics, speaking_formats, delivery_mode, target_audiences."""
    return {
        "type": "function",
        "function": {
            "name": "get_allowed_values",
            "description": "Fetch the allowed/valid values for topics, speaking_formats, delivery_mode, or target_audiences. Call this BEFORE asking the user for these fields or validating their input. Use value_type to specify which field.",
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
                    "linkedin_url": {"type": "string"},
                    "past_speaking_examples": {"type": "array", "items": {"type": "string"}},
                    "video_links": {"type": "array", "items": {"type": "string"}},
                    "key_takeaways": {"type": "string"},
                    "name_salutation": {"type": "string"},
                    "bio": {"type": "string"},
                    "twitter": {"type": "string"},
                    "facebook": {"type": "string"},
                    "address_city": {"type": "string"},
                    "address_state": {"type": "string"},
                    "address_country": {"type": "string"},
                    "phone_country_code": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "professional_memberships": {"type": "array", "items": {"type": "string"}},
                    "preferred_speaking_time": {"type": "string"},
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


class SpeakerProfileChatbotService:
    def __init__(
        self,
        speaker_profile_model,
        speaker_topics_model,
        speaker_target_audience_model,
        chat_session_model,
    ):
        self.profile_model = speaker_profile_model
        self.topics_model = speaker_topics_model
        self.audience_model = speaker_target_audience_model
        self.chat_session_model = chat_session_model

    async def _resolve_topics(self, topic_names: List[str]) -> List[dict]:
        if not topic_names:
            return []
        filtered = _filter_enum_values(topic_names, TOPICS)
        if not filtered:
            return []
        return await self.topics_model.get_many_by_names(filtered)

    async def _resolve_target_audiences(self, audience_names: List[str]) -> List[dict]:
        if not audience_names:
            return []
        filtered = _filter_enum_values(audience_names, TARGET_AUDIENCES)
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
        speaking_formats = _filter_enum_values(
            [str(x).strip() for x in tool_args.get("speaking_formats", []) if x],
            SPEAKING_FORMATS,
        )
        if speaking_formats:
            doc["speaking_formats"] = speaking_formats
        delivery_mode = _filter_enum_values(
            [str(x).strip() for x in tool_args.get("delivery_mode", []) if x],
            DELIVERY_MODE,
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
        past = tool_args.get("past_speaking_examples")
        if isinstance(past, list):
            doc["past_speaking_examples"] = [str(x).strip() for x in past if x]
        video = tool_args.get("video_links")
        if isinstance(video, list):
            doc["video_links"] = [str(x).strip() for x in video if x]
        kt = (tool_args.get("key_takeaways") or "").strip()
        if kt:
            doc["key_takeaways"] = kt
        for k in ["name_salutation", "bio", "twitter", "facebook", "address_city", "address_state", "address_country", "phone_country_code", "phone_number", "preferred_speaking_time"]:
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

    async def _set_completed_if_mandatory_filled(
        self, speaker_profile_id: str, profile: dict
    ) -> Optional[dict]:
        """If all mandatory fields are filled, set isCompleted=True on the profile. Returns updated profile or None."""
        if not self._all_mandatory_filled(profile):
            return None
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
            # After every update: check mandatory fields; if all filled, set isCompleted=True
            refreshed = await self._set_completed_if_mandatory_filled(speaker_profile_id, updated)
            if refreshed:
                updated = refreshed
            return {"action": "updated", "profile": updated}
        # Create - email is required
        email = (args.get("email") or "").strip().lower()
        if not email:
            return {"action": "email_required", "profile": None}
        full_name = (args.get("full_name") or "").strip()
        profile_doc["email"] = email
        profile_doc["full_name"] = full_name or email.split("@")[0]  # Use email prefix if no name
        created = await self.profile_model.create_chatbot_profile(profile_doc, user_id)
        # After create: check mandatory fields; if all filled, set isCompleted=True
        spid = str(created.get("_id", ""))
        if spid:
            refreshed = await self._set_completed_if_mandatory_filled(spid, created)
            if refreshed:
                created = refreshed
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
            profile_snapshot_fields = ("full_name", "email", "topics", "target_audiences", "speaking_formats", "delivery_mode")
            profile_json = json.dumps({k: _ser(profile.get(k)) for k in profile_snapshot_fields if profile.get(k) is not None}, default=str)
            steps_ctx = _get_steps_context()
            system = (
                "You are a Expert assistant for onboarding People to Human Driven AI  Platform. "
                "A profile already exists. Current profile: " + profile_json + ". "
                "CRITICAL: When the user provides ANY profile data, call upsert_speaker_profile with speaker_profile_id=\"" + str(speaker_profile_id) + "\" and the field(s) to update. "
                "If the user has NOT provided an email address, ask again and do NOT call upsert_speaker_profile - instead respond to the user's message and ask them to provide their email address (e.g. reply to what they said, then say 'Please provide your email address so I can create your speaker profile.'). "
                "For topics, speaking_formats, delivery_mode, target_audiences: call get_allowed_values first to get valid options - do NOT guess. Only pass exact values from that tool to upsert_speaker_profile. "
                "If user gives values not in the allowed list, mention it and suggest closest matches. "
                "Question flow (ask one at a time, reframe naturally based on chat history and profile):\n" + steps_ctx + "\n"
                "Required fields (topics, speaking_formats, delivery_mode, talk_description, target_audiences) cannot be skipped. Optional fields (linkedin_url, past_speaking_examples, video_links, key_takeaways) - user can skip. Ask required first. "
                "When all mandatory fields are done, do NOT say 'let's move on to optional fields' or list optional fields - directly ask the next question (first optional: linkedin_url, then past_speaking_examples, video_links, key_takeaways). Continue one question at a time. When user asks about their profile, use the profile data above."
            )
        else:
            steps_ctx = _get_steps_context()
            system = (
                "You are a Expert assistant for onboarding People to Human Driven AI  Platform. "
                "You are a friendly assistant for Human Driven AI. The user has NO profile yet. Email is REQUIRED to create a profile. "
                "If the user has NOT provided an email address, ask again and do NOT call upsert_speaker_profile - instead respond to the user's message and ask them to provide their email address (e.g. reply to what they said, then say 'Please provide your email address so I can create your speaker profile.'). "
                "ONLY call upsert_speaker_profile when the user provides an email. Extract email and optionally full_name from the message. "
                "After creating the profile, guide them through questions one by one (do NOT ask verbatim - reframe naturally). For topics, speaking_formats, delivery_mode, target_audiences: call get_allowed_values first. "
                "Question flow (required first, then optional; user can skip optional):\n" + steps_ctx + "\n"
                "After profile creation, ask the first unfilled required field (topics, speaking_formats, delivery_mode, talk_description, target_audiences) in a natural, conversational way."
                ""
            )


        tools = [_build_upsert_tool(speaker_profile_id), _build_get_allowed_values_tool()]
        chat_messages = [{"role": "system", "content": system}, *messages]
        tool_results = []
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
                    allowed = _ALLOWED_VALUES_MAP.get(vt, [])
                    chat_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps({"allowed_values": allowed}),
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
                assistant_content = "Please provide your email address so I can create your speaker profile."
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
                prompt = "Briefly tell the user what was done." if action == "created" else ("Briefly tell the user what was updated." if action == "updated" else "Ask the user for their email address to create their speaker profile.")
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
                    assistant_content = "Your profile has been created!" if action == "created" else ("Your profile has been updated." if action == "updated" else "To get started, please share your email address so I can create your speaker profile.")

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

        # After any create/update: check mandatory fields. If all filled -> action = "completed"
        if profile:
            all_mandatory_filled = all(bool(profile.get(f)) for f in MANDATORY_FIELDS)
            if all_mandatory_filled:
                action = "completed"

        return {
            "assistant_message": assistant_content,
            "action": action,
            "speaker_profile_id": profile.get("_id") if profile else None,
            "chat_session_id": chat_session_id_out,
            "profile_snapshot": profile,
        }
