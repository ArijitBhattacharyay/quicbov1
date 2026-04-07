import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page, sync_playwright

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
        return int(re.search(r'(\d+)', del_str).group(1))
    except:
        return 20

def type_into(page: Page, selector: str, text: str, delay: int = 50) -> bool:
    try:
        el = page.locator(selector).first
        el.wait_for(state="visible", timeout=5000)
        el.click()
        page.wait_for_timeout(200)
        el.triple_click()
        page.keyboard.press("Control+a")
        page.keyboard.press("Backspace")
        el.type(text, delay=delay)
        return True
    except Exception:
        return False

def click_first_suggestion(page: Page, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            container = page.locator(sel)
            container.first.wait_for(state="visible", timeout=4000)
            container.first.click()
            return True
        except Exception:
            pass
    return False

def read_header_info(page: Page, pincode: str) -> tuple[str, str]:
    location_text = "—"
    delivery_time = "—"
    try:
        header = page.locator("header").first.inner_text(timeout=4000)
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

    def set_location(self, pincode: str) -> tuple[str, str]:
        self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=300000)
        self.page.wait_for_timeout(2000)

        opened = False
        for sel in ["[data-testid='location-btn']", ".LocationBar__Main-sc", "text=Deliver to", "text=Select Location"]:
            try:
                el = self.page.locator(sel).first
                if el.is_visible(timeout=1500):
                    el.click()
                    opened = True
                    break
            except Exception:
                pass
        
        self.page.wait_for_timeout(1200)
        typed = type_into(self.page, "input[placeholder='search delivery location']", pincode)
        if not typed:
            type_into(self.page, "input[placeholder*='delivery']", pincode)

        self.page.wait_for_timeout(2000)
        self.page.keyboard.press("ArrowDown")
        self.page.wait_for_timeout(300)
        self.page.keyboard.press("Enter")

        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            self.page.wait_for_timeout(3000)

        return read_header_info(self.page, pincode)

    def search(self, product: str) -> list[ProductResult]:
        try:
            self.page.locator("a[href='/s/']").first.click()
            self.page.wait_for_timeout(600)
        except:
            pass

        typed = type_into(self.page, "input[placeholder='Search for atta dal and more']", product)
        if not typed:
            typed = type_into(self.page, "input[type='search']", product)
        
        if not typed:
            self.page.goto(f"{self.BASE_URL}/s/?q={product.replace(' ', '%20')}", wait_until="domcontentloaded", timeout=300000)
        else:
            self.page.keyboard.press("Enter")

        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            self.page.wait_for_timeout(2000)

        for _ in range(4):
            self.page.mouse.wheel(0, 900)
            self.page.wait_for_timeout(400)
        return self._extract_products()

    def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["[data-testid='product-card']", "div[role='button'][id]", "div[class*='tw-flex'][role='button']"]:
            try:
                found = self.page.locator(sel)
                if found.count() > 0:
                    cards = found
                    break
            except:
                pass

        if cards is None: return []

        _, global_delivery = read_header_info(self.page, "")
        global_del_val = _parse_delivery(global_delivery)

        for i in range(min(cards.count(), 15)):
            try:
                card = cards.nth(i)
                full_text = card.inner_text(timeout=1500).strip()
                if not full_text: continue
                lines = [l.strip() for l in full_text.split("\n") if l.strip()]

                name = "—"
                for sel in ["div.tw-line-clamp-2", "[class*='line-clamp']"]:
                    try:
                        t = card.locator(sel).first.inner_text(timeout=400).strip()
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

                # Get the real image
                image_url = ""
                try:
                    img_el = card.locator("img").first
                    if img_el.is_visible(timeout=500):
                        image_url = img_el.get_attribute("src") or ""
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

    def set_location(self, pincode: str) -> tuple[str, str]:
        self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=300000)
        self.page.wait_for_timeout(2000)

        for sel in ["text=Select Location", "button[class*='location']", "text=Detect my location"]:
            try:
                el = self.page.locator(sel).first
                if el.is_visible(timeout=1500):
                    el.click()
                    break
            except: pass

        self.page.wait_for_timeout(1000)
        typed = type_into(self.page, "input[placeholder='Search a new address']", pincode)
        if not typed: typed = type_into(self.page, "input[type='text']", pincode)

        self.page.wait_for_timeout(2000)
        self.page.keyboard.press("ArrowDown")
        self.page.wait_for_timeout(300)
        self.page.keyboard.press("Enter")

        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            self.page.wait_for_timeout(2000)

        return read_header_info(self.page, pincode)

    def search(self, product: str) -> list[ProductResult]:
        try:
            self.page.locator("a[href='/search']").first.click()
            self.page.wait_for_timeout(600)
        except: pass

        typed = type_into(self.page, "input[placeholder*='Search']", product)
        if not typed:
            self.page.goto(f"{self.BASE_URL}/search?query={product.replace(' ', '+')}", wait_until="domcontentloaded", timeout=300000)
        else:
            self.page.keyboard.press("Enter")

        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except:
            self.page.wait_for_timeout(2000)

        for _ in range(4):
            self.page.mouse.wheel(0, 900)
            self.page.wait_for_timeout(400)

        return self._extract_products()

    def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["a[href^='/pn/']", "[data-testid='product-card']"]:
            try:
                found = self.page.locator(sel)
                if found.count() > 0:
                    cards = found
                    break
            except: pass

        if cards is None: return []

        global_delivery = 20
        try:
            hdr = self.page.locator("header").first.inner_text(timeout=2000)
            for line in hdr.split("\n"):
                if "min" in line.lower() and len(line) < 30:
                    global_delivery = _parse_delivery(line)
                    break
        except: pass

        for i in range(min(cards.count(), 15)):
            try:
                card = cards.nth(i)
                full_text = card.inner_text(timeout=1500).strip()
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
                    if img_el.is_visible(timeout=500):
                        image_url = img_el.get_attribute("src") or ""
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

    def set_location(self, pincode: str) -> tuple[str, str]:
        self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(2000)
        # Bigbasket location is tricky headers, we will try to default to national or click header
        for sel in ["button[class*='Location']", "div[class*='AddressSelect']", "span[class*='Address']", "text=Select Location"]:
            try:
                el = self.page.locator(sel).first
                if el.is_visible(timeout=1000):
                    el.click()
                    break
            except: pass
        
        self.page.wait_for_timeout(1000)
        type_into(self.page, "input[placeholder*='Search location'], input[placeholder*='Enter your city']", pincode)
        self.page.wait_for_timeout(1500)
        self.page.keyboard.press("ArrowDown")
        self.page.wait_for_timeout(200)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(1500)
        return read_header_info(self.page, pincode)

    def search(self, product: str) -> list[ProductResult]:
        self.page.goto(f"{self.BASE_URL}/custompage/sysgenpd/?type=pc&slug={product.replace(' ', '-')}", wait_until="domcontentloaded", timeout=300000)
        # Use classic URL
        self.page.goto(f"{self.BASE_URL}/search/?nc=as&q={product.replace(' ', '+')}", wait_until="domcontentloaded", timeout=300000)
        
        try: self.page.wait_for_load_state("networkidle", timeout=8000)
        except: self.page.wait_for_timeout(2000)

        for _ in range(4):
            self.page.mouse.wheel(0, 900)
            self.page.wait_for_timeout(400)
        return self._extract_products()

    def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["div[class*='SKUDeck___StyledDiv']", "a[href^='/pd/']", "li[class*='PaginateItems']"]:
            try:
                found = self.page.locator(sel)
                if found.count() > 0:
                    cards = found
                    break
            except: pass

        if cards is None: return []

        for i in range(min(cards.count(), 15)):
            try:
                card = cards.nth(i)
                text = card.inner_text(timeout=1500).strip()
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
                    if img_el.is_visible(timeout=500):
                        image_url = img_el.get_attribute("src") or ""
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

    def set_location(self, pincode: str) -> tuple[str, str]:
        self.page.goto("https://www.swiggy.com/", wait_until="domcontentloaded", timeout=300000)
        self.page.wait_for_timeout(2000)
        type_into(self.page, "input[id='location']", pincode)
        self.page.wait_for_timeout(2000)
        self.page.keyboard.press("ArrowDown")
        self.page.wait_for_timeout(300)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(2000)
        return read_header_info(self.page, pincode)

    def search(self, product: str) -> list[ProductResult]:
        self.page.goto(f"{self.BASE_URL}/search?custom_back=true&query={product.replace(' ', '+')}", wait_until="domcontentloaded", timeout=300000)
        
        try: self.page.wait_for_load_state("networkidle", timeout=6000)
        except: self.page.wait_for_timeout(2000)

        for _ in range(4):
            self.page.mouse.wheel(0, 900)
            self.page.wait_for_timeout(400)
        return self._extract_products()

    def _extract_products(self) -> list[ProductResult]:
        products = []
        cards = None
        for sel in ["div[data-testid='item-card']", "div[class*='ItemCard']", "div[class*='ProductList'] > div"]:
            try:
                found = self.page.locator(sel)
                if found.count() > 0:
                    cards = found; break
            except: pass

        if cards is None: return []

        for i in range(min(cards.count(), 15)):
            try:
                card = cards.nth(i)
                text = card.inner_text(timeout=1500).strip()
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
                    if img_el.is_visible(timeout=500):
                        image_url = img_el.get_attribute("src") or ""
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

