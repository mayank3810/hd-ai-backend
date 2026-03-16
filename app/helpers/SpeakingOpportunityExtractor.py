"""
Uses an LLM to extract Speaking Opportunities from scraped website content.
Processes content in chunks with overlap to avoid hallucination and context loss at boundaries.
Topics extracted by the LLM are constrained to the canonical list in speaker_profile_chatbot.TOPICS.
"""
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from app.config.speaker_profile_chatbot import (
    TOPICS as ALLOWED_TOPICS,
    SPEAKING_FORMATS,
    DELIVERY_MODE,
    TARGET_AUDIENCES,
)

logger = logging.getLogger(__name__)

_ALLOWED_TOPICS_SET = set(ALLOWED_TOPICS)
_ALLOWED_TOPICS_LOWER = {t.lower(): t for t in ALLOWED_TOPICS}
_TOPICS_LIST_STR = ", ".join(f'"{t}"' for t in ALLOWED_TOPICS)

_SPEAKING_FORMATS_SET = set(SPEAKING_FORMATS)
_SPEAKING_FORMATS_LOWER = {t.lower(): t for t in SPEAKING_FORMATS}
_SPEAKING_FORMATS_STR = ", ".join(f'"{t}"' for t in SPEAKING_FORMATS)

_DELIVERY_MODE_SET = set(DELIVERY_MODE)
_DELIVERY_MODE_LOWER = {t.lower(): t for t in DELIVERY_MODE}
_DELIVERY_MODE_STR = ", ".join(f'"{t}"' for t in DELIVERY_MODE)

_TARGET_AUDIENCES_SET = set(TARGET_AUDIENCES)
_TARGET_AUDIENCES_LOWER = {t.lower(): t for t in TARGET_AUDIENCES}
_TARGET_AUDIENCES_STR = ", ".join(f'"{t}"' for t in TARGET_AUDIENCES)


def _filter_single_to_allowed(value: str, allowed: List[str], allowed_lower: dict, default: str = "") -> str:
    """Map a single value to the allowed list (exact or case-insensitive). Returns default if no match."""
    s = (value or "").strip()
    if not s:
        return default
    if s in set(allowed):
        return s
    return allowed_lower.get(s.lower(), default)


def _filter_list_to_allowed(raw_list: List[str], allowed: List[str], allowed_set: set, allowed_lower: dict) -> List[str]:
    """Keep only values in allowed (exact or case-insensitive), deduplicated."""
    if not raw_list:
        return []
    seen = set()
    result = []
    for t in raw_list:
        s = (t or "").strip()
        if not s:
            continue
        if s in allowed_set and s not in seen:
            result.append(s)
            seen.add(s)
            continue
        canonical = allowed_lower.get(s.lower())
        if canonical and canonical not in seen:
            result.append(canonical)
            seen.add(canonical)
    return result


def _filter_topics_to_allowed(raw_topics: List[str]) -> List[str]:
    """Keep only topics that are in ALLOWED_TOPICS (exact or case-insensitive). If none match, return first allowed topic."""
    if not raw_topics:
        return [ALLOWED_TOPICS[0]] if ALLOWED_TOPICS else []
    seen = set()
    result = []
    for t in raw_topics:
        s = (t or "").strip()
        if not s:
            continue
        if s in _ALLOWED_TOPICS_SET and s not in seen:
            result.append(s)
            seen.add(s)
            continue
        canonical = _ALLOWED_TOPICS_LOWER.get(s.lower())
        if canonical and canonical not in seen:
            result.append(canonical)
            seen.add(canonical)
    if not result:
        result = [ALLOWED_TOPICS[0]] if ALLOWED_TOPICS else []
    return result


def _filter_speaking_format(raw: str) -> str:
    """Constrain to SPEAKING_FORMATS; if no match, return first allowed."""
    return _filter_single_to_allowed(
        raw, SPEAKING_FORMATS, _SPEAKING_FORMATS_LOWER,
        default=SPEAKING_FORMATS[0] if SPEAKING_FORMATS else "",
    )


def _filter_delivery_mode(raw: str) -> str:
    """Constrain to DELIVERY_MODE; if no match, return empty string."""
    return _filter_single_to_allowed(raw, DELIVERY_MODE, _DELIVERY_MODE_LOWER, default="")


