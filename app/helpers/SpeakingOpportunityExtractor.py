"""
Uses an LLM to extract Speaking Opportunities from scraped website content.
Processes content in chunks with overlap to avoid hallucination and context loss at boundaries.
"""
import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI


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

For each opportunity, extract:
- title: Clear name of the event/opportunity
- description: Brief description (1-2 sentences)
- eventType: e.g. "conference", "webinar", "podcast", "panel", "workshop"
- url: Source URL if mentioned, otherwise empty string
- deadline: Submission or registration deadline if mentioned, otherwise null
- contactInfo: Any contact or submission info if mentioned, otherwise null

Return a JSON array of objects with these keys. If no opportunities are found in this chunk, return [].
Return ONLY valid JSON, no other text. Do not invent or hallucinate opportunities - only extract what is explicitly present."""

USER_PROMPT_TEMPLATE = """Extract speaking opportunities from this chunk of website content (chunk {chunk_idx} of {total_chunks}):

---
{content}
---

Return a JSON array of opportunity objects. If none found, return []."""


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
    """Merge and deduplicate opportunities by (title_normalized, url)."""
    seen = set()
    result = []
    for opp in opportunities:
        title = (opp.get("title") or "").strip().lower()[:100]
        url = (opp.get("url") or "").strip()
        key = (title, url) if title or url else json.dumps(opp, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(opp)
    return result


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
    return _parse_llm_json_response(text) if text else []


def extract_speaking_opportunities(markdown_content: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Process content in overlapping chunks, extract opportunities from each,
    then merge and deduplicate. Reduces hallucination by keeping chunk sizes small.
    Returns (opportunities, error). error is set if OPENAI_API_KEY missing or LLM fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return [], "OPENAI_API_KEY not configured; opportunities could not be extracted"

    try:
        client = OpenAI(api_key=api_key)
        content = (markdown_content or "").strip()
        if not content:
            return [], None

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Split into overlapping chunks
        chunks = _chunk_with_overlap(content, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            return [], None

        all_opportunities: List[Dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            opps = _extract_from_chunk(client, chunk, i, len(chunks), model)
            all_opportunities.extend(opps)

        # Deduplicate (same opportunity may appear in overlapping chunks)
        merged = _deduplicate_opportunities(all_opportunities)
        return merged, None
    except Exception as e:
        print(f"[SpeakingOpportunityExtractor] Error: {e}")
        return [], str(e)
