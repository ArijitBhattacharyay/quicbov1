"""
Base scraper class for all platform scrapers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BaseScraper(ABC):
    """Abstract base scraper. Each platform implements this."""
    
    platform_name: str = "base"
    base_url: str = ""

    def __init__(self):
        self.browser: Browser = None
        self.context: BrowserContext = None

    @abstractmethod
    async def search(self, query: str, pincode: str) -> List[Dict[str, Any]]:
        """
        Search for products and return list of dicts:
        [{"name": str, "price": float, "image": str, "delivery_time": int, 
          "url": str, "quantity": str, "original_price": float}, ...]
        """
        pass

    async def _make_browser(self, playwright) -> Browser:
        return await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

    async def _stealth_context(self, browser: Browser) -> BrowserContext:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        # Remove webdriver flag
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return context

    def _parse_price(self, price_str: str) -> float:
        """Parse price string like '₹77' or '77.00' to float."""
        if not price_str:
            return None
        cleaned = price_str.replace("₹", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_delivery(self, delivery_str: str) -> int:
        """Parse delivery string like '27 mins' to int minutes."""
        if not delivery_str:
            return None
        import re
        match = re.search(r'(\d+)', delivery_str)
        if match:
            return int(match.group(1))
        return None
