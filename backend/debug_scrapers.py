import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug_pages():
    urls = [
        ("Blinkit", "https://blinkit.com"),
        ("Zepto", "https://www.zepto.com"),
        ("BigBasket", "https://www.bigbasket.com"),
        ("Instamart", "https://www.swiggy.com/instamart")
    ]
    
    print("Starting deep debug of platforms via Headless Chrome with STEALTH...\n")
    
    async with async_playwright() as pw:
        # Pass standard arguments that help bypass basic bot checks
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        for name, url in urls:
            print(f"--- Testing {name} ({url}) ---")
            try:
                page = await ctx.new_page()
                # Apply stealth directly to the page!
                await Stealth().apply_stealth_async(page)
                
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(3000)  # Wait for JS
                
                title = await page.title()
                content_lower = (await page.content()).lower()
                text_content = await page.inner_text("body")
                
                print(f"  HTTP Status : {resp.status if resp else 'Unknown'}")
                print(f"  Page Title  : {title}")
                print(f"  Body length : {len(text_content)} characters")
                
                if any(k in content_lower for k in ["cloudflare", "captcha", "access denied", "please verify you are a human", "unusual traffic"]):
                    print("  [!] WARNING: Bot blocking or CAPTCHA detected in HTML!")
                else:
                    print("  [OK] No explicit CAPTCHA/Block keywords detected.")
                
            except Exception as e:
                print(f"  [!] Error: {e}")
            finally:
                await page.close()
            print()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_pages())
