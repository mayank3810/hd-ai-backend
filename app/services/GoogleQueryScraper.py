import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.helpers.SerpHelper import SerpHelper
from app.models.GoogleQuery import GoogleQueryModel
from app.services.UrlScraperRapidAPI import UrlScraperRapidAPIService, RAPIDAPI_DELAY_SECONDS

logger = logging.getLogger(__name__)

GOOGLE_QUERY_TOP_N = 5


class GoogleQueryScraperService:
    """
    Flow: Save query+createdAt+status=pending to GoogleQueries -> background task
    runs SERP -> takes top N URLs -> runs same RapidAPI+LLM extraction flow as UrlScraperRapidAPIService.
    """

    def __init__(self):
        self.google_query_model = GoogleQueryModel()
        self.url_scraper_service = UrlScraperRapidAPIService()

    async def create_google_query_job(self, query: str, user_id: Optional[str] = None) -> str:
        doc = {
            "query": query,
            "status": "pending",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "urls": [],
            "urlCollectionIds": [],
            "error": None,
        }
        if user_id:
            doc["userId"] = user_id
        inserted_id = await self.google_query_model.create(doc)
        logger.info("GoogleQuery created google_query_id=%s query=%s", inserted_id, query[:120])
        return inserted_id

    async def get_google_query_by_id(self, google_query_id: str, user_id: Optional[str] = None):
        return await self.google_query_model.get_by_id(google_query_id, user_id=user_id)

    async def run_query_serp_and_scrape(self, google_query_id: str, query: str, user_id: Optional[str] = None) -> None:
        logger.info("GoogleQuery background job started google_query_id=%s query=%s", google_query_id, query[:120])
        await self.google_query_model.update_by_id(
            google_query_id,
            {"status": "running", "updatedAt": datetime.utcnow(), "error": None},
        )
        try:
            urls = await asyncio.to_thread(SerpHelper().search, query)
            top_urls = (urls or [])[:GOOGLE_QUERY_TOP_N]
            await self.google_query_model.update_by_id(
                google_query_id,
                {"urls": top_urls, "updatedAt": datetime.utcnow()},
            )

            if not top_urls:
                await self.google_query_model.update_by_id(
                    google_query_id,
                    {"status": "completed", "updatedAt": datetime.utcnow()},
                )
                logger.info("GoogleQuery job completed (0 urls) google_query_id=%s", google_query_id)
                return

            url_collection_ids: list[str] = []
            for i, url in enumerate(top_urls):
                try:
                    if i > 0:
                        await asyncio.sleep(RAPIDAPI_DELAY_SECONDS)
                    url_collection_id = await self.url_scraper_service.create_url_scrape_job(url, user_id=user_id)
                    url_collection_ids.append(url_collection_id)
                    await self.google_query_model.update_by_id(
                        google_query_id,
                        {"urlCollectionIds": url_collection_ids, "updatedAt": datetime.utcnow()},
                    )
                    await self.url_scraper_service.run_scrape_and_extract(
                        url_collection_id,
                        url,
                        delay_seconds=RAPIDAPI_DELAY_SECONDS,
                    )
                except Exception as e:
                    logger.exception("GoogleQuery job url failed google_query_id=%s url=%s err=%s", google_query_id, url[:120], e)

            await self.google_query_model.update_by_id(
                google_query_id,
                {"status": "completed", "updatedAt": datetime.utcnow()},
            )
            logger.info("GoogleQuery job completed google_query_id=%s urls=%d", google_query_id, len(top_urls))
        except Exception as e:
            logger.exception("GoogleQuery job failed google_query_id=%s err=%s", google_query_id, e)
            await self.google_query_model.update_by_id(
                google_query_id,
                {"status": "failed", "error": str(e), "updatedAt": datetime.utcnow()},
            )

