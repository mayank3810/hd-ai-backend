"""
Service for scraping URLs via RapidAPI and storing opportunities.
Flow: Save url+createdAt to UrlCollection -> background task scrapes -> updates sourceName/description -> extracts via LLM -> inserts opportunities into Opportunities collection.
No connection with existing Scraper/Scrapers collection.
Blocking I/O (RapidAPI requests, OpenAI) runs in a thread pool to avoid blocking the event loop.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from app.models.UrlCollection import UrlCollectionModel
from app.models.Opportunity import OpportunityModel
from app.helpers.RapidAPIScraper import RapidAPIScraper
from app.helpers.SpeakingOpportunityExtractor import SpeakingOpportunityExtractor
from app.agents.EventDetailEnricherAgent import EventDetailEnricherAgent

logger = logging.getLogger(__name__)

DESCRIPTION_MAX_LENGTH = 500


def _sync_scrape_extract_enrich(url: str) -> Optional[dict]:
    """
    Synchronous scrape + LLM extract + enrich. Runs in thread pool to avoid blocking event loop.
    Returns dict with keys: source_name, description, opportunities; or None on failure.
    """
    scraper = RapidAPIScraper()
    extractor = SpeakingOpportunityExtractor()
    enricher = EventDetailEnricherAgent()

    result = scraper.scrape(url)
    if not result.get("success"):
        return None
    content = result.get("data", {}).get("content", "")
    if not content:
        return None
    data = result.get("data", {})
    source_name = data.get("name") or ""
    if not source_name:
        parsed = urlparse(url)
        source_name = parsed.netloc or parsed.path or "unknown"
    description = data.get("description") or ""
    if len(description) > DESCRIPTION_MAX_LENGTH:
        description = description[:DESCRIPTION_MAX_LENGTH] + "..."

    opportunities, llm_error = extractor.extract(content)
    if llm_error and not opportunities:
        logger.warning("LLM extraction error: %s", llm_error)
    if opportunities:
        opportunities = enricher.enrich_opportunities(opportunities)

    return {"source_name": source_name, "description": description, "opportunities": opportunities or []}


class UrlScraperRapidAPIService:
    """
    Scrapes URLs via RapidAPI AI Content Scraper, extracts speaking opportunities via LLM,
    saves url+createdAt+sourceName+description to UrlCollection, inserts opportunities into Opportunities collection.
    """

    def __init__(self):
        self.url_collection_model = UrlCollectionModel()
        self.opportunity_model = OpportunityModel()
        self.enricher_agent = EventDetailEnricherAgent()

    async def create_url_scrape_job(self, url: str, user_id: str = None) -> str:
        """
        Save url and createdAt to UrlCollection. sourceName and description are updated after RapidAPI scrape.
        """
        doc = {
            "url": url,
            "createdAt": datetime.utcnow(),
        }
        if user_id:
            doc["userId"] = user_id
        inserted_id = await self.url_collection_model.create(doc)
        logger.info("UrlCollection created url_collection_id=%s url=%s", inserted_id, url[:80])
        return inserted_id

    async def get_url_collection_by_id(self, url_collection_id: str, user_id: str = None):
        """Get a UrlCollection entry by ID."""
        return await self.url_collection_model.get_by_id(url_collection_id, user_id)

    async def get_list(self, user_id: str, skip: int = 0, limit: int = 100) -> dict:
        """Get list of UrlCollection entries (for get-all-scrapers)."""
        items = await self.url_collection_model.get_list(user_id=user_id, skip=skip, limit=limit)
        total = await self.url_collection_model.count(user_id=user_id)
        return {"success": True, "data": {"scrapers": items, "total": total}}

    async def get_by_id(self, url_collection_id: str, user_id: str) -> dict:
        """Get a single UrlCollection by ID (for get-scraper)."""
        doc = await self.url_collection_model.get_by_id(url_collection_id, user_id)
        if not doc:
            return {"success": False, "data": None, "error": "Scraper not found"}
        return {"success": True, "data": doc}

    async def delete(self, url_collection_id: str, user_id: str) -> dict:
        """Delete a UrlCollection entry by ID (for delete-scraper)."""
        deleted = await self.url_collection_model.delete_by_id(url_collection_id, user_id)
        if not deleted:
            return {"success": False, "data": None, "error": "Scraper not found"}
        return {"success": True, "data": "Scraper deleted successfully"}

    async def run_scrape_and_extract(self, url_collection_id: str, url: str) -> None:
        """
        Background task: scrape URL via RapidAPI, extract opportunities via LLM,
        insert each opportunity as root-level doc in Opportunities collection.
        Blocking I/O runs in thread pool so it does not block other requests.
        """
        logger.info("Background job started url_collection_id=%s url=%s", url_collection_id, url[:80])
        try:
            # Run blocking work (RapidAPI, OpenAI, enricher) in thread pool - prevents blocking event loop
            parsed = await asyncio.to_thread(_sync_scrape_extract_enrich, url)
            if parsed is None:
                logger.error("Job %s scrape/extract failed", url_collection_id)
                return

            source_name = parsed["source_name"]
            description = parsed["description"]
            opportunities = parsed["opportunities"]

            # Async DB ops run in main event loop
            await self.url_collection_model.update_by_id(url_collection_id, {
                "sourceName": source_name,
                "description": description,
            })

            if not opportunities:
                logger.info("Job %s completed with 0 opportunities", url_collection_id)
                return

            for opp in opportunities:
                if "metadata" not in opp or not isinstance(opp["metadata"], dict):
                    opp["metadata"] = {}
                opp["metadata"]["sourceUrl"] = url
                opp["metadata"]["urlCollectionId"] = url_collection_id

            inserted_ids = await self.opportunity_model.insert_many(opportunities)
            logger.info("Job %s completed: inserted %d opportunities into Opportunities collection", url_collection_id, len(inserted_ids))
        except Exception as e:
            logger.exception("Job %s failed: %s", url_collection_id, e)
