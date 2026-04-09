import argparse
import asyncio
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Page, async_playwright
from playwright_stealth import Stealth

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


# Matches review counts like "(5.1k)", "(308)"
_REVIEW_PATTERN = re.compile(r'^\(\d+[\d.,]*[kKmM]?\)$')
_UI_WORDS = {"ADD", "REMOVE", "BUY", "LOGIN", "CART", "SEARCH",
             "CLOSE", "CANCEL", "OK", "DONE", "SELECT", "CONFIRM"}

def _is_garbage(text: str) -> bool:
    t = text.strip()
    if not t or len(t) < 2: return True
    if "₹" in t: return True
    if _REVIEW_PATTERN.match(t): return True
    if re.match(r'^\d+[\d.,]*[kKmM]?$', t): return True
    if t.upper() in _UI_WORDS: return True
    if re.match(r'^[\d.]+ \(', t): return True
    return False

def _parse_price(price_str: str) -> float:
    try:
        return float(re.sub(r'[^\d.]', '', price_str))
    except:
        return 0.0

async def _wait_for_input(page: Page, placeholders: list[str], max_wait_ms: int = 8000) -> Optional[object]:
    step = 300
    elapsed = 0
    while elapsed < max_wait_ms:
        for ph in placeholders:
            try:
                el = page.locator(f"input[placeholder='{ph}']")
                if await el.count() > 0 and await el.first.is_visible():
                    return el.first
            except: pass
        for partial in ["delivery location", "new address", "pincode", "area"]:
            try:
                el = page.locator(f"input[placeholder*='{partial}']")
                if await el.count() > 0 and await el.first.is_visible():
                    return el.first
            except: pass
        await page.wait_for_timeout(step)
        elapsed += step
    return None

async def _js_open_location_modal(page: Page, site: str) -> str:
    result = await page.evaluate("""
        (site) => {
            function tryClick(selectors) {
                for (let sel of selectors) {
                    try {
                        let el = document.querySelector(sel);
                        if (el && el.offsetParent !== null) {
                            el.click();
                            return sel;
                        }
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
                if (['button','div','span','a','p'].includes(tag) && node.children.length <= 5 && txt.length > 0 && txt.length < 80 && keywords.some(k => txt.includes(k))) {
                    node.click();
                    return 'header-text:' + txt.slice(0, 40);
                }
            }
            let first = header.querySelector('button, a, [role="button"]');
            if (first) { first.click(); return 'header-first'; }
            header.click();
            return 'header-raw';
        }
    """, site)
    return str(result)

