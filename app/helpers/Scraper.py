import requests
import json
import random
import os
from playwright.sync_api import sync_playwright
import html2text



class WebsiteScraper:
    def __init__(self):
        self.api_key =os.getenv("SPIDER_API_KEY")
        self.PLAYWRIGHT_WSS=os.getenv("PLAYWRIGHT_WSS")
        

    def _scrape_url_with_spider(self, url: str, limit: int = 1):
        if not url.startswith('https://'):
            url = f'https://{url.strip("/")}/'

        country_code = random.choice(['us', 'gb', 'ca', 'in'])

        payload = {
            "url": url,
            "limit": limit,
            "return_format": "raw",
            "anti_bot": True,
            "proxy_enabled": True,
            "proxy_mobile": False,
            "stealth": True,
            "respect_robots": True,
            "metadata": True,
            "country_code": country_code,
            "disable_intercept": False,
            "wait_for": {
                "dom": {
                    "timeout": {"secs": 5, "nanos": 500},
                    "selector": "body"
                },
                "delay": {
                    "timeout": {"secs": 5, "nanos": 500}
                }
            }
        }

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(
                'https://api.spider.cloud/crawl',
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }



    def _scrape_url_with_playwright(self, url: str):
        if not url.startswith('https://'):
            url = f'https://{url.strip("/")}/'

        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.PLAYWRIGHT_WSS)
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.new_page()

                # Block unnecessary resources
                def handle_route(route, request):
                    if request.resource_type in ["image", "media", "font"]:
                        route.abort()
                    else:
                        route.continue_()

                page.route("**/*", handle_route)

                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector("body", timeout=20000)
                html_content = page.content()

                browser.close()

                return {
                    "success": True,
                    "url": url,
                    "html": html_content
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }



    def _fetch_html(self, url: str) -> dict:
        # Try Spider first
        result = self._scrape_url_with_spider(url)
        if isinstance(result, list) and result and result[0].get("status") == 200 and result[0].get("content"):
            return {"html": result[0].get("content"), "status": "Success"}
        # If Spider fails, try Playwright
        result = self._scrape_url_with_playwright(url)
        if isinstance(result, dict) and result.get("success", True):
            return {"html": result.get("html", ""), "status": "Success"}
        return {"html": "", "status": f"Failed: {result.get('error', 'Unknown error')}"}
    
    def html_to_markdown(self,html_content: str) -> str:
        try:
            converter = html2text.HTML2Text()
            converter.ignore_links = False  # Keep links in the output
            converter.ignore_images = False  # Keep images in the output
            # converter.body_width = 0  # Preserve formatting
            markdown_content = converter.handle(html_content)
            return markdown_content
        except Exception as e:
            return ''
    
    def scrape_url(self,url:str):
        try:
            html_content = self._fetch_html(url)
            if html_content["status"] == "Success":
                markdown_content = self.html_to_markdown(html_content["html"])
                return {
                    "success": True,
                    "data": {
                        "markdown": markdown_content
                    }
                }
            else:
                return {
                    "success": False,
                    "error": html_content["status"]
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        