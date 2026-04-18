import asyncio
from playwright.async_api import async_playwright
from live_agent import ZeptoScraper, InstamartScraper

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        # Record video to current directory
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            record_video_dir="videos/"
        )
        # Suppress webdriver property to evade initial bot checks
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        page_zepto = await context.new_page()
        page_instamart = await context.new_page()

        print("[zepto] Starting Zepto Test")
        z_scraper = ZeptoScraper(page_zepto)
        try:
            await z_scraper.set_location("700063")
            res_z = await z_scraper.search("coffee")
            print(f"Zepto extracted {len(res_z)} products")
        except Exception as e:
            print(f"Zepto failed: {e}")

        print("[instamart] Starting Instamart Test")
        i_scraper = InstamartScraper(page_instamart)
        try:
            await i_scraper.set_location("700063")
            res_i = await i_scraper.search("coffee")
            print(f"Instamart extracted {len(res_i)} products")
        except Exception as e:
            print(f"Instamart failed: {e}")

        # Wait to let videos finish
        await asyncio.sleep(2)
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
