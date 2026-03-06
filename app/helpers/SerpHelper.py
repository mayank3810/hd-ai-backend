"""SERP Helper - Google search via BrightData API returning URLs only."""
import json
import os
from typing import List
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()


class SerpHelper:
    """Helper for Google search queries - returns organic result URLs."""

    def __init__(self):
        self.api_key = os.getenv("BRIGHTDATA_SERP_KEY")

    def search(self, query: str) -> List[str]:
        """
        Search Google via BrightData SERP API and return list of organic result URLs.

        Args:
            query: Search query string

        Returns:
            List of URL strings from organic search results

        Raises:
            ValueError: If BRIGHTDATA_SERP_KEY is not set
            RuntimeError: If BrightData API request fails
        """
        if not self.api_key:
            raise ValueError("Missing BRIGHTDATA_SERP_KEY in environment variables")

        qs = urlencode({"q": query})
        google_url = f"https://www.google.com/search?{qs}&brd_json=1"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "zone": "source_hr_serp",
            "url": google_url,
            "format": "json",
        }

        r = requests.post(
            "https://api.brightdata.com/request",
            headers=headers,
            json=payload,
        )

        if r.status_code != 200:
            raise RuntimeError(
                f"BrightData SERP API failed: {r.status_code}, {r.text}\n"
                f"Payload url={google_url}"
            )

        data = r.json()

        if "body" in data:
            try:
                result = json.loads(data["body"])
            except json.JSONDecodeError:
                raise ValueError("Failed to parse BrightData 'body' JSON")
        else:
            result = data

        organic = result.get("organic", [])
        urls: List[str] = []

        for item in organic:
            link = item.get("link") or item.get("url")
            if link:
                urls.append(link)

        return urls
