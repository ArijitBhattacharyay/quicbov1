"""
live_agent.py — Persistent-browser scraper for Quicbo
======================================================
Architecture:
  • A single Playwright instance is started once when the FastAPI server boots.
  • Each platform gets ONE browser context that stays alive across requests.
  • When the user confirms a pincode (/api/prewarm), we set location on all
    4 browsers IN PARALLEL — no browser teardown, no re-launch.
  • Subsequent search calls skip set_location entirely → ~20-25 s instead of ~90 s.

Pattern follows grocery_agent.py (sync reference), translated to async Playwright.
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Page, async_playwright, Browser, BrowserContext, Playwright


# ── Data models ────────────────────────────────────────────────────────────────
@dataclass
class ProductResult:
    name: str
    weight: str
    price: float
    original_price: str
    discount: str
    delivery_time: int
    available: bool = True
    platform: str = ""
    image: str = ""


@dataclass
class TestReport:
    platform: str
    pincode: str
    location: str
    delivery_time: str
    product_query: str
    products: list[ProductResult] = field(default_factory=list)
    error: Optional[str] = None


# ── Global persistent state ─────────────────────────────────────────────────────
_playwright: Optional[Playwright] = None
_browsers: dict[str, Browser] = {}
_contexts: dict[str, BrowserContext] = {}
_pages: dict[str, Page] = {}
_warmed_pincode: Optional[str] = None   # last pincode location was set for
_ready = False


PLATFORM_IDS = ["blinkit", "zepto", "bigbasket", "instamart"]

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]


async def startup():
    """Call once at FastAPI startup — launches 4 persistent browser instances."""
    global _playwright, _ready
    print("[live_agent] Starting persistent browsers …")
    _playwright = await async_playwright().start()
    for pid in PLATFORM_IDS:
        await _launch_browser(pid)
    _ready = True
    print("[live_agent] All browsers ready ✓")


async def shutdown():
    """Call at FastAPI shutdown — closes all browsers cleanly."""
    global _playwright, _ready
    _ready = False
    for pid in PLATFORM_IDS:
        try:
            if pid in _browsers:
                await _browsers[pid].close()
        except Exception as e:
            print(f"[live_agent] shutdown {pid}: {e}")
    if _playwright:
        await _playwright.stop()
    print("[live_agent] Browsers closed.")


async def _launch_browser(pid: str):
    """Launch (or re-launch after crash) one browser for a platform."""
    try:
        if pid in _browsers:
            try:
                await _browsers[pid].close()
            except Exception:
                pass
        browser = await _playwright.chromium.launch(
            headless=False,  # keeps cookies / sessions; set True for prod
            args=LAUNCH_ARGS,
            slow_mo=0,
        )
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=UA,
        )
        page = await ctx.new_page()
        # Inject basic stealth JS (replaces playwright-stealth which is broken)
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        _browsers[pid] = browser
        _contexts[pid] = ctx
        _pages[pid] = page
        print(f"[live_agent] Browser ready: {pid}")
    except Exception as e:
        print(f"[live_agent] _launch_browser {pid} ERROR: {e}")


def _get_page(pid: str) -> Optional[Page]:
    return _pages.get(pid)


# ── Shared helper functions (mirrors grocery_agent.py) ─────────────────────────
_REVIEW_PATTERN = re.compile(r'^\(\d+[\d.,]*[kKmM]?\)$')
_UI_WORDS = {"ADD", "REMOVE", "BUY", "LOGIN", "CART", "SEARCH",
             "CLOSE", "CANCEL", "OK", "DONE", "SELECT", "CONFIRM"}


def _is_garbage(text: str) -> bool:
    t = text.strip()
    if not t or len(t) < 2:
        return True
    if "₹" in t:
        return True
    if _REVIEW_PATTERN.match(t):
        return True
    if re.match(r'^\d+[\d.,]*[kKmM]?$', t):
        return True
    if t.upper() in _UI_WORDS:
        return True
    if re.match(r'^[\d.]+ \(', t):
        return True
    return False


def _parse_price(s: str) -> float:
    try:
        return float(re.sub(r'[^\d.]', '', s))
    except Exception:
        return 0.0


async def _wait_for_input(page: Page, placeholders: list[str],
                          max_wait_ms: int = 8000) -> Optional[object]:
    step = 300
    elapsed = 0
    while elapsed < max_wait_ms:
        for ph in placeholders:
            try:
                el = page.locator(f"input[placeholder='{ph}']")
                if await el.count() > 0 and await el.first.is_visible():
                    return el.first
            except Exception:
                pass
        for partial in ["delivery location", "new address", "pincode", "area"]:
            try:
                el = page.locator(f"input[placeholder*='{partial}']")
                if await el.count() > 0 and await el.first.is_visible():
                    return el.first
            except Exception:
                pass
        await page.wait_for_timeout(step)
        elapsed += step
    return None


async def _js_open_location_modal(page: Page) -> str:
    result = await page.evaluate("""
        () => {
            function tryClick(selectors) {
                for (let sel of selectors) {
                    try {
                        let el = document.querySelector(sel);
                        if (el && el.offsetParent !== null) { el.click(); return sel; }
                    } catch(e) {}
                }
                return null;
            }
            let r = tryClick([
                "[data-testid='location-btn']",
                "button[aria-label*='location']",
                "button[aria-label*='Location']",
                "button[aria-label*='Layout']",
                "button[aria-label*='Nagar']",
                "button[aria-label*='Road']",
            ]);
            if (r) return r;
            let header = document.querySelector('header');
            if (!header) return 'no-header';
            let keywords = ['deliver', 'location', 'area', 'pincode', 'select', 'address', 'nagar', 'layout'];
            let walker = document.createTreeWalker(header, NodeFilter.SHOW_ELEMENT);
            let node;
            while ((node = walker.nextNode())) {
                let txt = (node.innerText || '').toLowerCase().trim();
                let tag = node.tagName.toLowerCase();
                if (['button','div','span','a','p'].includes(tag)
                        && node.children.length <= 5
                        && txt.length > 0 && txt.length < 80
                        && keywords.some(k => txt.includes(k))) {
                    node.click();
                    return 'header-text:' + txt.slice(0, 40);
                }
            }
            let first = header.querySelector('button, a, [role="button"]');
            if (first) { first.click(); return 'header-first'; }
            header.click();
            return 'header-raw';
        }
    """)
    return str(result)


async def _fill_and_trigger(page: Page, el, text: str, delay: int = 60) -> None:
    """Clear existing content and type new text — mirrors grocery_agent.py exactly."""
    try:
        await el.click(click_count=3)
        await page.wait_for_timeout(150)
        await page.keyboard.press("Control+a")
        await page.wait_for_timeout(50)
        await page.keyboard.press("Delete")
        await page.wait_for_timeout(50)
        await el.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input',{bubbles:true})); }")
        await page.wait_for_timeout(100)
        await el.type(text, delay=delay)
        await el.evaluate("""
            el => {
                el.dispatchEvent(new Event('input',  {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
            }
        """)
    except Exception as ex:
        print(f"[fill_and_trigger] {ex}")

async def _text_fallback(page: Page, platform: str) -> list[ProductResult]:
    """Last-resort text scanner when DOM selectors fail entirely."""
    print(f"[{platform}] using text fallback extractor")
    try:
        body = await page.inner_text("body", timeout=4000)
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        results = []
        i = 0
        while i < len(lines) - 1 and len(results) < 20:
            line = lines[i]
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            nxt2 = lines[i + 2] if i + 2 < len(lines) else ""
            
            if not _is_garbage(line) and len(line) > 3 and "₹" not in line and "min" not in line.lower() and "km" not in line.lower() and "location" not in line.lower():
                price_cand = next((x for x in [nxt, nxt2] if "₹" in x), None)
                if price_cand:
                    price_val = _parse_price(price_cand)
                    if price_val > 0:
                        results.append(ProductResult(
                            name=line, weight="—", price=price_val,
                            original_price="", discount="", delivery_time=25,
                            available=True, platform=platform, image=""
                        ))
                    i += 2
                    continue
            i += 1
        print(f"[{platform}] fallback extracted {len(results)} products")
        return results
    except Exception as e:
        print(f"[{platform}] text fallback error: {e}")
        return []


async def _pick_first_suggestion(page: Page, match_text: str = None) -> bool:
    """Wait for dropdown and click first valid item — mirrors grocery_agent.py."""
    try:
        await page.wait_for_timeout(3000)
        if match_text:
            locs = page.locator(f"text={match_text}")
            count = await locs.count()
            for i in range(count):
                el = locs.nth(i)
                if await el.is_visible():
                    tag = await el.evaluate("e => e.tagName.toLowerCase()")
                    if tag != "input":
                        await el.click()
                        print(f"[suggestion] picked via text match: {match_text}")
                        return True

        for sel in [
            "[role='dialog'] li",
            "[class*='SuggestionItem']",
            "[class*='LocationSearchList'] > div",
            "[data-testid='place-item']",
            "[role='option']",
            ".pac-item",
        ]:
            locs = page.locator(sel)
            count = await locs.count()
            if count > 0:
                for i in range(count):
                    item = locs.nth(i)
                    if await item.is_visible():
                        text = (await item.inner_text()).lower()
                        if "current location" in text or "detect" in text or "gps" in text:
                            continue
                        await item.click()
                        return True

        await page.keyboard.press("ArrowDown")
        await page.wait_for_timeout(300)
        await page.keyboard.press("Enter")
        return False
    except Exception as ex:
        print(f"[pick_suggestion] {ex}")
        return False


async def _read_delivery_time(page: Page) -> int:
    """Extract delivery time in minutes from page."""
    try:
        time_el = page.locator("text=/\\d+\\s*min/i").first
        if await time_el.is_visible(timeout=1000):
            txt = await time_el.inner_text()
            m = re.search(r'(\d+)', txt)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return 20


# ── Per-platform scrapers (stateless — use passed-in page) ─────────────────────

class BlinkitScraper:
    BASE_URL = "https://blinkit.com"

    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> None:
        print(f"[blinkit] set_location {pincode}")
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(1000)

        INPUT_PLACEHOLDERS = ["search delivery location", "Search delivery location"]
        loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=2000)

        if loc_input is None:
            await _js_open_location_modal(self.page)
            await self.page.wait_for_timeout(500)
            loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=2000)

        if loc_input:
            await _fill_and_trigger(self.page, loc_input, pincode)
        else:
            await self.page.keyboard.type(pincode, delay=30)

        await self.page.wait_for_timeout(1000)
        await _pick_first_suggestion(self.page, match_text=pincode)

        try:
            await self.page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            await self.page.wait_for_timeout(3000)

        await self.page.wait_for_timeout(2000)
        print(f"[blinkit] location set ✓")

    async def search(self, product: str) -> list[ProductResult]:
        print(f"[blinkit] search: {product}")
        # Try clicking the search anchor
        try:
            await self.page.locator("a[href='/s/']").first.click()
            await self.page.wait_for_timeout(600)
        except Exception:
            pass

        typed = False
        for sel in [
            "input[placeholder='Search for atta dal and more']",
            "input[placeholder*='atta dal']",
            "input[placeholder*='Search for']",
            "input[placeholder*='Search']",
            "input[type='search']",
        ]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click(click_count=3)
                    await self.page.keyboard.press("Backspace")
                    await self.page.wait_for_timeout(200)
                    await el.type(product, delay=50)
                    typed = True
                    break
            except Exception:
                pass

        if not typed:
            await self.page.goto(
                f"{self.BASE_URL}/s/?q={product.replace(' ', '%20')}",
                wait_until="domcontentloaded", timeout=60000
            )
        else:
            await self.page.keyboard.press("Enter")

        try:
            await self.page.locator("[data-testid='product-card']").first.wait_for(state="visible", timeout=4000)
        except Exception:
            pass

        for _ in range(2):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(150)

        return await self._extract()

    async def _extract(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in [
            "[data-testid='product-card']",
            "div[role='button'][id]",
            "div[class*='tw-flex'][role='button']",
        ]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found
                    break
            except Exception:
                pass

        if not cards:
            cards = self.page.locator("[data-testid='product-card'], div.tw-flex.tw-flex-col, a[href^='/pr/']")
        
        if not cards or await cards.count() == 0:
            return await _text_fallback(self.page, "blinkit")

        delivery_mins = await _read_delivery_time(self.page)
        count = await cards.count()

        for i in range(min(count, 20)):
            try:
                card = cards.nth(i)
                full_text = (await card.inner_text(timeout=3500)).strip()
                if not full_text:
                    continue
                lines = [l.strip() for l in full_text.split("\n") if l.strip()]

                name = "—"
                for sel in ["div.tw-line-clamp-2", "[class*='line-clamp']"]:
                    try:
                        t = (await card.locator(sel).first.inner_text(timeout=400)).strip()
                        if t and not _is_garbage(t):
                            name = t
                            break
                    except Exception:
                        pass
                if name == "—":
                    for line in lines:
                        if not _is_garbage(line):
                            name = line
                            break

                weight = "—"
                unit_tokens = [" g", "kg", " ml", " l ", " ltr", " pc", " pack", " gm"]
                for line in lines:
                    if (any(u in line.lower() for u in unit_tokens)
                            and "₹" not in line and len(line) <= 35
                            and line.strip() != name.strip()):
                        weight = line
                        break

                price_lines = [l for l in lines if l.startswith("₹") or ("₹" in l and len(l) < 15)]
                price_str = price_lines[0] if price_lines else "0"
                parsed_price = _parse_price(price_str)
                orig_price = price_lines[1] if len(price_lines) > 1 else ""
                discount = next((l for l in lines if "%" in l and "off" in l.lower()), "")
                available = "out of stock" not in full_text.lower() and "notify" not in full_text.lower()

                image_url = ""
                try:
                    img = card.locator("img").first
                    if await img.is_visible(timeout=400):
                        image_url = await img.get_attribute("src") or ""
                except Exception:
                    pass

                if name != "—" and parsed_price > 0:
                    products.append(ProductResult(
                        name=name, weight=weight, price=parsed_price,
                        original_price=orig_price, discount=discount,
                        delivery_time=delivery_mins, available=available,
                        platform="blinkit", image=image_url,
                    ))
            except Exception as ex:
                print(f"[blinkit] card {i} skip: {ex}")

        print(f"[blinkit] extracted {len(products)} products")
        return products


class ZeptoScraper:
    BASE_URL = "https://www.zepto.com"

    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> None:
        print(f"[zepto] set_location {pincode}")
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(1000)

        INPUT_PLACEHOLDERS = ["Search a new address", "Search a new"]
        loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=1000)

        if loc_input is None:
            await _js_open_location_modal(self.page)
            await self.page.wait_for_timeout(800)
            loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=2000)

        if loc_input:
            await _fill_and_trigger(self.page, loc_input, pincode)
        else:
            await self.page.keyboard.type(pincode, delay=30)

        await self.page.wait_for_timeout(1000)
        await _pick_first_suggestion(self.page, match_text=pincode)

        try:
            await self.page.wait_for_load_state("networkidle", timeout=4000)
        except Exception:
            await self.page.wait_for_timeout(1000)

        for sel in ["text=Confirm", "text=Proceed", "text=Done",
                    "button[class*='confirm']", "button[class*='proceed']"]:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible(timeout=500):
                    await btn.click()
                    await self.page.wait_for_timeout(300)
                    break
            except Exception:
                pass

        await self.page.wait_for_timeout(500)
        print(f"[zepto] location set ✓")

    async def search(self, product: str) -> list[ProductResult]:
        print(f"[zepto] search: {product}")
        
        # Step 1: Click the fake search bar to open actual search route
        for trigger_sel in [
            "a[href*='/search']",
            "div[class*='Search']",
            "[data-testid='search-container']"
        ]:
            try:
                el = self.page.locator(trigger_sel).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    await self.page.wait_for_timeout(800)
                    break
            except Exception:
                pass

        typed = False
        for sel in [
            "input[placeholder*='Search']",
            "input[type='search']",
            "[data-testid='search-input']",
        ]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click(click_count=3)
                    await self.page.keyboard.press("Backspace")
                    await el.type(product, delay=50)
                    typed = True
                    break
            except Exception:
                pass

        if not typed:
            # Fallback URL
            search_url = f"{self.BASE_URL}/search?query={product.replace(' ', '+')}"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        else:
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(1000)
        
        try:
            await self.page.locator("a[href^='/pn/'], [data-testid='product-card']").first.wait_for(state="visible", timeout=4000)
        except Exception:
            pass

        for _ in range(2):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(150)

        return await self._extract()

    async def _extract(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["a[href^='/pn/']", "[data-testid='product-card']"]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found
                    break
            except Exception:
                pass

        if not cards:
            cards = self.page.locator("[data-testid='product-card'], a[data-testid='product-card'], a[href^='/pn/']")
        
        if not cards or await cards.count() == 0:
            return await _text_fallback(self.page, "zepto")

        global_delivery = await _read_delivery_time(self.page)
        count = await cards.count()

        for i in range(min(count, 20)):
            try:
                card = cards.nth(i)
                full_text = (await card.inner_text(timeout=3500)).strip()
                if not full_text:
                    continue
                lines = [l.strip() for l in full_text.split("\n") if l.strip()]

                price_lines = [l for l in lines if l.startswith("₹")]
                discount_lines = [l for l in lines if ("off" in l.lower() or "OFF" in l) and not l.startswith("₹")]
                rating_lines = [l for l in lines if re.match(r'^[\d.]+ \(', l)]
                skip = set(price_lines) | set(discount_lines) | set(rating_lines) | {"ADD"}
                content_lines = [l for l in lines if l not in skip and not _is_garbage(l)]

                name = content_lines[0] if content_lines else "—"
                weight = content_lines[1] if len(content_lines) > 1 else "—"
                # Validate weight looks like a weight
                unit_tokens = [" g", "kg", " ml", " l", " ltr", " pc", " pack", " gm"]
                if not any(u in weight.lower() for u in unit_tokens):
                    weight = "—"
                    for l in lines:
                        if any(u in l.lower() for u in unit_tokens) and l not in skip and len(l) <= 35:
                            weight = l
                            break

                price_str = price_lines[0] if price_lines else "0"
                parsed_price = _parse_price(price_str)
                orig_price = price_lines[1] if len(price_lines) > 1 else ""
                discount = discount_lines[0] if discount_lines else ""
                available = "out of stock" not in full_text.lower() and "notify" not in full_text.lower()

                image_url = ""
                try:
                    img = card.locator("img").first
                    if await img.is_visible(timeout=400):
                        image_url = await img.get_attribute("src") or ""
                except Exception:
                    pass

                if name != "—" and parsed_price > 0:
                    products.append(ProductResult(
                        name=name, weight=weight, price=parsed_price,
                        original_price=orig_price, discount=discount,
                        delivery_time=global_delivery, available=available,
                        platform="zepto", image=image_url,
                    ))
            except Exception as ex:
                print(f"[zepto] card {i} skip: {ex}")

        print(f"[zepto] extracted {len(products)} products")
        return products


class BigBasketScraper:
    BASE_URL = "https://www.bigbasket.com"

    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> None:
        print(f"[bigbasket] set_location {pincode}")
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(1000)

        for sel in [
            "button[class*='Location']",
            "div[class*='AddressSelect']",
            "span[class*='Address']",
            "text=Select Location",
            "text=Deliver to",
        ]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=800):
                    await el.click()
                    break
            except Exception:
                pass

        await self.page.wait_for_timeout(500)
        loc_input = await _wait_for_input(
            self.page, ["Search location", "Enter your city", "Enter pincode"], max_wait_ms=1500
        )
        if loc_input:
            await _fill_and_trigger(self.page, loc_input, pincode)
        else:
            await self.page.keyboard.type(pincode, delay=30)

        await self.page.wait_for_timeout(1000)
        await _pick_first_suggestion(self.page, match_text=pincode)
        await self.page.wait_for_timeout(2500)
        print(f"[bigbasket] location set ✓")

    async def search(self, product: str) -> list[ProductResult]:
        print(f"[bigbasket] search: {product}")
        typed = False
        for sel in [
            "input[placeholder*='Search']",
            "input[type='text'][id='input']",
            "input[qa='searchBar']",
        ]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click(click_count=3)
                    await self.page.keyboard.press("Backspace")
                    await el.type(product, delay=50)
                    typed = True
                    break
            except Exception:
                pass

        if not typed:
            await self.page.goto(
                f"{self.BASE_URL}/search/?nc=as&q={product.replace(' ', '+')}",
                wait_until="domcontentloaded", timeout=60000
            )
        else:
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(1000)

        try:
            await self.page.locator("div[class*='SKUDeck___StyledDiv'], a[href^='/pd/']").first.wait_for(state="visible", timeout=4000)
        except Exception:
            pass

        for _ in range(2):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(150)

        return await self._extract()

    async def _extract(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in [
            "div[class*='SKUDeck___StyledDiv']",
            "a[href^='/pd/']",
            "li[class*='PaginateItems']",
        ]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found
                    break
            except Exception:
                pass

        if not cards or await cards.count() == 0:
            cards = self.page.locator("li[class*='PaginateItems'], a[href^='/pd/']")
            
        if not cards or await cards.count() == 0:
            return await _text_fallback(self.page, "bigbasket")

        count = await cards.count()
        for i in range(min(count, 15)):
            try:
                card = cards.nth(i)
                text = (await card.inner_text(timeout=3500)).strip()
                if not text:
                    continue
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                name = lines[1] if len(lines) > 1 else lines[0]
                weight = "—"
                unit_tokens = [" g", "kg", " ml", " l ", " ltr", " pc", " pack"]
                for l in lines:
                    if any(u in l.lower() for u in unit_tokens) and "₹" not in l and len(l) <= 35:
                        weight = l
                        break

                price_lines = [l for l in lines if l.startswith("₹")]
                parsed_price = _parse_price(price_lines[0]) if price_lines else 0.0
                orig_price = price_lines[1] if len(price_lines) > 1 else ""
                discount = next((l for l in lines if "%" in l and "off" in l.lower()), "")
                available = "out of stock" not in text.lower() and "notify" not in text.lower()

                image_url = ""
                try:
                    img = card.locator("img").first
                    if await img.is_visible(timeout=400):
                        image_url = await img.get_attribute("src") or ""
                except Exception:
                    pass

                if name and parsed_price > 0:
                    products.append(ProductResult(
                        name=name, weight=weight, price=parsed_price,
                        original_price=orig_price, discount=discount,
                        delivery_time=25, available=available,
                        platform="bigbasket", image=image_url,
                    ))
            except Exception as ex:
                print(f"[bigbasket] card {i} skip: {ex}")

        print(f"[bigbasket] extracted {len(products)} products")
        return products


class InstamartScraper:
    BASE_URL = "https://www.swiggy.com/instamart"

    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> None:
        print(f"[instamart] set_location {pincode}")
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(1000)

        # Look for location button on Instamart
        loc_button = None
        for sel in [
            "div[class*='Address']",
            "span[class*='Address']",
            "text=Select Location",
            "[data-testid='location-btn']",
            "div[class*='location']"
        ]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=800):
                    await el.click()
                    await self.page.wait_for_timeout(500)
                    break
            except Exception:
                pass

        loc_input = self.page.locator("input[id='location']")
        if await loc_input.is_visible(timeout=1000):
            await _fill_and_trigger(self.page, loc_input, pincode)
            await self.page.wait_for_timeout(1000)
            await _pick_first_suggestion(self.page, match_text=pincode)
            
            # Handle Confirm Location button if present
            try:
                btn = self.page.locator("text=Confirm Location").first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    await self.page.wait_for_timeout(500)
            except Exception:
                pass
                
            # Handle Swiggy "Something went wrong! Try Again" overlay
            try:
                retry = self.page.locator("text=Try Again").first
                if await retry.is_visible(timeout=1000):
                    await retry.click()
                    await self.page.wait_for_timeout(500)
            except Exception:
                pass
                
            # Swiggy has a known bug where confirming location shows a honey-jar error
            # but the cookie sets successfully. A fast reload fixes the DOM.
            print("[instamart] reloading to bypass honey-jar error state")
            await self.page.reload(wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(2500)
        else:
            # Try generic approach
            loc_input2 = await _wait_for_input(
                self.page, ["Enter your delivery location", "Search for area"], max_wait_ms=1500
            )
            if loc_input2:
                await _fill_and_trigger(self.page, loc_input2, pincode)
                await self.page.wait_for_timeout(1000)
                await _pick_first_suggestion(self.page, match_text=pincode)
                
            print("[instamart] reloading to bypass honey-jar error state")
            await self.page.reload(wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(2500)

        print(f"[instamart] location set ✓")

    async def search(self, product: str) -> list[ProductResult]:
        print(f"[instamart] search: {product}")
        
        # Ensure we are not on an error page. If we are, try going back to home.
        if "Something went wrong" in await self.page.content():
            await self.page.goto(self.BASE_URL, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(3000)

        # Step 1: Click fake search bar to open the overlay
        for trigger_sel in [
            "text=Search for",
            "div[class*='Search']",
            "a[href*='/search']"
        ]:
            try:
                el = self.page.locator(trigger_sel).first
                if await el.is_visible(timeout=3000):
                    await el.click(force=True)
                    await self.page.wait_for_timeout(1500)
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
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=3000):
                    await el.click(click_count=3)
                    await self.page.keyboard.press("Backspace")
                    await self.page.wait_for_timeout(200)
                    await el.type(product, delay=50)
                    typed = True
                    break
            except Exception:
                pass

        if not typed:
            print("[instamart] Using direct URL fallback for search")
            search_url = f"{self.BASE_URL}/search?q={product.replace(' ', '%20')}"
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        else:
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(2000)

        try:
            await self.page.locator("div[data-testid='item-card'], div[class*='ItemCard']").first.wait_for(state="visible", timeout=4000)
        except Exception:
            pass

        for _ in range(2):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(150)

        return await self._extract()

    async def _extract(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in [
            "div[data-testid='item-card']",
            "div[class*='ItemCard']",
            "div[class*='ProductList'] > div",
        ]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found
                    break
            except Exception:
                pass

        if not cards or await cards.count() == 0:
            cards = self.page.locator("div[data-testid='normal-item-container'], div[class*='ItemCard']")
            
        if not cards or await cards.count() == 0:
            return await _text_fallback(self.page, "instamart")

        count = await cards.count()
        for i in range(min(count, 15)):
            try:
                card = cards.nth(i)
                text = (await card.inner_text(timeout=3500)).strip()
                if not text:
                    continue
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                name = lines[0]
                weight = lines[1] if len(lines) > 1 else "—"
                price_lines = [l for l in lines if l.startswith("₹")]
                parsed_price = _parse_price(price_lines[0]) if price_lines else 0.0
                orig_price = price_lines[1] if len(price_lines) > 1 else ""
                discount = next((l for l in lines if "%" in l and "off" in l.lower()), "")
                available = "out of stock" not in text.lower()

                image_url = ""
                try:
                    img = card.locator("img").first
                    if await img.is_visible(timeout=400):
                        image_url = await img.get_attribute("src") or ""
                except Exception:
                    pass

                if name and parsed_price > 0:
                    products.append(ProductResult(
                        name=name, weight=weight, price=parsed_price,
                        original_price=orig_price, discount=discount,
                        delivery_time=18, available=available,
                        platform="instamart", image=image_url,
                    ))
            except Exception as ex:
                print(f"[instamart] card {i} skip: {ex}")

        print(f"[instamart] extracted {len(products)} products")
        return products


# ── Public API ──────────────────────────────────────────────────────────────────

SCRAPERS = {
    "blinkit":   BlinkitScraper,
    "zepto":     ZeptoScraper,
    "bigbasket": BigBasketScraper,
    "instamart": InstamartScraper,
}


async def prewarm_location(pincode: str) -> dict:
    """
    Set location on ALL 4 platforms in parallel using persistent browser pages.
    Called by /api/prewarm when user confirms pincode in UI.
    Returns status for each platform.
    """
    global _warmed_pincode
    global _prewarm_task

    if not _ready:
        return {"error": "browsers not ready"}

    if _prewarm_task is not None and not _prewarm_task.done():
        print(f"[prewarm] Awaiting previous prewarm task to finish before starting new PIN {pincode}...")
        try:
            await _prewarm_task
        except Exception:
            pass

    async def _do_prewarm():
        global _warmed_pincode
        async def _set_one(pid: str):
            page = _get_page(pid)
            if page is None:
                return pid, "no_page"
            try:
                scraper = SCRAPERS[pid](page)
                await scraper.set_location(pincode)
                return pid, "ok"
            except Exception as e:
                print(f"[prewarm] {pid} error: {e}")
                # Try re-launching the browser if it crashed
                try:
                    await _launch_browser(pid)
                    page2 = _get_page(pid)
                    scraper2 = SCRAPERS[pid](page2)
                    await scraper2.set_location(pincode)
                    return pid, "ok_after_relaunch"
                except Exception as e2:
                    return pid, f"error: {e2}"

        _warmed_pincode = pincode
        tasks = [_set_one(pid) for pid in PLATFORM_IDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # _warmed_pincode = pincode  # Moved to start of prewarm to prevent race conditions

        status = {}
        for r in results:
            if isinstance(r, Exception):
                status["unknown"] = str(r)
            else:
                pid, st = r
                status[pid] = st

        print(f"[prewarm] done for {pincode}: {status}")
        return status
        
    # Execute and store the task globally so other functions can await it
    _prewarm_task = asyncio.create_task(_do_prewarm())
    return await _prewarm_task
    
# Global tracker to ensure searches don't clash with ongoing prewarms
_prewarm_task = None



async def run_all_parallel(pincode: str, product: str) -> list[TestReport]:
    """
    Search all 4 platforms in parallel.
    If the pincode matches the warmed pincode, SKIP set_location (fast path).
    Otherwise fall back to setting location + searching sequentially per platform.
    """
    if not _ready:
        print("[live_agent] browsers not ready, falling back to empty")
        return []

    global _prewarm_task
    
    if _prewarm_task is not None:
        try:
            print("[live_agent] Awaiting ongoing prewarm task before parsing search...")
            await _prewarm_task
        except Exception as e:
            print(f"[live_agent] Ongoing prewarm ignored due to exception: {e}")

    skip_location = (_warmed_pincode == pincode)
    if not skip_location:
        print(f"[live_agent] pincode mismatch ({_warmed_pincode!r} != {pincode!r}) — setting location inline")

    async def _run_one(pid: str) -> TestReport:
        report = TestReport(
            platform=pid, pincode=pincode,
            location="—", delivery_time="—", product_query=product
        )
        page = _get_page(pid)
        if page is None:
            report.error = "browser not available"
            return report
        try:
            scraper = SCRAPERS[pid](page)
            if not skip_location:
                await scraper.set_location(pincode)
            report.products = await scraper.search(product)
        except Exception as e:
            print(f"[live_agent] {pid} search error: {e}")
            report.error = str(e)
            # Attempt to recover the browser
            try:
                await _launch_browser(pid)
                page2 = _get_page(pid)
                scraper2 = SCRAPERS[pid](page2)
                await scraper2.set_location(pincode)
                report.products = await scraper2.search(product)
                report.error = None
            except Exception as e2:
                report.error = f"recovery failed: {e2}"
        return report

    tasks = [_run_one(pid) for pid in PLATFORM_IDS]
    return list(await asyncio.gather(*tasks, return_exceptions=False))