def _new_context(pw, headless: bool):
    browser = pw.chromium.launch(headless=headless, slow_mo=0)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.set_default_timeout(300000)  # Set 5 mins global timeout
    return browser, ctx

def run_blinkit(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="blinkit", pincode=pincode, location="—", delivery_time="—", product_query=product)
    try:
        with sync_playwright() as pw:
            browser, ctx = _new_context(pw, True)
            try:
                page = ctx.new_page()
                s = BlinkitScraper(page)
                s.set_location(pincode)
                report.products = s.search(product)
            except Exception as e:
                report.error = str(e)
            finally:
                browser.close()
    except Exception as e:
        report.error = f"Browser Error: {e}"
    return report

def run_zepto(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="zepto", pincode=pincode, location="—", delivery_time="—", product_query=product)
    try:
        with sync_playwright() as pw:
            browser, ctx = _new_context(pw, True)
            try:
                page = ctx.new_page()
                s = ZeptoScraper(page)
                s.set_location(pincode)
                report.products = s.search(product)
            except Exception as e:
                report.error = str(e)
            finally:
                browser.close()
    except Exception as e:
        report.error = f"Browser Error: {e}"
    return report

def run_bigbasket(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="bigbasket", pincode=pincode, location="—", delivery_time="—", product_query=product)
    try:
        with sync_playwright() as pw:
            browser, ctx = _new_context(pw, True)
            try:
                page = ctx.new_page()
                s = BigBasketScraper(page)
                s.set_location(pincode)
                report.products = s.search(product)
            except Exception as e:
                report.error = str(e)
            finally:
                browser.close()
    except Exception as e:
        report.error = f"Browser Error: {e}"
    return report

def run_instamart(pincode: str, product: str) -> TestReport:
    report = TestReport(platform="instamart", pincode=pincode, location="—", delivery_time="—", product_query=product)
    try:
        with sync_playwright() as pw:
            browser, ctx = _new_context(pw, True)
            try:
                page = ctx.new_page()
                s = InstamartScraper(page)
                s.set_location(pincode)
                report.products = s.search(product)
            except Exception as e:
                report.error = str(e)
            finally:
                browser.close()
    except Exception as e:
        report.error = f"Browser Error: {e}"
    return report

def run_all_parallel(pincode: str, product: str) -> list[TestReport]:
    results = [None, None, None, None]
    # Scraping all 4 simultaneously!
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_b = pool.submit(run_blinkit, pincode, product)
        future_z = pool.submit(run_zepto, pincode, product)
        future_bb = pool.submit(run_bigbasket, pincode, product)
        future_i = pool.submit(run_instamart, pincode, product)
        results[0] = future_b.result()
        results[1] = future_z.result()
        results[2] = future_bb.result()
        results[3] = future_i.result()
    return [r for r in results if r is not None]
