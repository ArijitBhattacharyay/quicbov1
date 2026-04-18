import asyncio
from live_agent import ZeptoScraper, BigBasketScraper, InstamartScraper, _launch_browser, _get_page, startup, shutdown

async def main():
    await startup()
    page = _get_page("zepto")
    await page.goto("https://www.zepto.com/search?query=coffee", wait_until="networkidle", timeout=60000)
    print("ZEPTO HTML LIMIT:")
    print(await page.evaluate("document.body.innerHTML.substring(0, 500)"))
    cards = await page.locator("a[href^='/pn/']").count()
    print("ZEPTO cards href=/pn/:", cards)
    cards2 = await page.locator("[data-testid='product-card']").count()
    print("ZEPTO cards data-testid:", cards2)

    page2 = _get_page("bigbasket")
    await page2.goto("https://www.bigbasket.com/search/?nc=as&q=coffee", wait_until="networkidle", timeout=60000)
    cards = await page2.locator("div[class*='SKUDeck___StyledDiv']").count()
    print("BIGBASKET cards SKUDeck:", cards)

    page3 = _get_page("instamart")
    await page3.goto("https://www.swiggy.com/instamart/search?custom_back=true&query=coffee", wait_until="networkidle", timeout=60000)
    cards = await page3.locator("div[data-testid='item-card']").count()
    print("INSTAMART cards item-card:", cards)

    await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
