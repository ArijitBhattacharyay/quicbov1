from playwright.sync_api import sync_playwright
import time

def debug_scrape(platform, pincode, product):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        print(f"Testing {platform}...")
        if platform == "blinkit":
            page.goto("https://blinkit.com", wait_until="domcontentloaded")
            time.sleep(3)
            page.screenshot(path="blinkit_start.png")
            # Try to set location
            try:
                page.locator("input[placeholder*='location']").first.type(pincode, delay=100)
                time.sleep(2)
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                time.sleep(3)
                page.screenshot(path="blinkit_location.png")
                # Search
                page.goto(f"https://blinkit.com/s/?q={product}")
                time.sleep(5)
                page.screenshot(path="blinkit_search.png")
                print(f"Blinkit Search inner text: {page.locator('body').inner_text()[:500]}")
            except Exception as e:
                print(f"Blinkit error: {e}")
        
        browser.close()

if __name__ == "__main__":
    debug_scrape("blinkit", "700063", "Amul Dahi")
