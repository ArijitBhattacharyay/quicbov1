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

def _parse_delivery(del_str: str) -> int:
    try:
        match = re.search(r'(\d+)', del_str)
        return int(match.group(1)) if match else 20
    except:
        return 20

async def type_into(page: Page, selector: str, text: str, delay: int = 50) -> bool:
    try:
        el = page.locator(selector).first
        await el.wait_for(state="visible", timeout=5000)
        await el.click()
        await page.wait_for_timeout(200)
        await el.dblclick() # Triple click isn't standard in async_api, dblclick + select all
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Backspace")
        await el.type(text, delay=delay)
        return True
    except Exception:
        return False

async def click_first_suggestion(page: Page, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            container = page.locator(sel)
            await container.first.wait_for(state="visible", timeout=4000)
            await container.first.click()
            return True
        except Exception:
            pass
    return False

async def read_header_info(page: Page, pincode: str) -> tuple[str, str]:
    location_text = "—"
    delivery_time = "—"
    try:
        header_el = page.locator("header").first
        header = await header_el.inner_text(timeout=4000)
        for line in header.split("\n"):
            line = line.strip()
            if not line: continue
            low = line.lower()
            if "min" in low and delivery_time == "—":
                delivery_time = line
            if delivery_time == "—" and "deliver" in low and ("in " in low or "within" in low):
                delivery_time = line
            if pincode in line and location_text == "—":
                location_text = line
    except Exception:
        pass
    return location_text, delivery_time

class BlinkitScraper:
    BASE_URL = "https://blinkit.com"
    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> tuple[str, str]:
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2000)

        opened = False
        for sel in ["[data-testid='location-btn']", ".LocationBar__Main-sc", "text=Deliver to", "text=Select Location"]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=1500):
                    await el.click()
                    opened = True
                    break
            except Exception:
                pass
        
        await self.page.wait_for_timeout(1200)
        typed = await type_into(self.page, "input[placeholder='search delivery location']", pincode)
        if not typed:
            await type_into(self.page, "input[placeholder*='delivery']", pincode)

        await self.page.wait_for_timeout(2000)
        await self.page.keyboard.press("ArrowDown")
        await self.page.wait_for_timeout(300)
        await self.page.keyboard.press("Enter")

        try:
            await self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await self.page.wait_for_timeout(3000)

        return await read_header_info(self.page, pincode)

    async def search(self, product: str) -> list[ProductResult]:
        try:
            await self.page.locator("a[href='/s/']").first.click()
            await self.page.wait_for_timeout(600)
        except:
            pass

        typed = await type_into(self.page, "input[placeholder='Search for atta dal and more']", product)
        if not typed:
            typed = await type_into(self.page, "input[type='search']", product)
        
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
                    cards = found
                    break
            except:
                pass

        if cards is None: return []

        _, global_delivery = await read_header_info(self.page, "")
        global_del_val = _parse_delivery(global_delivery)

        count = await cards.count()
        for i in range(min(count, 15)):
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

                weight = "—"
                unit_tokens = [" g", "kg", " ml", " l ", " ltr", " pc", " pack"]
                for line in lines:
                    if any(u in line.lower() for u in unit_tokens) and "₹" not in line and len(line) <= 35:
                        weight = line
                        break

                price_lines = [l for l in lines if l.startswith("₹") or ("₹" in l and len(l) < 15)]
                price_str = price_lines[0] if price_lines else "0"
                orig_price = price_lines[1] if len(price_lines) > 1 else ""
                parsed_price = _parse_price(price_str)

                discount = next((l for l in lines if "%" in l and "off" in l.lower()), "")
                available = "out of stock" not in full_text.lower() and "notify" not in full_text.lower()

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
                        delivery_time=global_del_val, available=available,
                        platform="blinkit", image=image_url
                    ))
            except Exception as e:
                pass
        return products


class ZeptoScraper:
    BASE_URL = "https://www.zepto.com"
    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> tuple[str, str]:
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2000)

        for sel in ["text=Select Location", "button[class*='location']", "text=Detect my location"]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=1500):
                    await el.click()
                    break
            except: pass

        await self.page.wait_for_timeout(1000)
        typed = await type_into(self.page, "input[placeholder='Search a new address']", pincode)
        if not typed: typed = await type_into(self.page, "input[type='text']", pincode)

        await self.page.wait_for_timeout(2000)
        await self.page.keyboard.press("ArrowDown")
        await self.page.wait_for_timeout(300)
        await self.page.keyboard.press("Enter")

        try:
            await self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await self.page.wait_for_timeout(2000)

        return await read_header_info(self.page, pincode)

    async def search(self, product: str) -> list[ProductResult]:
        search_url = f"{self.BASE_URL}/search?query={product.replace(' ', '+')}"
        await self.page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        
        # Explicitly wait for React to fetch and render actual search results over "Trending Items"
        await self.page.wait_for_timeout(4000)
        
        try:
            await self.page.wait_for_load_state("networkidle", timeout=6000)
        except:
            pass

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
                    cards = found
                    break
            except: pass

        if cards is None: return []

        global_delivery = 20
        try:
            hdr_el = self.page.locator("header").first
            hdr = await hdr_el.inner_text(timeout=2000)
            for line in hdr.split("\n"):
                if "min" in line.lower() and len(line) < 30:
                    global_delivery = _parse_delivery(line)
                    break
        except: pass

        count = await cards.count()
        for i in range(min(count, 15)):
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
                parsed_price = _parse_price(price_str)
                orig_price = price_lines[1] if len(price_lines) > 1 else ""

                discount = discount_lines[0] if discount_lines else ""
                available = "out of stock" not in full_text.lower() and "notify" not in full_text.lower()

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
                        delivery_time=global_delivery, available=available,
                        platform="zepto", image=image_url
                    ))
            except Exception as e:
                pass
        return products

class BigBasketScraper:
    BASE_URL = "https://www.bigbasket.com"
    def __init__(self, page: Page):
        self.page = page

    async def set_location(self, pincode: str) -> tuple[str, str]:
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(2000)
        for sel in ["button[class*='Location']", "div[class*='AddressSelect']", "span[class*='Address']", "text=Select Location"]:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    break
            except: pass
        
        await self.page.wait_for_timeout(1000)
        await type_into(self.page, "input[placeholder*='Search location'], input[placeholder*='Enter your city']", pincode)
        await self.page.wait_for_timeout(1500)
        await self.page.keyboard.press("ArrowDown")
        await self.page.wait_for_timeout(200)
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(1500)
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
        await self.page.wait_for_timeout(2000)
        await type_into(self.page, "input[id='location']", pincode)
        await self.page.wait_for_timeout(2000)
        await self.page.keyboard.press("ArrowDown")
        await self.page.wait_for_timeout(300)
        await self.page.keyboard.press("Enter")
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
