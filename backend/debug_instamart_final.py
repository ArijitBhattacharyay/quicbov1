import asyncio
from playwright.async_api import async_playwright
from live_agent import InstamartScraper

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()

        sc = InstamartScraper(page)
        await sc.set_location("700063")
        
        # Manually run the search code up to the screenshot
        print("[instamart] search: coffee")
        
        # Step 1: Click fake search bar to open the overlay
        for trigger_sel in [
            "div[class*='sc-'][role='button'] span:has-text('Search')",
            "div[class*='Search']",
            "a[href*='/search']"
        ]:
            try:
                el = page.locator(trigger_sel).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    await page.wait_for_timeout(800)
                    break
            except Exception:
                pass
                
        typed = False
        for sel in [
            "input[placeholder*='Search']",
            "input[type='text']",
            "[data-testid='search-input']",
        ]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click(click_count=3)
                    await page.keyboard.press("Backspace")
                    await el.type("coffee", delay=50)
                    typed = True
                    break
            except Exception:
                pass

        if not typed:
            await page.goto(
                f"{sc.BASE_URL}/search?custom_back=true&query=coffee",
                wait_until="domcontentloaded", timeout=60000
            )
        else:
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1000)

        # WAIT FOR A MOMENT AND TAKE SCREENSHOT
        await page.wait_for_timeout(3000)
        await page.screenshot(path="instamart_final_debug.png", full_page=True)

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
