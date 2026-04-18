import asyncio
from live_agent import _pages, _browsers, startup, shutdown, PLATFORM_IDS

async def debug_screenshots():
    await startup()
    await asyncio.sleep(5)
    for pid in PLATFORM_IDS:
        page = _pages.get(pid)
        if page:
            print(f"Capturing {pid}...")
            await page.screenshot(path=f"{pid}_headless_debug.png", full_page=True)
    await shutdown()

if __name__ == "__main__":
    asyncio.run(debug_screenshots())
