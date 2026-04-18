"""
Parallel scraper manager.
Runs all platform scrapers simultaneously using asyncio.gather.
"""
import asyncio
from typing import Dict, List, Any

from scraper.blinkit import BlinkitScraper
from scraper.zepto import ZeptoScraper
from scraper.instamart import InstamartScraper
from scraper.bigbasket import BigBasketScraper


SCRAPERS = {
    "blinkit": BlinkitScraper,
    "zepto": ZeptoScraper,
    "instamart": InstamartScraper,
    "bigbasket": BigBasketScraper,
}


async def run_all_scrapers(query: str, pincode: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run all scrapers in parallel using asyncio.gather.
    Total time = slowest scraper, not sum of all scrapers.
    Returns: {"blinkit": [...], "zepto": [...], "instamart": [...], "bigbasket": [...]}
    """
    async def run_one(platform: str, scraper_cls):
        try:
            print(f"[{platform}] Starting scrape for '{query}' @ {pincode}...")
            scraper = scraper_cls()
            results = await scraper.search(query, pincode)
            print(f"[{platform}] Got {len(results)} results")
            return platform, results
        except Exception as e:
            print(f"[{platform}] Failed: {e}")
            return platform, []

    # Run all scrapers in parallel
    tasks = [
        run_one(platform, cls)
        for platform, cls in SCRAPERS.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    return {platform: data for platform, data in results}
