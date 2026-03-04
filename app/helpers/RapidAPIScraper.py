"""
Scrapes URL content using RapidAPI AI Content Scraper.
Returns markdown content suitable for LLM extraction.
"""
import os
import requests
from typing import Optional


RAPIDAPI_SCRAPE_URL = "https://ai-content-scraper.p.rapidapi.com/scrape"


def scrape_url(url: str) -> dict:
    """
    Scrape a URL via RapidAPI AI Content Scraper.
    Returns:
        success: bool
        data: { content: str, name?: str, description?: str, urls?: list } on success
        error: str on failure
    """
    api_key = os.getenv("RAPIDAPI_KEY", "")
    if not api_key:
        return {"success": False, "error": "RAPIDAPI_KEY not configured"}

    try:
        response = requests.post(
            RAPIDAPI_SCRAPE_URL,
            headers={
                "Content-Type": "application/json",
                "x-rapidapi-host": "ai-content-scraper.p.rapidapi.com",
                "x-rapidapi-key": api_key,
            },
            json={"url": url},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        content = data.get("content", "")
        if not content or not isinstance(content, str):
            return {"success": False, "error": "No content returned from scraper"}

        return {
            "success": True,
            "data": {
                "content": content,
                "name": data.get("name"),
                "description": data.get("description"),
                "urls": data.get("urls", []),
            },
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}