def _filter_target_audiences_to_allowed(raw_list: List[str]) -> List[str]:
    """Constrain to TARGET_AUDIENCES only."""
    return _filter_list_to_allowed(
        raw_list or [], TARGET_AUDIENCES, _TARGET_AUDIENCES_SET, _TARGET_AUDIENCES_LOWER
    )


class SpeakingOpportunityExtractor:
    """Extracts speaking opportunities from markdown content via LLM. Topics are constrained to speaker_profile_chatbot.TOPICS."""

    SYSTEM_PROMPT = """You are an expert at identifying speaking opportunities for financial traders and trading professionals.
Given a CHUNK of website content (in markdown format), extract all potential speaking opportunities such as:
- Conferences and summits where traders might speak
- Webinars and virtual events
- Podcast or media interview opportunities
- Panel discussions or roundtables
- Workshops or training sessions where experts are invited to speak
- Industry events calling for speakers or submissions

For each opportunity, extract and return a JSON array of objects with EXACTLY these keys:
- link: Source URL if mentioned, otherwise empty string
- event_name: Clear name of the event/opportunity
- location: Event location (city, country, or "Virtual") if mentioned, otherwise empty string
- topics: Array of relevant topics. You MUST choose ONLY from this exact list (use the exact string): """ + _TOPICS_LIST_STR + """. Pick one or more that best match the event. NEVER leave empty - pick at least one from the list.
- date: When the event is to happen (e.g. "2025-03-15", "March 2025"), null if not mentioned
- speaking_format: You MUST choose exactly ONE from this list (use the exact string): """ + _SPEAKING_FORMATS_STR + """. Pick the one that best matches the event type.
- delivery_mode: You MUST choose exactly ONE from this list (use the exact string), or empty string if unclear: """ + _DELIVERY_MODE_STR + """
- target_audiences: Array of audience types. You MUST choose ONLY from this exact list (use the exact strings): """ + _TARGET_AUDIENCES_STR + """. Empty array if none match.
- metadata: Object with any extra useful info (description, deadline, contact, etc.), empty object {} if none

Return ONLY valid JSON, no other text. Do not invent or hallucinate - only extract what is explicitly present.
If no opportunities are found in this chunk, return []."""

    USER_PROMPT_TEMPLATE = """Extract speaking opportunities from this chunk of website content (chunk {chunk_idx} of {total_chunks}):

---
{content}
---

Return a JSON array of opportunity objects with keys: link, event_name, location, topics, date, speaking_format, delivery_mode, target_audiences, metadata. Use ONLY: topics from """ + _TOPICS_LIST_STR + """; speaking_format from """ + _SPEAKING_FORMATS_STR + """; delivery_mode from """ + _DELIVERY_MODE_STR + """; target_audiences from """ + _TARGET_AUDIENCES_STR + """. topics must have at least one item. If none found, return []."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or int(os.getenv("LLM_CHUNK_SIZE", "6000"))
        self.chunk_overlap = chunk_overlap or int(os.getenv("LLM_CHUNK_OVERLAP", "1200"))

    def _chunk_with_overlap(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks to avoid losing context at boundaries."""
        if not text or len(text) <= chunk_size:
            return [text] if text.strip() else []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            if start >= len(text):
                break
        return chunks

    def _parse_llm_json_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse JSON array from LLM response, handling markdown code blocks."""
        text = (text or "").strip()
        if not text:
            return []
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return []

    def _ensure_topics_non_empty(self, opp: Dict[str, Any]) -> list:
        """Ensure topics is never empty; result is filtered to ALLOWED_TOPICS only."""
        topics = opp.get("topics")
        if isinstance(topics, list) and len(topics) > 0:
            filtered = _filter_topics_to_allowed([str(t).strip() for t in topics if t])
            if filtered:
                return filtered
        event_name = (opp.get("event_name") or opp.get("title") or "").strip()
        speaking_format = (opp.get("speaking_format") or "").strip().lower()
        if speaking_format and speaking_format != "not available":
            return _filter_topics_to_allowed([opp.get("speaking_format", "").strip()])
        if event_name:
            words = [w for w in event_name.replace(",", " ").split() if len(w) > 2][:2]
            if words:
                return _filter_topics_to_allowed(words)
        return _filter_topics_to_allowed([])  # returns first allowed topic as fallback

    def _normalize_opportunity(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM output to schema; topics, speaking_format, delivery_mode, target_audiences constrained to speaker_profile_chatbot lists."""
        raw_topics = opp.get("topics") if isinstance(opp.get("topics"), list) else []
        topics = _filter_topics_to_allowed([str(t).strip() for t in raw_topics if t]) if raw_topics else self._ensure_topics_non_empty(opp)
        raw_speaking = (opp.get("speaking_format") or "").strip()
        raw_delivery = (opp.get("delivery_mode") or "").strip()
        raw_audiences = opp.get("target_audiences") if isinstance(opp.get("target_audiences"), list) else []
        return {
            "link": opp.get("link") or opp.get("url") or "",
            "event_name": opp.get("event_name") or opp.get("title") or "",
            "location": opp.get("location") or "",
            "topics": topics,
            "date": opp.get("date"),
            "speaking_format": _filter_speaking_format(raw_speaking),
            "delivery_mode": _filter_delivery_mode(raw_delivery),
            "target_audiences": _filter_target_audiences_to_allowed([str(a).strip() for a in raw_audiences if a]),
            "metadata": opp.get("metadata") if isinstance(opp.get("metadata"), dict) else {},
        }

    def _deduplicate_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge and deduplicate opportunities by (event_name_normalized, link)."""
        seen = set()
        result = []
        for opp in opportunities:
            event_name = (opp.get("event_name") or opp.get("title") or "").strip().lower()[:100]
            link = (opp.get("link") or opp.get("url") or "").strip()
            key = (event_name, link) if event_name or link else json.dumps(opp, sort_keys=True)
            if key not in seen:
                seen.add(key)
                result.append(self._normalize_opportunity(opp))
        return result

    def _extract_from_chunk(
        self,
        client: OpenAI,
        chunk: str,
        chunk_idx: int,
        total_chunks: int,
        model: str,
    ) -> List[Dict[str, Any]]:
        """Extract opportunities from a single chunk."""
        if not chunk.strip():
            return []
        logger.debug("LLM extracting from chunk %d/%d (len=%d)", chunk_idx + 1, total_chunks, len(chunk))
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": self.USER_PROMPT_TEMPLATE.format(
                        content=chunk, chunk_idx=chunk_idx + 1, total_chunks=total_chunks
                    ),
                },
            ],
            temperature=0.2,
        )
        text = response.choices[0].message.content
        opps = self._parse_llm_json_response(text) if text else []
        logger.debug("Chunk %d/%d yielded %d opportunities", chunk_idx + 1, total_chunks, len(opps))
        return opps

    def extract(self, markdown_content: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Process content in overlapping chunks, extract opportunities from each,
        then merge and deduplicate.
        Returns (opportunities, error). error is set if OPENAI_API_KEY missing or LLM fails.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not configured; opportunities could not be extracted")
            return [], "OPENAI_API_KEY not configured; opportunities could not be extracted"

        try:
            client = OpenAI(api_key=api_key)
            content = (markdown_content or "").strip()
            if not content:
                logger.warning("Empty content passed to extract")
                return [], None

            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            logger.info("Starting LLM speaking opportunity extraction content_len=%d model=%s", len(content), model)

            chunks = self._chunk_with_overlap(content, self.chunk_size, self.chunk_overlap)
            if not chunks:
                logger.warning("No chunks produced from content")
                return [], None

            logger.info("Processing %d chunks for opportunity extraction", len(chunks))
            all_opportunities: List[Dict[str, Any]] = []
            for i, chunk in enumerate(chunks):
                opps = self._extract_from_chunk(client, chunk, i, len(chunks), model)
                all_opportunities.extend(opps)

            merged = self._deduplicate_opportunities(all_opportunities)
            logger.info("LLM extraction complete: raw=%d after_dedup=%d", len(all_opportunities), len(merged))
            return merged, None
        except Exception as e:
            logger.exception("Speaking opportunity extraction failed: %s", e)
            return [], str(e)
