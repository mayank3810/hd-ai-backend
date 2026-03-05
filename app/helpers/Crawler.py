"""Crawler for extracting links from web pages."""
import asyncio
import os
from collections import deque
from typing import List, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.helpers.Scraper import WebsiteScraper


class Crawler:
    """Crawls websites to extract links within the same domain."""

    def __init__(self):
        self.scraper = WebsiteScraper()

    def is_same_domain(self, url: str, root_netloc: str) -> bool:
        """Check if URL belongs to the same domain as root."""
        return urlparse(url).netloc == root_netloc

    def extract_links_spider(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        for tag in soup.find_all("a", href=True):
            full_url = urljoin(base_url, tag["href"])
            links.add(full_url)
        return list(links)

    def try_spider(self, url: str) -> List[str] | None:
        """Try to extract links via spider. Returns None on failure."""
        try:
            result = self.scraper._scrape_url_with_spider(url, limit=1)
            if (
                isinstance(result, list)
                and result
                and result[0].get("status") == 200
                and result[0].get("content")
            ):
                html = result[0]["content"]
                return self.extract_links_spider(html, url)
        except Exception as e:
            print(f"[Spider Failed] {url} - {e}")
        return None

    async def _try_playwright_async(self, url: str, browser) -> List[str] | None:
        """Try to extract links via Playwright."""
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            links = await page.eval_on_selector_all("a[href]", "els => els.map(el => el.href)")
            await page.close()
            return links
        except Exception as e:
            print(f"[Playwright Failed] {url} - {e}")
            return None

    async def hybrid_crawl_async(self, root_url: str, max_depth: int, max_urls: int) -> List[str]:
        """Crawl using spider + Playwright fallback. Returns list of visited URLs."""
        visited: Set[str] = set()
        queue: deque[Tuple[str, int]] = deque([(root_url, 0)])
        root_netloc = urlparse(root_url).netloc
        print("Crawling Started for", root_url)

        loop = asyncio.get_running_loop()

        async with async_playwright() as playwright:
            browser = None
            wss_url = os.getenv("PLAYWRIGHT_WSS")

            if wss_url:
                retries = int(os.getenv("PLAYWRIGHT_WSS_RETRIES", "5"))
                timeout_ms = int(os.getenv("PLAYWRIGHT_WSS_TIMEOUT_MS", "60000"))
                for attempt in range(1, retries + 1):
                    try:
                        browser = await playwright.chromium.connect_over_cdp(
                            wss_url, timeout=timeout_ms
                        )
                        print("[Playwright WSS] Connected successfully.")
                        break
                    except Exception as e:
                        print(f"[Playwright WSS Connect Failed] attempt {attempt}/{retries}: {e}")
                        if attempt < retries:
                            backoff_seconds = min(5 * attempt, 20)
                            await asyncio.sleep(backoff_seconds)

            if browser is None and os.getenv("PLAYWRIGHT_LOCAL_FALLBACK", "false").lower() == "true":
                try:
                    browser = await playwright.chromium.launch(headless=True)
                    print("[Playwright Local Fallback] Launched local Chromium.")
                except Exception as e:
                    print(f"[Playwright Local Launch Failed] {e}")
                    return list(visited)

            while queue and len(visited) < max_urls:
                current_url, depth = queue.popleft()
                if current_url in visited or depth > max_depth:
                    continue

                links = await loop.run_in_executor(None, self.try_spider, current_url)
                if links is None and browser is not None:
                    links = await self._try_playwright_async(current_url, browser)
                if links is None:
                    continue

                visited.add(current_url)

                if depth < max_depth:
                    for link in links:
                        normalized = urljoin(current_url, link)
                        if (
                            self.is_same_domain(normalized, root_netloc)
                            and normalized not in visited
                            and len(visited) + len(queue) < max_urls
                        ):
                            queue.append((normalized, depth + 1))

            if browser:
                await browser.close()

        return list(visited)


async def hybrid_crawl_logic_async(root_url: str, max_depth: int, max_urls: int) -> List[str]:
    """Convenience function - creates Crawler and runs hybrid_crawl_async."""
    crawler = Crawler()
    return await crawler.hybrid_crawl_async(root_url, max_depth, max_urls)
