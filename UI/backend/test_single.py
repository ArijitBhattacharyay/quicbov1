import asyncio
from live_agent import BigBasketScraper, _launch_browser, _get_page, startup, shutdown
import time

async def main():
    await startup()
    page = _get_page("bigbasket")
    sc = BigBasketScraper(page)
    await sc.set_location("110021")
    res = await sc.search("coffee")
    for r in res:
        print(r)
    await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
