"""
Service for scraping URLs via RapidAPI and storing opportunities.
Flow: Save url+createdAt to UrlCollection -> background task scrapes -> updates sourceName/description -> extracts via LLM -> inserts opportunities into Opportunities collection.
No connection with existing Scraper/Scrapers collection.
Blocking I/O (RapidAPI requests, OpenAI) runs in a thread pool to avoid blocking the event loop.
PDF URLs are not scraped. Only opportunities with all required fields (link, event_name, location, topics, date, speaking_format, delivery_mode, target_audiences) are saved.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.models.UrlCollection import UrlCollectionModel
from app.models.Opportunity import OpportunityModel
from app.helpers.RapidAPIScraper import RapidAPIScraper
from app.helpers.SpeakingOpportunityExtractor import SpeakingOpportunityExtractor
from app.helpers.SerpHelper import SerpHelper
from app.agents.EventDetailEnricherAgent import EventDetailEnricherAgent

RAPIDAPI_DELAY_SECONDS = 5
TEDX_CRON_QUERY = "Ted X opportunities"
TEDX_CRON_TOP_N = 5

logger = logging.getLogger(__name__)

DESCRIPTION_MAX_LENGTH = 500
# UrlCollection requires a non-empty description; use this when scrape returns none
DESCRIPTION_FALLBACK = "Scraped page"


def is_pdf_url(url: str) -> bool:
    """True if URL path ends with .pdf (case-insensitive), ignoring query/fragment."""
    if not url or not isinstance(url, str):
        return False
    path = (urlparse(url.strip()).path or "").rstrip("/")
    return path.lower().endswith(".pdf")


def filter_complete_opportunities(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep only opportunities that have all required fields filled (link, event_name, location,
    topics, date, speaking_format, delivery_mode, target_audiences). If LLM couldn't find any,
    the opportunity is not added to the collection.
    """
    result = []
    for opp in opportunities:
        link = (opp.get("link") or opp.get("url") or "").strip()
        event_name = (opp.get("event_name") or opp.get("title") or "").strip()
        location = (opp.get("location") or "").strip()
        topics = opp.get("topics")
        date_val = opp.get("date")
        speaking_format = (opp.get("speaking_format") or "").strip()
        delivery_mode = (opp.get("delivery_mode") or "").strip()
        target_audiences = opp.get("target_audiences")

        if not link or not event_name or not location:
            continue
        if not isinstance(topics, list) or len(topics) == 0:
            continue
        if date_val is None or not str(date_val).strip():
            continue
        if not speaking_format or not delivery_mode:
            continue
        if not isinstance(target_audiences, list):
            continue
        result.append(opp)
    return result


