"""
Speaker Profile Chatbot Service: LLM-driven create/update via tool calls.
Flow: user message -> LLM -> tool call -> create/update profile -> ChatSession -> return.
"""
import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.config.speaker_profile_chatbot import (
    TOPICS,
    SPEAKING_FORMATS,
    DELIVERY_MODE,
    TARGET_AUDIENCES,
    MANDATORY_FIELDS,
    OPTIONAL_FIELDS,
    OPTIONAL_FIELDS_DISPLAY,
)
from app.models.SpeakerProfile import PROFILE_FIELDS

logger = logging.getLogger(__name__)

_EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}"
)

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
            "Create new speaker profile. Extract name and/or email from user message. "
            "Call with full_name and/or email. Omit speaker_profile_id. If neither found, omit both."
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
                    "topics": {"type": "array", "items": {"type": "string"}, "description": f"From: {TOPICS}"},
                    "speaking_formats": {"type": "array", "items": {"type": "string"}, "description": f"From: {SPEAKING_FORMATS}"},
                    "delivery_mode": {"type": "array", "items": {"type": "string"}, "description": f"From: {DELIVERY_MODE}"},
                    "talk_description": {"type": "string"},
                    "target_audiences": {"type": "array", "items": {"type": "string"}, "description": f"From: {TARGET_AUDIENCES}"},
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
            if k not in PROFILE_FIELDS or k in ("email", "_id"):
                continue
            if v is not None and v != "" and v != []:
                merged[k] = v
        return merged

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
                return {"action": "updated", "profile": profile}
            updates = {k: v for k, v in merged.items() if k != "email"}
            updated = await self.profile_model.update_profile(speaker_profile_id, updates)
            return {"action": "updated", "profile": updated}
        # Create
        email = (args.get("email") or "").strip().lower() or f"random-{uuid.uuid4().hex[:8]}@sample.com"
        full_name = (args.get("full_name") or "").strip() or f"Random user {uuid.uuid4().hex[:4]}"
        profile_doc["email"] = email
        profile_doc["full_name"] = full_name
        created = await self.profile_model.create_chatbot_profile(profile_doc, user_id)
        return {"action": "created", "profile": created}

    async def process_chat(
        self,
        message: str,
        chat_session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Simple flow:
        - No session_id: LLM creates profile via tool (name/email or synthetic), then we create ChatSession.
        - With session_id: load session + profile, LLM upserts via tool using speaker_profile_id.
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
                speaker_profile_id = session.get("speaker_profile_id")
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

            profile_json = json.dumps({k: _ser(v) for k, v in profile.items() if v is not None and k not in ("conversation", "completed_steps", "last_assistant_message", "current_step")}, default=str)
            system = (
                "You are a friendly assistant for Human Driven AI speaker profiles. "
                "A profile already exists. Current profile: " + profile_json + ". "
                "CRITICAL: When the user provides ANY profile data (name, email, topics, linkedin_url, talk_description, etc.), "
                "you MUST call upsert_speaker_profile with speaker_profile_id=\"" + str(speaker_profile_id) + "\" and the field(s) to update. "
                "speaker_profile_id comes from the chat session and MUST be included in every tool call for updates. "
                "Topics: " + ", ".join(TOPICS[:12]) + ". Formats: " + ", ".join(SPEAKING_FORMATS) + ". "
                "Delivery: " + ", ".join(DELIVERY_MODE) + ". Audiences: " + ", ".join(TARGET_AUDIENCES[:10]) + ". "
                "When all mandatory fields are filled, say mandatory fields are done and ask about optional: " + ", ".join(OPTIONAL_FIELDS_DISPLAY.get(f, f) for f in OPTIONAL_FIELDS) + "."
            )
        else:
            system = (
                "You are a friendly assistant for Human Driven AI. "
                "The user has NO profile yet. Extract their name and/or email from the message. "
                "Call upsert_speaker_profile with full_name and/or email (no speaker_profile_id). "
                "If neither name nor email found, omit both - backend will use synthetic. "
                "Topics: " + ", ".join(TOPICS[:12]) + ". Formats: " + ", ".join(SPEAKING_FORMATS) + ". "
                "Delivery: " + ", ".join(DELIVERY_MODE) + ". Audiences: " + ", ".join(TARGET_AUDIENCES[:10]) + ". "
                "After creating, say something like 'Your profile has been created!' and ask what they'd like to add next."
            )

        tools = [_build_upsert_tool(speaker_profile_id)]
        chat_messages = [{"role": "system", "content": system}, *messages]
        tool_results = []
        for _ in range(3):
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=chat_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.3,
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
                if tc.function.name != "upsert_speaker_profile":
                    continue
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                spid = (args.get("speaker_profile_id") or "").strip() or None
                result = await self._execute_upsert(args, spid or speaker_profile_id, user_id)
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
            prompt = "Briefly tell the user what was done." if action == "created" else "Briefly tell the user what was updated."
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
                assistant_content = "Your profile has been created!" if action == "created" else "Your profile has been updated."

        # ChatSession: create if new, else append
        chunk = [{"role": "user", "content": message or ""}, {"role": "assistant", "content": assistant_content}]
        if session:
            await self.chat_session_model.append_messages(chat_session_id, chunk)
            chat_session_id_out = chat_session_id
        else:
            spid_for_session = profile.get("_id") if profile else ""
            new_sess = await self.chat_session_model.create_session(speaker_profile_id=spid_for_session, messages=chunk)
            chat_session_id_out = new_sess["_id"]

        # After any create/update: check mandatory fields. If all filled -> action = "completed"
        if profile:
            all_mandatory_filled = all(bool(profile.get(f)) for f in MANDATORY_FIELDS)
            if all_mandatory_filled:
                action = "completed"
            # else: keep action as "created" or "updated" from tool result

        return {
            "assistant_message": assistant_content,
            "action": action,
            "speaker_profile_id": profile.get("_id") if profile else None,
            "chat_session_id": chat_session_id_out,
            "profile_snapshot": profile,
        }
