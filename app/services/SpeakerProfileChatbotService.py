"""
Speaker Profile Chatbot Service: conversation-based onboarding.
Uses LLM to extract profile data from messages, tool calling for create/update.
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
)
from app.models.SpeakerProfile import PROFILE_FIELDS

logger = logging.getLogger(__name__)

# Email regex for extraction
_EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}"
)

UPSERT_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "upsert_speaker_profile",
        "description": "Create or update a speaker profile. Call this when you have extracted email and profile data from the conversation. If email exists, update the profile; otherwise create new.",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Email address (required; first one found in conversation)",
                },
                "full_name": {"type": "string", "description": "Full name of the speaker"},
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"Topic names from: {TOPICS}",
                },
                "speaking_formats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"From: {SPEAKING_FORMATS}",
                },
                "delivery_mode": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"From: {DELIVERY_MODE}",
                },
                "talk_description": {"type": "string", "description": "Description of talk or expertise"},
                "target_audiences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"From: {TARGET_AUDIENCES}",
                },
                "linkedin_url": {"type": "string", "description": "LinkedIn profile URL"},
                "past_speaking_examples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Past speaking examples or events",
                },
                "video_links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Links to speaking videos (YouTube/Vimeo)",
                },
                "key_takeaways": {"type": "string", "description": "Key takeaways for audience"},
                "name_salutation": {"type": "string"},
                "bio": {"type": "string"},
                "twitter": {"type": "string"},
                "facebook": {"type": "string"},
                "address_city": {"type": "string"},
                "address_state": {"type": "string"},
                "address_country": {"type": "string"},
                "phone_country_code": {"type": "string"},
                "phone_number": {"type": "string"},
                "professional_memberships": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "preferred_speaking_time": {"type": "string"},
            },
            "required": ["email"],
        },
    },
}


def _extract_first_email_from_messages(messages: List[dict]) -> Optional[str]:
    """Extract first email from user messages in conversation."""
    for m in messages or []:
        if m.get("role") != "user":
            continue
        content = m.get("content")
        if isinstance(content, str):
            match = _EMAIL_REGEX.search(content)
            if match:
                return match.group(0).strip().lower()
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    match = _EMAIL_REGEX.search(text)
                    if match:
                        return match.group(0).strip().lower()
    return None


def _filter_enum_values(values: List[str], allowed: List[str]) -> List[str]:
    """Filter values to only those in allowed list (case-insensitive match)."""
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


def _normalize_profile_from_tool_args(args: dict) -> dict:
    """Normalize tool call args into profile-ready dict."""
    return {k: v for k, v in args.items() if v is not None and v != "" and v != [] and k in PROFILE_FIELDS}


class SpeakerProfileChatbotService:
    def __init__(
        self,
        speaker_profile_model,
        speaker_topics_model,
        speaker_target_audience_model,
    ):
        self.profile_model = speaker_profile_model
        self.topics_model = speaker_topics_model
        self.audience_model = speaker_target_audience_model

    async def _resolve_topics(self, topic_names: List[str]) -> List[dict]:
        """Resolve topic names to {_id, name, slug} from speakerTopics collection."""
        if not topic_names:
            return []
        filtered = _filter_enum_values(topic_names, TOPICS)
        if not filtered:
            return []
        return await self.topics_model.get_many_by_names(filtered)

    async def _resolve_target_audiences(self, audience_names: List[str]) -> List[dict]:
        """Resolve audience names to {_id, name, slug} from speakerTargetAudeince collection."""
        if not audience_names:
            return []
        filtered = _filter_enum_values(audience_names, TARGET_AUDIENCES)
        if not filtered:
            return []
        return await self.audience_model.get_many_by_names(filtered)

    async def _build_profile_doc(self, tool_args: dict) -> dict:
        """Build profile document from tool args, resolving topics and target_audiences."""
        doc = {}

        email = (tool_args.get("email") or "").strip().lower()
        if email:
            doc["email"] = email

        full_name = (tool_args.get("full_name") or "").strip()
        if full_name:
            doc["full_name"] = full_name

        topics_raw = tool_args.get("topics")
        if topics_raw and isinstance(topics_raw, list):
            topics_resolved = await self._resolve_topics([str(t).strip() for t in topics_raw])
            if topics_resolved:
                doc["topics"] = topics_resolved

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
            audiences_resolved = await self._resolve_target_audiences(
                [str(a).strip() for a in audiences_raw if a]
            )
            if audiences_resolved:
                doc["target_audiences"] = audiences_resolved

        linkedin = (tool_args.get("linkedin_url") or "").strip()
        if linkedin:
            doc["linkedin_url"] = linkedin
        elif "linkedin_url" not in doc:
            doc["linkedin_url"] = None

        past_examples = tool_args.get("past_speaking_examples")
        if isinstance(past_examples, list):
            doc["past_speaking_examples"] = [str(x).strip() for x in past_examples if x]
        elif past_examples is not None and past_examples != "":
            doc["past_speaking_examples"] = [str(past_examples).strip()]
        elif "past_speaking_examples" not in doc:
            doc["past_speaking_examples"] = []

        video_links = tool_args.get("video_links")
        if isinstance(video_links, list):
            doc["video_links"] = [str(x).strip() for x in video_links if x]
        elif video_links is not None and video_links != "":
            doc["video_links"] = [str(video_links).strip()]
        elif "video_links" not in doc:
            doc["video_links"] = []

        key_takeaways = (tool_args.get("key_takeaways") or "").strip()
        if key_takeaways:
            doc["key_takeaways"] = key_takeaways

        for field in [
            "name_salutation", "bio", "twitter", "facebook",
            "address_city", "address_state", "address_country",
            "phone_country_code", "phone_number", "preferred_speaking_time",
        ]:
            v = tool_args.get(field)
            if v is not None:
                if isinstance(v, str):
                    doc[field] = v.strip() or None
                else:
                    doc[field] = v

        pro_memberships = tool_args.get("professional_memberships")
        if isinstance(pro_memberships, list):
            doc["professional_memberships"] = [str(x).strip() for x in pro_memberships if x]
        elif pro_memberships:
            doc["professional_memberships"] = [str(pro_memberships).strip()]

        return doc

    async def _execute_upsert(self, email: str, profile_doc: dict, user_id: Optional[str] = None) -> dict:
        """Execute create or update. Returns result with action and profile."""
        profile_doc["email"] = email.strip().lower()
        existing = await self.profile_model.get_profile_by_email(email)
        if existing:
            updates = {k: v for k, v in profile_doc.items() if k != "email" and k != "createdAt" and k != "_id"}
            updated = await self.profile_model.update_chatbot_profile(email, updates)
            return {"action": "updated", "profile": updated}
        else:
            created = await self.profile_model.create_chatbot_profile(profile_doc, user_id)
            return {"action": "created", "profile": created}

    async def process_chat(
        self,
        body: dict,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        Process chat messages. Extracts email, runs LLM with tool calling, create/update profile,
        returns LLM-generated response about what was created/updated.
        body: dict with "messages" (list of {role, content}) - Open AI style.
        """
        messages = body.get("messages") or body.get("message") or []
        if not isinstance(messages, list):
            messages = []

        first_email = _extract_first_email_from_messages(messages)
        if not first_email:
            return {
                "assistant_message": "I couldn't find an email address in our conversation. Please share your email so I can create or update your speaker profile.",
                "profile": None,
                "action": None,
            }

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "assistant_message": "Service is temporarily unavailable. Please try again later.",
                "profile": None,
                "action": None,
            }

        client = OpenAI(api_key=api_key)
        system_content = (
            "You are a friendly assistant helping users create or update their speaker profile for Human Driven AI. "
            "From the conversation, extract the first email address and any profile information (name, topics, speaking formats, delivery mode, talk description, target audiences, etc.). "
            "Topics must be from: " + ", ".join(TOPICS) + ". "
            "Speaking formats from: " + ", ".join(SPEAKING_FORMATS) + ". "
            "Delivery mode from: " + ", ".join(DELIVERY_MODE) + ". "
            "Target audiences from: " + ", ".join(TARGET_AUDIENCES) + ". "
            "When you have enough info, call upsert_speaker_profile with email and the extracted data. "
            "Always extract the FIRST email from the conversation. After the tool returns, write a brief, friendly message summarizing what was saved (created or updated)."
        )

        chat_messages = [
            {"role": "system", "content": system_content},
            *[{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages],
        ]

        tool_results = []
        max_rounds = 3
        for _ in range(max_rounds):
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=chat_messages,
                tools=[UPSERT_TOOL_DEF],
                tool_choice="auto",
                temperature=0.3,
                timeout=30,
            )
            msg = completion.choices[0].message
            if not msg:
                break

            assistant_msg_dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_msg_dict["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                    for tc in msg.tool_calls
                ]
            chat_messages.append(assistant_msg_dict)

            tool_calls = msg.tool_calls or []
            if not tool_calls:
                profile_out = None
                action_out = None
                if tool_results:
                    last = tool_results[-1]
                    profile_out = last["profile"]
                    action_out = last["action"]
                    if profile_out and "_id" in profile_out:
                        profile_out["_id"] = str(profile_out["_id"])
                return {
                    "assistant_message": (msg.content or "").strip(),
                    "profile": profile_out,
                    "action": action_out,
                }

            for tc in tool_calls:
                if tc.function.name != "upsert_speaker_profile":
                    continue
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                tool_email = (args.get("email") or first_email).strip().lower()
                if not tool_email:
                    tool_email = first_email
                profile_doc = await self._build_profile_doc(args)
                result = await self._execute_upsert(tool_email, profile_doc, user_id)
                tool_results.append(result)
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"action": result["action"], "profile_id": str(result["profile"].get("_id", ""))}),
                }
                chat_messages.append(tool_msg)

        if not tool_results:
            last_msg = chat_messages[-1] if chat_messages else {}
            assistant_content = (last_msg.get("content", "") if isinstance(last_msg, dict) else "") or ""
            return {
                "assistant_message": assistant_content,
                "profile": None,
                "action": None,
            }

        last_result = tool_results[-1]
        profile = last_result["profile"]
        if profile and "_id" in profile:
            profile["_id"] = str(profile["_id"])

        last_msg = chat_messages[-1] if chat_messages else {}
        assistant_content = (last_msg.get("content", "") if isinstance(last_msg, dict) else "").strip()
        if not assistant_content or last_msg.get("role") == "tool":
            final = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=chat_messages + [
                    {"role": "user", "content": f"Great, the profile was {last_result['action']}. Reply briefly and warmly to the user confirming what was saved."}
                ],
                temperature=0.5,
                timeout=15,
            )
            assistant_content = (final.choices[0].message.content or "").strip() or "Your profile has been saved."
        return {
            "assistant_message": assistant_content,
            "profile": profile,
            "action": last_result["action"],
        }
