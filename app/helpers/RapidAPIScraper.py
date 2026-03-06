"""
Scrapes URL content using RapidAPI AI Content Scraper.
Returns markdown content suitable for LLM extraction.
"""
import logging
import os
import time
import requests

logger = logging.getLogger(__name__)


class RapidAPIScraper:
    """Scrapes URLs via RapidAPI AI Content Scraper."""

    SCRAPE_URL = "https://ai-content-scraper.p.rapidapi.com/scrape"

    def __init__(self, delay_seconds: float = 0):
        """
        Args:
            delay_seconds: Optional delay before each RapidAPI request (e.g. 5 to avoid rate limits).
                           Default 0 - no delay, for normal API usage.
        """
        self.api_key = os.getenv("RAPIDAPI_KEY", "")
        self.delay_seconds = float(delay_seconds) if delay_seconds else 0

    def scrape(self, url: str) -> dict:
        """
        Scrape a URL via RapidAPI AI Content Scraper.
        Returns:
            success: bool
            data: { content: str, name?: str, description?: str, urls?: list } on success
            error: str on failure
        """
        logger.info("Starting RapidAPI scrape for url=%s", url[:80] + "..." if len(url) > 80 else url)
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        if not self.api_key:
            logger.error("RAPIDAPI_KEY not configured")
            return {"success": False, "error": "RAPIDAPI_KEY not configured"}

        try:
            response = requests.post(
                self.SCRAPE_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-rapidapi-host": "ai-content-scraper.p.rapidapi.com",
                    "x-rapidapi-key": self.api_key,
                },
                json={"url": url},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("content", "")
            if not content or not isinstance(content, str):
                logger.warning("No content returned from RapidAPI for url=%s", url[:80])
                return {"success": False, "error": "No content returned from scraper"}

            content_len = len(content) if content else 0
            logger.info("RapidAPI scrape success url=%s content_length=%d", url[:80], content_len)
            return {
                "success": True,
                "data": {
                    "content": content,
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "urls": data.get("urls", []),
                    "ogUrl": data.get("ogUrl"),
                },
            }
        except requests.exceptions.RequestException as e:
            logger.exception("RapidAPI request failed for url=%s: %s", url[:80], e)
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("RapidAPI scrape error for url=%s: %s", url[:80], e)
            return {"success": False, "error": str(e)}