def _sync_scrape_extract_enrich(url: str, delay_seconds: float = 0) -> Optional[dict]:
    """
    Synchronous scrape + LLM extract + enrich. Runs in thread pool to avoid blocking event loop.
    Returns dict with keys: source_name, description, opportunities; or None on failure.
    Does not scrape URLs that end with .pdf.

    Args:
        url: URL to scrape
        delay_seconds: Optional delay before each RapidAPI call (e.g. 5 to avoid rate limits). Default 0.
    """
    if is_pdf_url(url):
        return None
    scraper = RapidAPIScraper(delay_seconds=delay_seconds)
    extractor = SpeakingOpportunityExtractor()
    enricher = EventDetailEnricherAgent(rapidapi_scraper=scraper)

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
    description = (data.get("description") or "").strip()
    if not description:
        description = source_name or DESCRIPTION_FALLBACK
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

    async def create_url_scrape_job(self, url: str, user_id: str = None, topics: Optional[list] = None) -> str:
        """
        Save url and createdAt to UrlCollection. sourceName and description are updated after RapidAPI scrape.
        topics is optional; when provided, stored on the document for reference (allowed values from speaker_profile_chatbot.TOPICS).
        Raises ValueError if url ends with .pdf (PDFs are not scraped).
        """
        if is_pdf_url(url):
            raise ValueError("PDF URLs are not scraped")
        doc = {
            "url": url,
            "status": "pending",
            "createdAt": datetime.utcnow(),
        }
        if user_id:
            doc["userId"] = user_id
        if topics is not None and len(topics) > 0:
            doc["topics"] = topics
        inserted_id = await self.url_collection_model.create(doc)
        logger.info("UrlCollection created url_collection_id=%s url=%s", inserted_id, url[:80])
        return inserted_id

    async def get_url_collection_by_id(self, url_collection_id: str, user_id: str = None):
        """Get a UrlCollection entry by ID."""
        return await self.url_collection_model.get_by_id(url_collection_id, user_id)

    async def get_list(self, skip: int = 0, limit: int = 100) -> dict:
        """Get list of UrlCollection entries (for get-all-scrapers). No user filter."""
        items = await self.url_collection_model.get_list(user_id=None, skip=skip, limit=limit)
        total = await self.url_collection_model.count(user_id=None)
        return {"success": True, "data": {"scrapers": items, "total": total}}

    async def get_by_id(self, url_collection_id: str, user_id: str) -> dict:
        """Get a single UrlCollection by ID (for get-scraper)."""
        doc = await self.url_collection_model.get_by_id(url_collection_id, user_id)
        if not doc:
            return {"success": False, "data": None, "error": "Scraper not found"}
        return {"success": True, "data": doc}

    async def delete(self, url_collection_id: str) -> dict:
        """Delete a UrlCollection entry by ID (for delete-scraper). Deletion is by scraper_id only."""
        deleted = await self.url_collection_model.delete_by_id(url_collection_id, user_id=None)
        if not deleted:
            return {"success": False, "data": None, "error": "Scraper not found"}
        return {"success": True, "data": "Scraper deleted successfully"}

    async def run_scrape_and_extract(
        self, url_collection_id: str, url: str, delay_seconds: float = 0
    ) -> None:
        """
        Background task: scrape URL via RapidAPI, extract opportunities via LLM,
        insert each opportunity as root-level doc in Opportunities collection.
        Blocking I/O runs in thread pool so it does not block other requests.

        Args:
            url_collection_id: UrlCollection document ID
            url: URL to scrape
            delay_seconds: Optional delay before each RapidAPI call (e.g. 5 for cron). Default 0.
        """
        logger.info("Background job started url_collection_id=%s url=%s", url_collection_id, url[:80])
        try:
            if is_pdf_url(url):
                logger.info("Skipping PDF URL url_collection_id=%s", url_collection_id)
                await self.url_collection_model.update_by_id(url_collection_id, {"status": "failed"})
                return
            # Run blocking work (RapidAPI, OpenAI, enricher) in thread pool - prevents blocking event loop
            parsed = await asyncio.to_thread(_sync_scrape_extract_enrich, url, delay_seconds)
            if parsed is None:
                logger.error("Job %s scrape/extract failed", url_collection_id)
                await self.url_collection_model.update_by_id(url_collection_id, {"status": "failed"})
                return

            source_name = parsed["source_name"]
            description = parsed["description"]
            opportunities = parsed["opportunities"]

            complete = filter_complete_opportunities(opportunities)
            dropped = len(opportunities) - len(complete)
            if dropped:
                logger.info("Job %s: dropped %d opportunities missing required fields (link, event_name, location, topics, date, speaking_format, delivery_mode, target_audiences)", url_collection_id, dropped)

            # Unique topics from saved opportunities, for UrlCollection
            extracted_topics = sorted(
                set(
                    str(t).strip()
                    for opp in complete
                    for t in (opp.get("topics") or [])
                    if t and str(t).strip()
                )
            )

            # Description is compulsory for UrlCollection; use fallback if empty
            description_for_db = (description or "").strip() or DESCRIPTION_FALLBACK

            # Async DB ops: update UrlCollection with sourceName, description, status, and extracted topics
            await self.url_collection_model.update_by_id(url_collection_id, {
                "sourceName": source_name,
                "description": description_for_db,
                "status": "completed",
                "topics": extracted_topics,
            })

            if not opportunities:
                logger.info("Job %s completed with 0 opportunities", url_collection_id)
                return

            for opp in complete:
                if "metadata" not in opp or not isinstance(opp["metadata"], dict):
                    opp["metadata"] = {}
                opp["metadata"]["sourceUrl"] = url
                opp["metadata"]["urlCollectionId"] = url_collection_id

            if complete:
                inserted_ids = await self.opportunity_model.insert_many(complete)
                logger.info("Job %s completed: inserted %d opportunities into Opportunities collection", url_collection_id, len(inserted_ids))
            else:
                logger.info("Job %s completed with 0 opportunities to insert (all incomplete)", url_collection_id)
        except Exception as e:
            logger.exception("Job %s failed: %s", url_collection_id, e)
            await self.url_collection_model.update_by_id(url_collection_id, {"status": "failed"})

    async def _run_tedx_cron_async(self) -> None:
        """
        Cron job: Search Google for Ted X opportunities, take top 5 URLs,
        and run the same scrape+extract+enrich flow as the API (with 5s delay between RapidAPI calls).
        No user_id - runs as system job.
        """
        logger.info("TedX cron job started")
        try:
            serp = SerpHelper()
            urls = serp.search(TEDX_CRON_QUERY)
            non_pdf = [u for u in (urls or []) if not is_pdf_url(u)]
            top_urls = non_pdf[:TEDX_CRON_TOP_N]
            if not top_urls:
                logger.warning("TedX cron: no URLs from SERP for query=%s", TEDX_CRON_QUERY)
                return

            logger.info("TedX cron: processing %d URLs with %ds delay between RapidAPI calls and between URLs", len(top_urls), RAPIDAPI_DELAY_SECONDS)
            for i, url in enumerate(top_urls):
                try:
                    if i > 0:
                        await asyncio.sleep(RAPIDAPI_DELAY_SECONDS)  # 5s between URLs
                    url_collection_id = await self.create_url_scrape_job(url, user_id=None)
                    await self.run_scrape_and_extract(url_collection_id, url, delay_seconds=RAPIDAPI_DELAY_SECONDS)
                except Exception as e:
                    logger.exception("TedX cron: failed for url=%s: %s", url[:80], e)
            logger.info("TedX cron job completed")
        except Exception as e:
            logger.exception("TedX cron job failed: %s", e)

    def run_tedx_daily_cron(self) -> None:
        """
        Synchronous entrypoint for APScheduler.
        Runs TedX cron in a new event loop (scheduler runs in background thread).
        """
        asyncio.run(self._run_tedx_cron_async())
