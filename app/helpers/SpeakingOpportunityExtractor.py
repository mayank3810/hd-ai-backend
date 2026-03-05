"""
Uses an LLM to extract Speaking Opportunities from scraped website content.
Processes content in chunks with overlap to avoid hallucination and context loss at boundaries.
"""
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)


class SpeakingOpportunityExtractor:
    """Extracts speaking opportunities from markdown content via LLM."""

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
- topics: Array of relevant topics/themes (e.g. ["trading", "markets"]). NEVER leave empty - always infer at least one topic from the event name, description, type, or context (e.g. "networking", "conference theme", industry keywords)
- date: When the event is to happen (e.g. "2025-03-15", "March 2025"), null if not mentioned
- speaking_format: Type of event - e.g. "Workshop", "Panel discussion", "Conference", "Webinar". Use "Not available" if not determinable
- delivery_mode: "Virtual" or "In person" based on event format, empty string if not clear
- target_audiences: Array of audience types (e.g. ["General Audience", "Managers", "Traders"]), empty array if not found
- metadata: Object with any extra useful info (description, deadline, contact, etc.), empty object {} if none

Return ONLY valid JSON, no other text. Do not invent or hallucinate - only extract what is explicitly present.
If no opportunities are found in this chunk, return []."""

    USER_PROMPT_TEMPLATE = """Extract speaking opportunities from this chunk of website content (chunk {chunk_idx} of {total_chunks}):

---
{content}
---

Return a JSON array of opportunity objects with keys: link, event_name, location, topics, date, speaking_format, delivery_mode, target_audiences, metadata. topics must always have at least one item. If none found, return []."""

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
        """Ensure topics is never empty - infer from event_name or speaking_format if needed."""
        topics = opp.get("topics")
        if isinstance(topics, list) and len(topics) > 0:
            return [str(t).strip() for t in topics if t]
        event_name = (opp.get("event_name") or opp.get("title") or "").strip()
        speaking_format = (opp.get("speaking_format") or "").strip().lower()
        if speaking_format and speaking_format != "not available":
            return [opp.get("speaking_format", "").strip()]
        if event_name:
            words = [w for w in event_name.replace(",", " ").split() if len(w) > 2][:2]
            if words:
                return words
        return ["general"]

    def _normalize_opportunity(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LLM output to schema."""
        raw_topics = opp.get("topics") if isinstance(opp.get("topics"), list) else []
        topics = [str(t).strip() for t in raw_topics if t] if raw_topics else self._ensure_topics_non_empty(opp)
        return {
            "link": opp.get("link") or opp.get("url") or "",
            "event_name": opp.get("event_name") or opp.get("title") or "",
            "location": opp.get("location") or "",
            "topics": topics,
            "date": opp.get("date"),
            "speaking_format": opp.get("speaking_format") or "Not available",
            "delivery_mode": opp.get("delivery_mode") or "",
            "target_audiences": opp.get("target_audiences") if isinstance(opp.get("target_audiences"), list) else [],
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
