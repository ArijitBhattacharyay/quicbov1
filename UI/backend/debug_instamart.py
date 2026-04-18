import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print("Visiting Instamart...")
        await page.goto("https://www.swiggy.com/instamart/search?custom_back=true&query=coffee")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="instamart_direct.png", full_page=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
