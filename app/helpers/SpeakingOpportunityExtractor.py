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


# Chunk config: smaller chunks + overlap reduce hallucination at boundaries
CHUNK_SIZE = int(os.getenv("LLM_CHUNK_SIZE", "6000"))  # chars per chunk
CHUNK_OVERLAP = int(os.getenv("LLM_CHUNK_OVERLAP", "1200"))  # overlapping chars (~20%)


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
- topics: Array of relevant topics/themes (e.g. ["trading", "markets"]), empty array if not found
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

Return a JSON array of opportunity objects with keys: link, event_name, location, topics, date, speaking_format, delivery_mode, target_audiences, metadata. If none found, return []."""


def _chunk_with_overlap(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into overlapping chunks to avoid losing context at boundaries.
    Overlap ensures opportunities spanning a split are fully present in at least one chunk.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        # Next chunk starts (chunk_size - overlap) chars ahead so we overlap
        start = end - overlap
        if start >= len(text):
            break
    return chunks


def _parse_llm_json_response(text: str) -> List[Dict[str, Any]]:
    """Parse JSON array from LLM response, handling markdown code blocks."""
    text = (text or "").strip()
    if not text:
        return []
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove ```json or ``` from first/last lines
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        # Try to find JSON array in response
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []


def _deduplicate_opportunities(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge and deduplicate opportunities by (event_name_normalized, link)."""
    seen = set()
    result = []
    for opp in opportunities:
        event_name = (opp.get("event_name") or opp.get("title") or "").strip().lower()[:100]
        link = (opp.get("link") or opp.get("url") or "").strip()
        key = (event_name, link) if event_name or link else json.dumps(opp, sort_keys=True)
        if key not in seen:
            seen.add(key)
            # Normalize to new schema (link, event_name, etc.)
            result.append(_normalize_opportunity(opp))
    return result


def _normalize_opportunity(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize LLM output to schema: link, event_name, location, topics, date, speaking_format, delivery_mode, target_audiences, metadata."""
    return {
        "link": opp.get("link") or opp.get("url") or "",
        "event_name": opp.get("event_name") or opp.get("title") or "",
        "location": opp.get("location") or "",
        "topics": opp.get("topics") if isinstance(opp.get("topics"), list) else [],
        "date": opp.get("date"),
        "speaking_format": opp.get("speaking_format") or "Not available",
        "delivery_mode": opp.get("delivery_mode") or "",
        "target_audiences": opp.get("target_audiences") if isinstance(opp.get("target_audiences"), list) else [],
        "metadata": opp.get("metadata") if isinstance(opp.get("metadata"), dict) else {},
    }


def _extract_from_chunk(
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
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    content=chunk, chunk_idx=chunk_idx + 1, total_chunks=total_chunks
                ),
            },
        ],
        temperature=0.2,
    )
    text = response.choices[0].message.content
    opps = _parse_llm_json_response(text) if text else []
    logger.debug("Chunk %d/%d yielded %d opportunities", chunk_idx + 1, total_chunks, len(opps))
    return opps


def extract_speaking_opportunities(markdown_content: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Process content in overlapping chunks, extract opportunities from each,
    then merge and deduplicate. Reduces hallucination by keeping chunk sizes small.
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
            logger.warning("Empty content passed to extract_speaking_opportunities")
            return [], None

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info("Starting LLM speaking opportunity extraction content_len=%d model=%s", len(content), model)

        # Split into overlapping chunks
        chunks = _chunk_with_overlap(content, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            logger.warning("No chunks produced from content")
            return [], None

        logger.info("Processing %d chunks for opportunity extraction", len(chunks))
        all_opportunities: List[Dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            opps = _extract_from_chunk(client, chunk, i, len(chunks), model)
            all_opportunities.extend(opps)

        # Deduplicate (same opportunity may appear in overlapping chunks)
        merged = _deduplicate_opportunities(all_opportunities)
        logger.info("LLM extraction complete: raw=%d after_dedup=%d", len(all_opportunities), len(merged))
        return merged, None
    except Exception as e:
        logger.exception("Speaking opportunity extraction failed: %s", e)
        return [], str(e)
