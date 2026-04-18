import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def log_resp(response):
            if "search" in response.url.lower():
                print(f"URL: {response.url} Status: {response.status}")
                if response.status == 200:
                    try:
                        data = await response.json()
                        keys = list(data.keys())
                        print(f"Keys in JSON: {keys}")
                        # Check first few items if exists
                        for k in ["products", "items", "data"]:
                            if k in data and data[k]:
                                print(f"Found '{k}' with {len(data[k])} items. First item: {list(data[k][0].keys())}")
                    except: print("Could not parse JSON")

        page.on("response", log_resp)
        await page.goto("https://www.zepto.com")
        # Just type 110001 (not perfectly setting location, but might trigger search page load)
        await page.wait_for_timeout(2000)
        await page.goto("https://www.zepto.com/search?query=Milk")
        await page.wait_for_timeout(5000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