async def _fill_and_trigger(page: Page, el, text: str, delay: int = 60) -> None:
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
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
            }
        """)
    except Exception as ex:
        print(f"fill_and_trigger error: {ex}")

async def _pick_first_suggestion(page: Page, match_text: str = None) -> bool:
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
                        return True
        suggestion_selectors = ["[role='dialog'] li", "[class*='SuggestionItem']", "[class*='LocationSearchList'] > div", "[data-testid='place-item']", "[role='option']", ".pac-item"]
        for sel in suggestion_selectors:
            locs = page.locator(sel)
            count = await locs.count()
            if count > 0:
                for i in range(count):
                    item = locs.nth(i)
                    if await item.is_visible():
                        text = (await item.inner_text()).lower()
                        if "current location" in text or "detect" in text or "gps" in text: continue
                        await item.click()
                        return True
        await page.keyboard.press("ArrowDown")
        await page.wait_for_timeout(300)
        await page.keyboard.press("Enter")
        return False
    except Exception as ex:
        print(f"pick_suggestion error: {ex}")
        return False

async def read_header_info(page: Page, pincode: str) -> tuple[str, str]:
    location_text = "—"
    delivery_time = "—"
    try:
        header_text = ""
        for sel in ["header", "[class*='Header']", "[class*='header']", "nav", "body"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=1000):
                    header_text = await el.inner_text(timeout=1000)
                    break
            except: pass
        lines = [line.strip() for line in header_text.split("\n") if line.strip()]
        for line in lines[:20]:
            low = line.lower()
            if ("min" in low or "⚡" in low) and delivery_time == "—" and len(line) < 30: delivery_time = line
            if delivery_time == "—" and "deliver" in low and ("in " in low or "within" in low): delivery_time = line
            if location_text == "—" and len(line) < 60:
                if (pincode in line or any(city in low for city in ["kolkata", "bengal", "bangalore", "mumbai", "delhi"])):
                    if "search" not in low and "detect" not in low: location_text = line
        if delivery_time == "—":
            try:
                time_el = page.locator("text=/\d+\s*min/i").first
                if await time_el.is_visible(timeout=500): delivery_time = await time_el.inner_text()
            except: pass
    except: pass
    return location_text, delivery_time

class BlinkitScraper:
    BASE_URL = "https://blinkit.com"
    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> tuple[str, str]:
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(3000)
        INPUT_PLACEHOLDERS = ["search delivery location", "Search delivery location"]
        loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=4000)
        if loc_input is None:
            await _js_open_location_modal(self.page, "blinkit")
            await self.page.wait_for_timeout(1500)
            loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=6000)
        if loc_input is None:
            await self.page.keyboard.type(pincode, delay=60)
        else:
            await _fill_and_trigger(self.page, loc_input, pincode)
        await self.page.wait_for_timeout(2500)
        await _pick_first_suggestion(self.page, match_text=pincode)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await self.page.wait_for_timeout(3000)
        await self.page.wait_for_timeout(1500)
        return await read_header_info(self.page, pincode)

    async def search(self, product: str) -> list[ProductResult]:
        try:
            await self.page.locator("a[href='/s/']").first.click()
            await self.page.wait_for_timeout(600)
        except: pass
        typed = False
        selectors = ["input[placeholder='Search for atta dal and more']", "input[placeholder*='atta dal']", "input[placeholder*='Search']", "input[type='search']"]
        for sel in selectors:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    await self.page.keyboard.press("Control+a")
                    await self.page.keyboard.press("Backspace")
                    await el.type(product, delay=50)
                    typed = True; break
            except: pass
        if not typed:
            await self.page.goto(f"{self.BASE_URL}/s/?q={product.replace(' ', '%20')}", wait_until="domcontentloaded", timeout=60000)
        else:
            await self.page.keyboard.press("Enter")
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await self.page.wait_for_timeout(2000)
        for _ in range(3):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(400)
        return await self._extract_products()

    async def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["[data-testid='product-card']", "div[role='button'][id]", "div[class*='tw-flex'][role='button']"]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found; break
            except: pass
        if cards is None: return []
        _, global_delivery = await read_header_info(self.page, "")
        def parse_del(s):
            m = re.search(r'(\d+)', s)
            return int(m.group(1)) if m else 20
        global_del_val = parse_del(global_delivery)
        count = await cards.count()
        for i in range(min(count, 20)):
            try:
                card = cards.nth(i)
                full_text = (await card.inner_text(timeout=1500)).strip()
                if not full_text: continue
                lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                name = "—"
                for sel in ["div.tw-line-clamp-2", "[class*='line-clamp']"]:
                    try:
                        t = (await card.locator(sel).first.inner_text(timeout=400)).strip()
                        if t and not _is_garbage(t): name = t; break
                    except: pass
                if name == "—":
                    for line in lines:
                        if not _is_garbage(line): name = line; break
                weight = "—"
                unit_tokens = [" g", "kg", " ml", " l ", " ltr", " pc", " pack"]
                for line in lines:
                    if any(u in line.lower() for u in unit_tokens) and "₹" not in line and len(line) <= 35 and line.strip() != name.strip():
                        weight = line; break
                price_lines = [l for l in lines if l.startswith("₹") or ("₹" in l and len(l) < 15)]
                price_str = price_lines[0] if price_lines else "0"
                parsed_price = float(re.sub(r'[^\d.]', '', price_str)) if price_lines else 0.0
                orig_price = price_lines[1] if len(price_lines) > 1 else ""
                discount = next((l for l in lines if "%" in l and "off" in l.lower()), "")
                available = "out of stock" not in full_text.lower() and "notify" not in full_text.lower()
                image_url = ""
                try:
                    img_el = card.locator("img").first
                    if await img_el.is_visible(timeout=500): image_url = await img_el.get_attribute("src") or ""
                except: pass
                if name != "—" and parsed_price > 0:
                    products.append(ProductResult(name=name, weight=weight, price=parsed_price, original_price=orig_price, discount=discount, delivery_time=global_del_val, available=available, platform="blinkit", image=image_url))
            except: pass
        return products


class ZeptoScraper:
    BASE_URL = "https://www.zepto.com"
    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> tuple[str, str]:
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2500)
        INPUT_PLACEHOLDERS = ["Search a new address", "Search a new"]
        loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=2000)
        if loc_input is None:
            await _js_open_location_modal(self.page, "zepto")
            await self.page.wait_for_timeout(1800)
            loc_input = await _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=6000)
        if loc_input is None:
            await self.page.keyboard.type(pincode, delay=60)
        else:
            await _fill_and_trigger(self.page, loc_input, pincode)
        await self.page.wait_for_timeout(2500)
        await _pick_first_suggestion(self.page, match_text=pincode)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await self.page.wait_for_timeout(3000)
        for sel in ["text=Confirm", "text=Proceed", "text=Done", "button[class*='confirm']", "button[class*='proceed']"]:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    await self.page.wait_for_timeout(800); break
            except: pass
        await self.page.wait_for_timeout(1500)
        return await read_header_info(self.page, pincode)

    async def search(self, product: str) -> list[ProductResult]:
        search_url = f"{self.BASE_URL}/search?query={product.replace(' ', '+')}"
        await self.page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(4000)
        try:
            await self.page.wait_for_load_state("networkidle", timeout=6000)
        except: pass
        for _ in range(3):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(400)
        return await self._extract_products()

    async def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["a[href^='/pn/']", "[data-testid='product-card']"]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found; break
            except: pass
        if cards is None: return []
        global_delivery = 20
        try:
            hdr_el = self.page.locator("header").first
            hdr = await hdr_el.inner_text(timeout=2000)
            for line in hdr.split("\n"):
                if "min" in line.lower() and len(line) < 30:
                    m = re.search(r'(\d+)', line)
                    if m: global_delivery = int(m.group(1)); break
        except: pass
        count = await cards.count()
        for i in range(min(count, 20)):
            try:
                card = cards.nth(i)
                full_text = (await card.inner_text(timeout=1500)).strip()
                if not full_text: continue
                lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                price_lines = [l for l in lines if l.startswith("₹")]
                discount_lines = [l for l in lines if ("off" in l.lower() or "OFF" in l) and not l.startswith("₹")]
                rating_lines = [l for l in lines if re.match(r'^[\d.]+ \(', l)]
                skip = set(price_lines) | set(discount_lines) | set(rating_lines) | {"ADD"}
                content_lines = [l for l in lines if l not in skip and not _is_garbage(l)]
                name = content_lines[0] if content_lines else "—"
                weight = content_lines[1] if len(content_lines) > 1 else "—"
                price_str = price_lines[0] if price_lines else "0"
                parsed_price = float(re.sub(r'[^\d.]', '', price_str)) if price_lines else 0.0
                orig_price = price_lines[1] if len(price_lines) > 1 else ""
                discount = discount_lines[0] if discount_lines else ""
                available = "out of stock" not in full_text.lower() and "notify" not in full_text.lower()
                image_url = ""
                try:
                    img_el = card.locator("img").first
                    if await img_el.is_visible(timeout=500): image_url = await img_el.get_attribute("src") or ""
                except: pass
                if name != "—" and parsed_price > 0:
                    products.append(ProductResult(name=name, weight=weight, price=parsed_price, original_price=orig_price, discount=discount, delivery_time=global_delivery, available=available, platform="zepto", image=image_url))
            except: pass
        return products

class BigBasketScraper:
    BASE_URL = "https://www.bigbasket.com"
    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> tuple[str, str]:
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2500)
        for sel in ["button[class*='Location']", "div[class*='AddressSelect']", "span[class*='Address']", "text=Select Location"]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=1500):
                    await el.click()
                    break
            except: pass
        await self.page.wait_for_timeout(1500)
        loc_input = await _wait_for_input(self.page, ["Search location", "Enter your city"], max_wait_ms=3000)
        if loc_input:
            await _fill_and_trigger(self.page, loc_input, pincode)
        else:
            await self.page.keyboard.type(pincode, delay=60)
        await self.page.wait_for_timeout(2500)
        await _pick_first_suggestion(self.page, match_text=pincode)
        await self.page.wait_for_timeout(2000)
        return await read_header_info(self.page, pincode)

    async def search(self, product: str) -> list[ProductResult]:
        await self.page.goto(f"{self.BASE_URL}/search/?nc=as&q={product.replace(' ', '+')}", wait_until="domcontentloaded", timeout=60000)
        
        try: await self.page.wait_for_load_state("networkidle", timeout=8000)
        except: await self.page.wait_for_timeout(2000)

        for _ in range(3):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(400)
        return await self._extract_products()

    async def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["div[class*='SKUDeck___StyledDiv']", "a[href^='/pd/']", "li[class*='PaginateItems']"]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found; break
            except: pass

        if cards is None: return []

        count = await cards.count()
        for i in range(min(count, 15)):
            try:
                card = cards.nth(i)
                text = (await card.inner_text(timeout=1500)).strip()
                if not text: continue
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                name = lines[1] if len(lines) > 1 else lines[0]
                weight = "—"
                unit_tokens = [" g", "kg", " ml", " l ", " ltr", " pc", " pack"]
                for l in lines:
                    if any(u in l.lower() for u in unit_tokens) and "₹" not in l and len(l) <= 35:
                        weight = l; break

                price_lines = [l for l in lines if l.startswith("₹")]
                price_str = price_lines[0] if price_lines else "0"
                parsed_price = _parse_price(price_str)
                orig_price = price_lines[1] if len(price_lines) > 1 else ""

                discount = next((l for l in lines if "%" in l and "off" in l.lower()), "")
                available = "out of stock" not in text.lower() and "notify" not in text.lower()

                image_url = ""
                try:
                    img_el = card.locator("img").first
                    if await img_el.is_visible(timeout=500):
                        image_url = await img_el.get_attribute("src") or ""
                except: pass

                if name != "—" and parsed_price > 0:
                    products.append(ProductResult(
                        name=name, weight=weight, price=parsed_price,
                        original_price=orig_price, discount=discount,
                        delivery_time=25, available=available,
                        platform="bigbasket", image=image_url
                    ))
            except: pass
        return products

class InstamartScraper:
    BASE_URL = "https://www.swiggy.com/instamart"
    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> tuple[str, str]:
        await self.page.goto("https://www.swiggy.com/", wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2500)
        loc_input = self.page.locator("input[id='location']")
        if await loc_input.is_visible(timeout=2000):
            await _fill_and_trigger(self.page, loc_input, pincode)
            await self.page.wait_for_timeout(2000)
            await _pick_first_suggestion(self.page, match_text=pincode)
        await self.page.wait_for_timeout(2000)
        return await read_header_info(self.page, pincode)

    async def search(self, product: str) -> list[ProductResult]:
        await self.page.goto(f"{self.BASE_URL}/search?custom_back=true&query={product.replace(' ', '+')}", wait_until="domcontentloaded", timeout=60000)
        
        try: await self.page.wait_for_load_state("networkidle", timeout=6000)
        except: await self.page.wait_for_timeout(2000)

        for _ in range(3):
            await self.page.mouse.wheel(0, 800)
            await self.page.wait_for_timeout(400)
        return await self._extract_products()

    async def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["div[data-testid='item-card']", "div[class*='ItemCard']", "div[class*='ProductList'] > div"]:
            try:
                found = self.page.locator(sel)
                if await found.count() > 0:
                    cards = found; break
            except: pass

        if cards is None: return []

        count = await cards.count()
        for i in range(min(count, 15)):
            try:
                card = cards.nth(i)
                text = (await card.inner_text(timeout=1500)).strip()
                if not text: continue
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                name = lines[0]
                weight = lines[1] if len(lines) > 1 else "—"

                price_lines = [l for l in lines if l.startswith("₹")]
                price_str = price_lines[0] if price_lines else "0"
                parsed_price = _parse_price(price_str)
                orig_price = price_lines[1] if len(price_lines) > 1 else ""

                discount = next((l for l in lines if "%" in l and "off" in l.lower()), "")
                available = "out of stock" not in text.lower()

                image_url = ""
                try:
                    img_el = card.locator("img").first
                    if await img_el.is_visible(timeout=500):
                        image_url = await img_el.get_attribute("src") or ""
                except: pass

                if name != "—" and parsed_price > 0:
                    products.append(ProductResult(
                        name=name, weight=weight, price=parsed_price,
                        original_price=orig_price, discount=discount,
                        delivery_time=18, available=available,
                        platform="instamart", image=image_url
                    ))
            except: pass
        return products

async def run_blinkit(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="blinkit", pincode=pincode, location="—", delivery_time="—", product_query=product)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await ctx.new_page()
            await Stealth().apply_stealth_async(page)
            s = BlinkitScraper(page)
            report.location, report.delivery_time = await s.set_location(pincode)
            report.products = await s.search(product)
        except Exception as e:
            report.error = str(e)
        finally:
            await browser.close()
    return report

async def run_zepto(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="zepto", pincode=pincode, location="—", delivery_time="—", product_query=product)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await ctx.new_page()
            await Stealth().apply_stealth_async(page)
            s = ZeptoScraper(page)
            report.location, report.delivery_time = await s.set_location(pincode)
            report.products = await s.search(product)
        except Exception as e:
            report.error = str(e)
        finally:
            await browser.close()
    return report

async def run_bigbasket(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="bigbasket", pincode=pincode, location="—", delivery_time="—", product_query=product)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await ctx.new_page()
            await Stealth().apply_stealth_async(page)
            s = BigBasketScraper(page)
            report.location, report.delivery_time = await s.set_location(pincode)
            report.products = await s.search(product)
        except Exception as e:
            report.error = str(e)
        finally:
            await browser.close()
    return report

async def run_instamart(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="instamart", pincode=pincode, location="—", delivery_time="—", product_query=product)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        try:
            ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = await ctx.new_page()
            await Stealth().apply_stealth_async(page)
            s = InstamartScraper(page)
            report.location, report.delivery_time = await s.set_location(pincode)
            report.products = await s.search(product)
        except Exception as e:
            report.error = str(e)
        finally:
            await browser.close()
    return report

async def run_all_parallel(pincode: str, product: str) -> list[TestReport]:
    tasks = [
        run_blinkit(pincode, product),
        run_zepto(pincode, product),
        run_bigbasket(pincode, product),
        run_instamart(pincode, product)
    ]
    return list(await asyncio.gather(*tasks))
