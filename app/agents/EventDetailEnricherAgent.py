"""
Agent that enriches opportunities with incomplete details by scraping event URLs
via RapidAPI and extracting missing fields (location, topics, date, speaking_format,
delivery_mode, target_audiences, metadata) using an LLM.
"""
import json
import os
import re
from typing import Dict, Any, Optional

from openai import OpenAI

from app.helpers.RapidAPIScraper import RapidAPIScraper


class EventDetailEnricherAgent:
    """
    Agent that enriches opportunities with incomplete details by scraping
    each event URL via RapidAPI and extracting missing fields via LLM.
    """

    ENRICHER_SYSTEM_PROMPT = """You are an expert at extracting event details from webpage content.
Given scraped content from an event page (markdown format), extract structured event information.

The content may include: event name, description, venue, location, date/time, topics, format, delivery mode, etc.

Extract and return a JSON object with EXACTLY these keys (no array, single object):
- event_name: Full name of the event (from page title/heading if not in content)
- location: City, country, or "Virtual" (e.g. "Leipzig, Germany", "New York, USA")
- topics: Array of relevant topics/themes (e.g. ["expat", "networking", "cultural exchange"]). NEVER leave empty - always infer at least one topic from the event name, description, or context
- date: When the event happens - prefer ISO date if clear (e.g. "2026-03-06"), or "Fri, Mar 6, 2026, 7:00 PM", or "March 2026"
- speaking_format: Type - "Workshop", "Panel discussion", "Meetup", "Conference", "Webinar", etc. Use "Not available" if unclear
- delivery_mode: "Virtual" or "In person" - infer from venue/description
- target_audiences: Array of audience types (e.g. ["Expats", "General Audience", "Professionals"])
- metadata: Object with description (1-2 sentences), venue name if mentioned, contact info if any, deadline if any. Use {} for empty.

Return ONLY valid JSON, no other text. Extract only what is explicitly present; use empty string, [], or null for missing fields. topics must always have at least one item related to the event."""

    ENRICHER_USER_PROMPT_TEMPLATE = """Extract event details from this scraped page content.

Page name/title from scraper: {name}

Description snippet: {description}

Full content:
---
{content}
---

Return a single JSON object with keys: event_name, location, topics, date, speaking_format, delivery_mode, target_audiences, metadata."""

    def __init__(self):
        self.rapidapi_scraper = RapidAPIScraper()

    def _is_opportunity_incomplete(self, opp: Dict[str, Any]) -> bool:
        """Return True if opportunity needs enrichment (missing key details)."""
        has_location = bool((opp.get("location") or "").strip())
        has_topics = bool(opp.get("topics") and len(opp.get("topics", [])) > 0)
        has_date = opp.get("date") is not None and str(opp.get("date")).strip() != ""
        has_speaking_format = bool((opp.get("speaking_format") or "").strip()) and (opp.get("speaking_format") or "").lower() != "not available"
        has_delivery_mode = bool((opp.get("delivery_mode") or "").strip())
        has_target_audiences = bool(opp.get("target_audiences") and len(opp.get("target_audiences", [])) > 0)
        missing = sum([
            not has_location,
            not has_topics,
            not has_date,
            not has_speaking_format,
            not has_delivery_mode,
            not has_target_audiences,
        ])
        return missing >= 2

    def _parse_llm_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON object from LLM response."""
        text = (text or "").strip()
        if not text:
            return None
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _ensure_topics_non_empty(self, opp: Dict[str, Any]) -> list:
        """Ensure topics is never empty - infer from event_name or speaking_format if needed."""
        topics = opp.get("topics")
        if isinstance(topics, list) and len(topics) > 0:
            return [str(t).strip() for t in topics if t]
        event_name = (opp.get("event_name") or "").strip()
        speaking_format = (opp.get("speaking_format") or "").strip().lower()
        if speaking_format and speaking_format != "not available":
            return [(opp.get("speaking_format") or "").strip()]
        if event_name:
            words = [w for w in event_name.replace(",", " ").split() if len(w) > 2][:2]
            if words:
                return words
        return ["general"]

    def _merge_enriched(self, original: Dict[str, Any], enriched: Dict[str, Any]) -> Dict[str, Any]:
        """Merge enriched fields into original, only filling in empty/missing values."""
        result = dict(original)
        result["link"] = original.get("link") or original.get("url") or ""

        def _fill(key: str, default_empty=None):
            if default_empty is None:
                default_empty = ""
            orig_val = result.get(key, default_empty)
            new_val = enriched.get(key)
            if orig_val is None or orig_val == "" or orig_val == [] or orig_val == {}:
                if new_val is not None:
                    result[key] = new_val
            elif key == "event_name" and not (orig_val and str(orig_val).strip()):
                if new_val:
                    result[key] = new_val

        _fill("event_name")
        _fill("location")
        _fill("topics", [])
        _fill("date")
        _fill("speaking_format")
        _fill("delivery_mode")
        _fill("target_audiences")
        if enriched.get("metadata") and isinstance(enriched["metadata"], dict):
            meta = result.get("metadata") or {}
            if not isinstance(meta, dict):
                meta = {}
            meta.update(enriched["metadata"])
            result["metadata"] = meta
        return result

    def _enrich_opportunity(self, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single opportunity by scraping its link and extracting via LLM."""
        link = (opp.get("link") or opp.get("url") or "").strip()
        if not link:
            return opp
        if not self._is_opportunity_incomplete(opp):
            return opp

        result = self.rapidapi_scraper.scrape(link)
        if not result.get("success"):
            return opp

        data = result.get("data", {})
        content = (data.get("content") or "").strip()
        name = data.get("name") or ""
        description = data.get("description") or ""
        og_url = data.get("ogUrl")

        if not content:
            return opp

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return opp

        try:
            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.ENRICHER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": self.ENRICHER_USER_PROMPT_TEMPLATE.format(
                            name=name or "(not provided)",
                            description=description or "(not provided)",
                            content=content[:8000],
                        ),
                    },
                ],
                temperature=0.1,
            )
            text = response.choices[0].message.content
            enriched_data = self._parse_llm_json_object(text) if text else None
            if not enriched_data:
                return opp

            merged = self._merge_enriched(opp, enriched_data)
            if not (merged.get("topics") and len(merged["topics"]) > 0):
                merged["topics"] = self._ensure_topics_non_empty(merged)
            if og_url:
                meta = merged.get("metadata")
                if not isinstance(meta, dict):
                    meta = {}
                meta["ogUrl"] = og_url
                merged["metadata"] = meta
            return merged
        except Exception:
            return opp

    def enrich_opportunities(self, opportunities: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """Enrich opportunities that have link but missing details."""
        enriched = []
        to_enrich = [o for o in opportunities if self._is_opportunity_incomplete(o) and (o.get("link") or o.get("url"))]
        if not to_enrich:
            return opportunities

        for opp in opportunities:
            if opp in to_enrich:
                enriched.append(self._enrich_opportunity(opp))
            else:
                enriched.append(opp)
        return enriched
