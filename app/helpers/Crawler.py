from typing import List, Set, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import deque
import os
import asyncio
from app.helpers.Scraper import WebsiteScraper
from playwright.async_api import async_playwright


def is_same_domain(url: str, root_netloc: str) -> bool:
    return urlparse(url).netloc == root_netloc


def extract_links_spider(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for tag in soup.find_all("a", href=True):
        full_url = urljoin(base_url, tag["href"])
        links.add(full_url)
    return list(links)


def try_spider(url: str) -> List[str] | None:
    try:
        scraper = WebsiteScraper()
        result = scraper._scrape_url_with_spider(url, limit=1)
        if (
            isinstance(result, list)
            and result
            and result[0].get("status") == 200
            and result[0].get("content")
        ):
            html = result[0]["content"]
            return extract_links_spider(html, url)
    except Exception as e:
        print(f"[Spider Failed] {url} - {e}")
    return None


async def try_playwright_async(url: str, browser) -> List[str] | None:
    try:
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        links = await page.eval_on_selector_all(
            "a[href]", "els => els.map(el => el.href)"
        )
        await page.close()
        return links
    except Exception as e:
        print(f"[Playwright Failed] {url} - {e}")
        return None


async def hybrid_crawl_logic_async(root_url: str, max_depth: int, max_urls: int) -> List[str]:
    visited: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque([(root_url, 0)])
    root_netloc = urlparse(root_url).netloc
    print("Crawling Started for",root_url )

    loop = asyncio.get_running_loop()

    async with async_playwright() as playwright:
        browser = None
        wss_url = os.getenv("PLAYWRIGHT_WSS")

        # Try WSS connection first
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

        # Local fallback if WSS fails
        if browser is None and os.getenv("PLAYWRIGHT_LOCAL_FALLBACK", "false").lower() == "true":
            try:
                browser = await playwright.chromium.launch(headless=True)
                print("[Playwright Local Fallback] Launched local Chromium.")
            except Exception as e:
                print(f"[Playwright Local Launch Failed] {e}")
                return list(visited)  # No browser, stop crawling

        # Start crawling
        while queue and len(visited) < max_urls:
            current_url, depth = queue.popleft()
            if current_url in visited or depth > max_depth:
                continue

            # Try spider (blocking) in threadpool
            links = await loop.run_in_executor(None, try_spider, current_url)

            # If spider fails, try Playwright
            if links is None and browser is not None:
                links = await try_playwright_async(current_url, browser)

            if links is None:
                continue

            visited.add(current_url)

            if depth < max_depth:
                for link in links:
                    normalized = urljoin(current_url, link)
                    if (
                        is_same_domain(normalized, root_netloc)
                        and normalized not in visited
                        and len(visited) + len(queue) < max_urls
                    ):
                        queue.append((normalized, depth + 1))

        # Close browser
        if browser:
            await browser.close()

    return list(visited)


