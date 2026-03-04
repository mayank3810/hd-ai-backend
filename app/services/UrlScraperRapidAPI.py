"""
Service for scraping URLs via RapidAPI and storing opportunities.
Flow: Save url+createdAt to UrlCollection -> background task scrapes -> extracts via LLM -> inserts opportunities into Opportunities collection.
No connection with existing Scraper/Scrapers collection.
"""
import logging
from datetime import datetime

from app.models.UrlCollection import UrlCollectionModel
from app.models.Opportunity import OpportunityModel
from app.helpers.RapidAPIScraper import scrape_url
from app.helpers.SpeakingOpportunityExtractor import extract_speaking_opportunities
from app.agents.EventDetailEnricherAgent import EventDetailEnricherAgent

logger = logging.getLogger(__name__)


class UrlScraperRapidAPIService:
    """
    Scrapes URLs via RapidAPI AI Content Scraper, extracts speaking opportunities via LLM,
    saves only url+createdAt to UrlCollection, and inserts each opportunity into Opportunities collection.
    """

    def __init__(self):
        self.url_collection_model = UrlCollectionModel()
        self.opportunity_model = OpportunityModel()
        self.enricher_agent = EventDetailEnricherAgent()

    async def create_url_scrape_job(self, url: str) -> str:
        """
        Save url and createdAt to UrlCollection, return the id.
        """
        doc = {
            "url": url,
            "createdAt": datetime.utcnow(),
        }
        inserted_id = await self.url_collection_model.create(doc)
        logger.info("UrlCollection created url_collection_id=%s url=%s", inserted_id, url[:80])
        return inserted_id

    async def get_url_collection_by_id(self, url_collection_id: str):
        """Get a UrlCollection entry by ID."""
        return await self.url_collection_model.get_by_id(url_collection_id)

    async def run_scrape_and_extract(self, url_collection_id: str, url: str) -> None:
        """
        Background task: scrape URL via RapidAPI, extract opportunities via LLM,
        insert each opportunity as root-level doc in Opportunities collection.
        """
        logger.info("Background job started url_collection_id=%s url=%s", url_collection_id, url[:80])
        try:
            # 1. Scrape via RapidAPI AI Content Scraper
            result = scrape_url(url)
            if not result.get("success"):
                logger.error("Job %s RapidAPI scrape failed: %s", url_collection_id, result.get("error"))
                return

            content = result.get("data", {}).get("content", "")
            if not content:
                logger.error("Job %s no content from scraper", url_collection_id)
                return

            logger.info("Job %s scrape complete, starting LLM extraction content_len=%d", url_collection_id, len(content))

            # 2. LLM extract speaking opportunities (new schema: link, event_name, etc.)
            opportunities, llm_error = extract_speaking_opportunities(content)
            if llm_error and not opportunities:
                logger.warning("Job %s LLM error: %s", url_collection_id, llm_error)

            if not opportunities:
                logger.info("Job %s completed with 0 opportunities", url_collection_id)
                return

            # 2b. Enrich opportunities with incomplete details (scrape each event link via RapidAPI, extract via LLM)
            opportunities = self.enricher_agent.enrich_opportunities(opportunities)

            # 3. Add source url to each opportunity's metadata for traceability
            for opp in opportunities:
                if "metadata" not in opp or not isinstance(opp["metadata"], dict):
                    opp["metadata"] = {}
                opp["metadata"]["sourceUrl"] = url
                opp["metadata"]["urlCollectionId"] = url_collection_id

            # 4. Insert each opportunity at root level in Opportunities collection
            inserted_ids = await self.opportunity_model.insert_many(opportunities)
            logger.info("Job %s completed: inserted %d opportunities into Opportunities collection", url_collection_id, len(inserted_ids))
        except Exception as e:
            logger.exception("Job %s failed: %s", url_collection_id, e)
