import asyncio
from live_agent import run_all_parallel, prewarm_location, startup, shutdown, _get_page
import time

async def main():
    await startup()
    await prewarm_location("110021")
    
    # Trigger searches
    pages = [_get_page("zepto"), _get_page("bigbasket"), _get_page("instamart")]
    
    await pages[0].goto("https://www.zepto.com/search?query=coffee", wait_until="domcontentloaded")
    await pages[1].goto("https://www.bigbasket.com/search/?nc=as&q=coffee", wait_until="domcontentloaded")
    await pages[2].goto("https://www.swiggy.com/instamart/search?custom_back=true&query=coffee", wait_until="domcontentloaded")
    
    await asyncio.sleep(4)
    
    await pages[0].screenshot(path="zepto_debug.png", full_page=True)
    await pages[1].screenshot(path="bigbasket_debug.png", full_page=True)
    await pages[2].screenshot(path="instamart_debug.png", full_page=True)

    await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
