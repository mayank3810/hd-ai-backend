"""
AI agent that checks whether a single opportunity matches a speaker profile.
Used after vector matching to filter opportunities before saving to matchedOpportunities.
"""
import json
import logging
import os
import re
from typing import Any, Dict

from openai import OpenAI

from app.helpers.PineconeOpportunityStore import OpportunityTextBuilder

logger = logging.getLogger(__name__)


def _summary_profile(profile: dict) -> str:
    """Build a short text summary of speaker profile for the LLM."""
    parts = []
    topics = OpportunityTextBuilder._to_str(profile.get("topics") or [])
    if topics:
        parts.append(f"Topics: {topics}")
    formats = profile.get("speaking_formats") or []
    if isinstance(formats, list):
        f_str = " ".join(OpportunityTextBuilder._item_text(s) for s in formats if s)
        if f_str:
            parts.append(f"Speaking formats: {f_str}")
    delivery = OpportunityTextBuilder._to_str(profile.get("delivery_mode"))
    if delivery:
        parts.append(f"Delivery mode: {delivery}")
    audiences = OpportunityTextBuilder._to_str(profile.get("target_audiences") or [])
    if audiences:
        parts.append(f"Target audiences: {audiences}")
    talk = (profile.get("talk_description") or "").strip()
    if isinstance(profile.get("talk_description"), str) and talk:
        parts.append(f"Talk description: {talk[:500]}")
    return "\n".join(parts) if parts else ""


def _summary_opportunity(opp: dict) -> str:
    """Build a short text summary of opportunity for the LLM."""
    parts = []
    name = (opp.get("event_name") or "").strip()
    if name:
        parts.append(f"Event: {name}")
    topics = opp.get("topics") or []
    if isinstance(topics, list):
        parts.append(f"Topics: {', '.join(str(t) for t in topics if t)}")
    fmt = (opp.get("speaking_format") or "").strip()
    if fmt:
        parts.append(f"Speaking format: {fmt}")
    delivery = (opp.get("delivery_mode") or "").strip()
    if delivery:
        parts.append(f"Delivery mode: {delivery}")
    audiences = opp.get("target_audiences") or []
    if isinstance(audiences, list):
        parts.append(f"Target audiences: {', '.join(str(a) for a in audiences if a)}")
    meta = opp.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("description"):
        parts.append(f"Description: {str(meta['description'])[:400]}")
    return "\n".join(parts) if parts else ""


class OpportunitySpeakerMatchAgent:
    """
    Agent that uses an LLM to decide if an opportunity is a good match for a speaker profile.
    Returns True only when the opportunity aligns with the speaker's topics, formats, delivery mode, and audiences.
    """

    SYSTEM_PROMPT = """You are an expert at matching speaking opportunities to speaker profiles.
Given a SPEAKER PROFILE and an OPPORTUNITY, decide if this opportunity is a good match for this speaker.

A good match means:
- The opportunity's topics overlap with the speaker's topics or expertise.
- The opportunity's speaking format (e.g. Keynote, Panel, Workshop) fits what the speaker offers.
- The opportunity's delivery mode (Virtual, In-person, Hybrid) matches the speaker's preference.
- The opportunity's target audience aligns with who the speaker wants to reach.

Reply with ONLY a JSON object with one key: "match" (boolean). Example: {"match": true} or {"match": false}.
Do not include any other text or explanation."""

    USER_PROMPT_TEMPLATE = """SPEAKER PROFILE:
{speaker_summary}

OPPORTUNITY:
{opportunity_summary}

Is this opportunity a good match for this speaker? Reply with JSON only: {{"match": true}} or {{"match": false}}."""

    def __init__(self, openai_client: OpenAI = None):
        self._client = openai_client

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpportunitySpeakerMatchAgent")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def is_match(self, speaker_profile: Dict[str, Any], opportunity: Dict[str, Any]) -> bool:
        """
        Return True if the opportunity is a good match for the speaker profile, False otherwise.
        Uses the LLM to compare profile and opportunity. On API/parse errors, returns False (exclude from match).
        """
        speaker_summary = _summary_profile(speaker_profile)
        opportunity_summary = _summary_opportunity(opportunity)
        if not speaker_summary or not opportunity_summary:
            return False
        try:
            client = self._get_client()
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": self.USER_PROMPT_TEMPLATE.format(
                            speaker_summary=speaker_summary,
                            opportunity_summary=opportunity_summary,
                        ),
                    },
                ],
                temperature=0.1,
            )
            text = (response.choices[0].message.content or "").strip()
            if not text:
                return False
            # Parse JSON (allow surrounding text)
            match = re.search(r"\{\s*\"match\"\s*:\s*(true|false)\s*\}", text, re.IGNORECASE)
            if match:
                obj = json.loads(match.group(0))
                return bool(obj.get("match", False))
            data = json.loads(text)
            return bool(data.get("match", False))
        except Exception as e:
            logger.warning("OpportunitySpeakerMatchAgent is_match failed: %s", e)
            return False
