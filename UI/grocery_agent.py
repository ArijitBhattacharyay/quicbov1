"""
╔══════════════════════════════════════════════════════════════╗
║        Grocery Delivery Automated Testing Agent              ║
║        Platforms: Blinkit | Zepto                            ║
║        Extracts: Product Name, Price, Delivery Time          ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python grocery_agent.py
    python grocery_agent.py --platform blinkit --pincode 700063 --product "Amul Dahi"
    python grocery_agent.py --platform zepto   --pincode 700063 --product "Farmlite"
    python grocery_agent.py --platform both    --pincode 700063 --product "Amul Dahi"

Install dependencies:
    pip install colorama playwright tabulate
    playwright install chromium
"""

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

from colorama import Fore, Style, init
from playwright.sync_api import Page, sync_playwright
from tabulate import tabulate

init(autoreset=True)


# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class ProductResult:
    name: str
    weight: str
    price: str
    original_price: str
    discount: str
    delivery_time: str
    available: bool = True
    platform: str = ""


@dataclass
class TestReport:
    platform: str
    pincode: str
    location: str
    delivery_time: str
    product_query: str
    products: list[ProductResult] = field(default_factory=list)
    error: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────
def banner(msg: str, color=Fore.CYAN) -> None:
    width = 62
    print(f"\n{color}{'─' * width}")
    print(f"  {msg}")
    print(f"{'─' * width}{Style.RESET_ALL}")


def log(msg: str, color=Fore.WHITE) -> None:
    print(f"{color}  ▸ {msg}{Style.RESET_ALL}")


def ok(msg: str) -> None:
    print(f"{Fore.GREEN}  ✓ {msg}{Style.RESET_ALL}")


def warn(msg: str) -> None:
    print(f"{Fore.YELLOW}  ⚠ {msg}{Style.RESET_ALL}")


def err(msg: str) -> None:
    print(f"{Fore.RED}  ✗ {msg}{Style.RESET_ALL}")


# Matches review counts like "(5.1k)", "(308)", "(28.5k)"
_REVIEW_PATTERN = re.compile(r'^\(\d+[\d.,]*[kKmM]?\)$')
# UI button labels to reject as product names
_UI_WORDS = {"ADD", "REMOVE", "BUY", "LOGIN", "CART", "SEARCH",
             "CLOSE", "CANCEL", "OK", "DONE", "SELECT", "CONFIRM"}

def _is_garbage(text: str) -> bool:
    """Return True if a text line is clearly not a product name."""
    t = text.strip()
    if not t or len(t) < 2:
        return True
    if "₹" in t:
        return True
    if _REVIEW_PATTERN.match(t):
        return True
    if re.match(r'^\d+[\d.,]*[kKmM]?$', t):
        return True
    # Reject short all-caps UI button words
    if t.upper() in _UI_WORDS:
        return True
    # Reject strings like "4.7 (47.9k) 7 mins" (ratings)
    if re.match(r'^[\d.]+ \(', t):
        return True
    return False


def type_into(page: Page, selector: str, text: str, delay: int = 50) -> bool:
    """
    Click an element, clear it, and type text character-by-character to
    trigger JS autocomplete listeners. Returns True on success.
    delay=50ms is fast enough to trigger autocomplete while staying reliable.
    """
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
    """
    Wait for any suggestion dropdown to appear and click the FIRST item.
    Always picks item 0 — no ambiguity.
    """
    for sel in selectors:
        try:
            container = page.locator(sel)
            # Wait for at least one to appear
            container.first.wait_for(state="visible", timeout=4000)
            container.first.click()
            log(f"Clicked first suggestion via: {sel}")
            return True
        except Exception:
            pass
    return False


def read_header_info(page: Page, pincode: str) -> tuple[str, str]:
    """Extract location text and delivery time from the page top bar / body."""
    location_text = "—"
    delivery_time = "—"
    try:
        # Fallback to body if header not found
        header_text = ""
        for sel in ["header", "[class*='Header']", "[class*='header']", "nav", "body"]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=1000):
                    header_text = el.inner_text(timeout=1000)
                    break
            except Exception:
                pass

        lines = [line.strip() for line in header_text.split("\n") if line.strip()]
        # Only check the top portion of the text to avoid matching products
        for line in lines[:20]:
            low = line.lower()
            if ("min" in low or "⚡" in low) and delivery_time == "—" and len(line) < 30:
                delivery_time = line
            if delivery_time == "—" and "deliver" in low and ("in " in low or "within" in low):
                delivery_time = line
            
            # Identify location line
            if location_text == "—" and len(line) < 60:
                if (pincode in line or any(city in low for city in
                    ["kolkata", "bengal", "bangalore", "bengaluru",
                     "mumbai", "delhi", "hyderabad", "chennai", "pune",
                     "layout", "nagar", "road"]
                )):
                    # Ignore lines that are buttons or input placeholders
                    if "search" not in low and "detect" not in low and "enter" not in low:
                        location_text = line
                        
        # Immediate fallback for delivery time using direct regex locator
        if delivery_time == "—":
            try:
                # Find any text node resembling "X mins" or "X minutes"
                time_el = page.locator("text=/\d+\s*min/i").first
                if time_el.is_visible(timeout=500):
                    delivery_time = time_el.inner_text().strip()
            except Exception:
                pass
                
    except Exception as ex:
        warn(f"Header info read failed: {ex}")
    return location_text, delivery_time


def _wait_for_input(page: Page, placeholders: list[str],
                    max_wait_ms: int = 8000) -> Optional[object]:
    """
    Poll until one of the given inputs is visible, then return the locator.
    Returns None if nothing appears within max_wait_ms.
    """
    step = 300
    elapsed = 0
    while elapsed < max_wait_ms:
        for ph in placeholders:
            try:
                el = page.locator(f"input[placeholder='{ph}']")
                if el.count() > 0 and el.first.is_visible():
                    return el.first
            except Exception:
                pass
        # Also try partial placeholder matches
        for partial in ["delivery location", "new address", "pincode", "area"]:
            try:
                el = page.locator(f"input[placeholder*='{partial}']")
                if el.count() > 0 and el.first.is_visible():
                    return el.first
            except Exception:
                pass
        page.wait_for_timeout(step)
        elapsed += step
    return None


def _js_open_location_modal(page: Page, site: str) -> str:
    """
    Use JavaScript to find and click the location trigger element in the header.
    Returns a string describing what was clicked (for logging).
    """
    result = page.evaluate("""
        (site) => {
            // Helper: click first matching element, return its text
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

            // 1. Try known data-testid / aria-label selectors
            let r = tryClick([
                "[data-testid='location-btn']",
                "button[aria-label*='location']",
                "button[aria-label*='Location']",
                "button[aria-label*='Layout']",
                "button[aria-label*='Nagar']",
                "button[aria-label*='Road']",
            ]);
            if (r) return r;

            // 2. Walk the header and click first element whose text
            //    mentions delivery / location / area
            let header = document.querySelector('header');
            if (!header) return 'no-header';

            let keywords = ['deliver', 'location', 'area', 'pincode',
                            'select', 'address', 'nagar', 'layout'];
            let walker = document.createTreeWalker(
                header, NodeFilter.SHOW_ELEMENT);
            let node;
            while ((node = walker.nextNode())) {
                let txt = (node.innerText || '').toLowerCase().trim();
                let tag = node.tagName.toLowerCase();
                // Only click leaf-ish nodes (button, div, span, a)
                if (['button','div','span','a','p'].includes(tag)
                        && node.children.length <= 5
                        && txt.length > 0 && txt.length < 80
                        && keywords.some(k => txt.includes(k))) {
                    node.click();
                    return 'header-text:' + txt.slice(0, 40);
                }
            }

            // 3. Last resort: click first clickable child of header
            let first = header.querySelector('button, a, [role="button"]');
            if (first) { first.click(); return 'header-first'; }
            header.click();
            return 'header-raw';
        }
    """, site)
    return str(result)


def _fill_and_trigger(page: Page, el, text: str, delay: int = 60) -> None:
    """
    Fill an input element and fire input/change events to trigger autocomplete.
    IMPORTANT: Many sites (Blinkit) pre-fill the location input with a previous
    pincode. We MUST clear it fully before typing the new one.
    """
    try:
        # Step 1: Triple-click = click(click_count=3) — selects all existing text
        el.click(click_count=3)
        page.wait_for_timeout(150)
        # Step 2: Ctrl+A as belt-and-suspenders select-all
        page.keyboard.press("Control+a")
        page.wait_for_timeout(50)
        # Step 3: Delete the selected text
        page.keyboard.press("Delete")
        page.wait_for_timeout(50)
        # Step 4: JS clear to handle React controlled inputs that ignore key events
        el.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input',{bubbles:true})); }")
        page.wait_for_timeout(100)
        # Step 5: Type the new pincode character by character
        el.type(text, delay=delay)
        # Step 6: Extra synthetic events for React/Vue autocomplete listeners
        el.evaluate("""
            el => {
                el.dispatchEvent(new Event('input',  {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
            }
        """)
    except Exception as ex:
        warn(f"fill_and_trigger error: {ex}")



def _pick_first_suggestion(page: Page, match_text: str = None) -> bool:
    """
    Wait for suggestion dropdown then click the first item.
    Uses Playwright's text engine to reliably click the deepest suggestion 
    containing the pincode, bypassing the need to guess DOM classes or tags.
    """
    try:
        # Give network time to populate suggestions
        page.wait_for_timeout(3000)

        # 1. Deepest text match approach (Extremely robust for dynamically generated React/Vue lists)
        if match_text:
            # Playwright's `text="string"` selector finds elements containing the string.
            # When multiple match (e.g. wrapper divs), it automatically prefers the deepest element.
            locs = page.locator(f"text={match_text}")
            count = locs.count()
            for i in range(count):
                el = locs.nth(i)
                if el.is_visible():
                    tag = el.evaluate("e => e.tagName.toLowerCase()")
                    if tag != "input":  # Don't click the search bar again
                        el.click()
                        log(f"Picked suggestion perfectly via text match: '{match_text}'")
                        return True

        # 2. Heuristic fallback for generic dropdown classes (if strict match fails)
        suggestion_selectors = [
            "[role='dialog'] li",
            "[class*='SuggestionItem']",
            "[class*='LocationSearchList'] > div",
            "[data-testid='place-item']",
            "[role='option']",
            ".pac-item"
        ]
        
        for sel in suggestion_selectors:
            locs = page.locator(sel)
            if locs.count() > 0:
                for i in range(locs.count()):
                    item = locs.nth(i)
                    if item.is_visible():
                        text = item.inner_text().lower()
                        if "current location" in text or "detect" in text or "gps" in text:
                            continue
                        item.click()
                        log(f"Picked fallback suggestion via Playwright element: '{text[:30].replace(chr(10), ' ')}'")
                        return True
            
        warn("Suggestion selected via keyboard ArrowDown+Enter fallback")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(300)
        page.keyboard.press("Enter")
        return False
        
    except Exception as ex:
        warn(f"pick_suggestion error: {ex}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  BLINKIT SCRAPER
# ═══════════════════════════════════════════════════════════════════════════════
class BlinkitScraper:
    BASE_URL = "https://blinkit.com"

    def __init__(self, page: Page):
        self.page = page

    # ── Location ──────────────────────────────────────────────────────────────
    def set_location(self, pincode: str) -> tuple[str, str]:
        log("Opening Blinkit …", Fore.CYAN)
        self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(3000)   # React needs time to render

        # ── Step 1: Find the location input ──────────────────────────────────
        # Blinkit ALWAYS pre-fills the input with a previous pincode (from
        # localStorage/cookies). The modal may auto-open or need a click.
        INPUT_PLACEHOLDERS = ["search delivery location", "Search delivery location"]

        # First check if modal is already open (common on first page load)
        loc_input = _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=4000)

        if loc_input is None:
            # Need to click the header location area to open it
            log("Clicking Blinkit location trigger via JS …", Fore.CYAN)
            result = _js_open_location_modal(self.page, "blinkit")
            log(f"JS trigger result: {result}")
            self.page.wait_for_timeout(1500)
            loc_input = _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=6000)

        if loc_input is None:
            warn("Blinkit location input not found — keyboard fallback")
            self.page.keyboard.type(pincode, delay=60)
        else:
            # ── Step 2: Clear pre-filled content and type new pincode ─────────
            log(f"Typing pincode '{pincode}' into Blinkit input …", Fore.CYAN)
            _fill_and_trigger(self.page, loc_input, pincode)

        # ── Step 3: Wait for suggestions & pick the FIRST one ────────────────
        self.page.wait_for_timeout(2500)
        _pick_first_suggestion(self.page, match_text=pincode)

        # ── Step 4: Wait for page to reflect new location ─────────────────────
        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            self.page.wait_for_timeout(3000)

        # Let asynchronous UI elements (like updated ETAs) render
        self.page.wait_for_timeout(1500)
        location_text, delivery_time = read_header_info(self.page, pincode)
        ok(f"Blinkit ► Location: {location_text}  |  Delivery: {delivery_time}")
        return location_text, delivery_time

    # ── Product search via the on-page search bar ─────────────────────────────
    def search(self, product: str) -> list[ProductResult]:
        log(f"Blinkit search: '{product}' …", Fore.CYAN)

        # Click the search anchor <a href="/s/"> then type into the input
        try:
            self.page.locator("a[href='/s/']").first.click()
            self.page.wait_for_timeout(600)
        except Exception:
            pass

        # Confirmed placeholder from live DOM
        typed = type_into(self.page,
                          "input[placeholder='Search for atta dal and more']",
                          product)

        if not typed:
            for sel in [
                "input[placeholder*='atta dal']",
                "input[placeholder*='Search for']",
                "input[placeholder*='Search']",
                "[class*='search'] input",
                "input[type='search']",
            ]:
                if type_into(self.page, sel, product):
                    typed = True
                    break

        if not typed:
            warn("Blinkit search input not found — URL fallback")
            self.page.goto(f"{self.BASE_URL}/s/?q={product.replace(' ', '%20')}",
                           wait_until="domcontentloaded", timeout=30000)
        else:
            self.page.keyboard.press("Enter")

        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            self.page.wait_for_timeout(3000)

        # Scroll to trigger lazy loading
        for _ in range(5):
            self.page.mouse.wheel(0, 900)
            self.page.wait_for_timeout(400)
        self.page.wait_for_timeout(800)

        return self._extract_products()

    # ── Extraction ────────────────────────────────────────────────────────────
    def _extract_products(self) -> list[ProductResult]:
        products: list[ProductResult] = []

        # Card container — Blinkit uses Tailwind tw- classes + numeric id
        cards = None
        for sel in [
            "[data-testid='product-card']",
            "div[role='button'][id]",
            "div[class*='tw-flex'][role='button']",
        ]:
            try:
                found = self.page.locator(sel)
                c = found.count()
                if c > 0:
                    cards = found
                    log(f"Blinkit: {c} cards via '{sel}'")
                    break
            except Exception:
                pass

        if cards is None:
            warn("Blinkit: no cards found — text fallback")
            return self._text_fallback("Blinkit")

        _, global_delivery = read_header_info(self.page, "")

        for i in range(cards.count()):
            try:
                card = cards.nth(i)
                full_text = card.inner_text(timeout=1500).strip()
                if not full_text:
                    continue

                lines = [l.strip() for l in full_text.split("\n") if l.strip()]

                # ── Name: tw-line-clamp-2 is confirmed for Blinkit cards ──────
                name = "—"
                for sel in ["div.tw-line-clamp-2", "[class*='line-clamp']",
                             "[class*='item-name']", "[class*='product-name']"]:
                    try:
                        t = card.locator(sel).first.inner_text(timeout=400).strip()
                        if t and not _is_garbage(t):
                            name = t
                            break
                    except Exception:
                        pass
                # Text fallback: first non-garbage line
                if name == "—":
                    for line in lines:
                        if not _is_garbage(line):
                            name = line
                            break

                # ── Weight: short line with units, distinct from name ─────────
                weight = "—"
                unit_tokens = [" g", "kg", " ml", " l ", " ltr", " pc",
                               " pack", " litre", " gm", " gms", "tablet"]
                for line in lines:
                    low = line.lower()
                    # Must contain a unit, must not be a price, must be short
                    # (≤35 chars) and must NOT be the same as the product name
                    if (any(u in low for u in unit_tokens)
                            and "₹" not in line
                            and len(line) <= 35
                            and line.strip() != name.strip()):
                        weight = line
                        break

                # ── Prices: collect all ₹ lines ───────────────────────────────
                price_lines = [l for l in lines
                               if l.startswith("₹") or ("₹" in l and len(l) < 15)]
                price = price_lines[0] if price_lines else "—"
                orig_price = price_lines[1] if len(price_lines) > 1 else "—"

                # ── Discount ──────────────────────────────────────────────────
                discount = "—"
                for line in lines:
                    if "%" in line and "off" in line.lower():
                        discount = line
                        break

                available = "out of stock" not in full_text.lower() \
                            and "notify" not in full_text.lower()

                if name != "—":
                    products.append(ProductResult(
                        name=name, weight=weight, price=price,
                        original_price=orig_price, discount=discount,
                        delivery_time=global_delivery, available=available,
                        platform="Blinkit",
                    ))
            except Exception as ex:
                warn(f"Blinkit card {i} skipped: {ex}")

        ok(f"Blinkit: extracted {len(products)} products")
        return products

    def _text_fallback(self, platform: str) -> list[ProductResult]:
        try:
            body = self.page.inner_text("body", timeout=4000)
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            results = []
            i = 0
            while i < len(lines) - 1:
                line = lines[i]
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                nxt2 = lines[i + 2] if i + 2 < len(lines) else ""
                if not _is_garbage(line):
                    price_cand = next(
                        (x for x in [nxt, nxt2] if x.startswith("₹")), None
                    )
                    if price_cand:
                        results.append(ProductResult(
                            name=line, weight="—", price=price_cand,
                            original_price="—", discount="—",
                            delivery_time="See page", platform=platform,
                        ))
                        i += 3
                        continue
                i += 1
            return results[:20]
        except Exception:
            return []


# ═══════════════════════════════════════════════════════════════════════════════
#  ZEPTO SCRAPER
# ═══════════════════════════════════════════════════════════════════════════════
class ZeptoScraper:
    BASE_URL = "https://www.zepto.com"

    def __init__(self, page: Page):
        self.page = page

    # ── Location ──────────────────────────────────────────────────────────────
    def set_location(self, pincode: str) -> tuple[str, str]:
        log("Opening Zepto …", Fore.MAGENTA)
        self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(2500)

        # ── Step 1: Get the location input open ───────────────────────────────
        INPUT_PLACEHOLDERS = [
            "Search a new address",
            "Search a new",
        ]

        loc_input = _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=2000)

        if loc_input is None:
            log("Clicking Zepto location trigger via JS …", Fore.MAGENTA)
            result = _js_open_location_modal(self.page, "zepto")
            log(f"JS trigger result: {result}")
            self.page.wait_for_timeout(1800)
            loc_input = _wait_for_input(self.page, INPUT_PLACEHOLDERS, max_wait_ms=6000)

        if loc_input is None:
            warn("Zepto location input not found — keyboard fallback")
            self.page.keyboard.type(pincode, delay=60)
        else:
            # ── Step 2: Type pincode ──────────────────────────────────────────
            log(f"Typing pincode '{pincode}' into Zepto input …", Fore.MAGENTA)
            _fill_and_trigger(self.page, loc_input, pincode)

        # ── Step 3: Wait for suggestions & pick the first ─────────────────────
        self.page.wait_for_timeout(2500)
        _pick_first_suggestion(self.page, match_text=pincode)

        # ── Step 4: Wait for location to be applied ───────────────────────────
        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            self.page.wait_for_timeout(3000)

        # Dismiss confirmation popups
        for sel in ["text=Confirm", "text=Proceed", "text=Done",
                    "button[class*='confirm']", "button[class*='proceed']"]:
            try:
                btn = self.page.locator(sel).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    self.page.wait_for_timeout(800)
                    break
            except Exception:
                pass

        # Let asynchronous UI elements (like updated ETAs) render
        self.page.wait_for_timeout(1500)
        location_text, delivery_time = read_header_info(self.page, pincode)
        ok(f"Zepto ► Location: {location_text}  |  Delivery: {delivery_time}")
        return location_text, delivery_time


    # ── Product search via the on-page search bar ─────────────────────────────
    def search(self, product: str) -> list[ProductResult]:
        log(f"Zepto search: '{product}' …", Fore.MAGENTA)

        try:
            self.page.locator("a[href='/search']").first.click()
            self.page.wait_for_timeout(600)
        except Exception:
            pass

        # Confirmed placeholder from live DOM
        typed = type_into(self.page,
                          "input[placeholder='Search for over 5000 products']",
                          product)

        if not typed:
            for sel in [
                "input[placeholder*='5000 products']",
                "input[placeholder*='Search for']",
                "input[placeholder*='Search']",
                "[class*='search'] input",
                "input[type='search']",
            ]:
                if type_into(self.page, sel, product):
                    typed = True
                    break

        if not typed:
            warn("Zepto search input not found — URL fallback")
            self.page.goto(
                f"{self.BASE_URL}/search?query={product.replace(' ', '+')}",
                wait_until="domcontentloaded", timeout=30000,
            )
        else:
            self.page.keyboard.press("Enter")

        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            self.page.wait_for_timeout(3000)

        for _ in range(5):
            self.page.mouse.wheel(0, 900)
            self.page.wait_for_timeout(400)
        self.page.wait_for_timeout(800)

        return self._extract_products()

    # ── Extraction ────────────────────────────────────────────────────────────
    def _extract_products(self) -> list[ProductResult]:
        """
        Zepto card structure (confirmed from live screenshot + DOM inspection):
          - Card container : a[href^='/pn/']  (product page links)
          - Per card visual order:
              1. Product image + ADD button
              2. Price (green badge, e.g. ₹24) + MRP (strikethrough ₹25)
              3. Discount label (e.g. ₹1 OFF)
              4. Product name  (plain text, e.g. Amul Curd Pouch)
              5. Weight/qty    (e.g. 1 pack (450 g))
              6. Rating + delivery time (e.g. 4.7 (47.9k) 7 mins)
        """
        products: list[ProductResult] = []

        # Delivery time from the header (e.g. "7 minutes")
        global_delivery = "—"
        try:
            # Check the whole body for a generic ETA because the top bar changes often
            time_el = self.page.locator("text=/\d+\s*min/i").first
            if time_el.is_visible(timeout=1000):
                global_delivery = time_el.inner_text().strip()
        except Exception:
            pass

        # Card container: every Zepto product is an anchor to /pn/...
        cards = None
        for sel in [
            "a[href^='/pn/']",               # confirmed live DOM
            "a[data-testid='product-card']",
            "[data-testid='product-card']",
        ]:
            try:
                found = self.page.locator(sel)
                c = found.count()
                if c > 0:
                    cards = found
                    log(f"Zepto: {c} cards via '{sel}'")
                    break
            except Exception:
                pass

        if cards is None:
            warn("Zepto: no cards found — text fallback")
            return self._text_fallback("Zepto")

        for i in range(cards.count()):
            try:
                card = cards.nth(i)
                full_text = card.inner_text(timeout=1500).strip()
                if not full_text:
                    continue

                # Split card text into clean lines
                lines = [l.strip() for l in full_text.split("\n") if l.strip()]

                # ── Parse lines in confirmed visual order ─────────────────────
                # Lines look like:
                #   ADD               ← button (skip)
                #   ₹24               ← current price
                #   ₹25               ← MRP (optional, strikethrough)
                #   ₹1 OFF            ← discount (optional, has OFF)
                #   Amul Curd Pouch   ← product name
                #   1 pack (450 g)    ← weight
                #   4.7 (47.9k) 7 mins  ← rating+delivery (skip)

                price_lines   = [l for l in lines if l.startswith("₹")]
                discount_lines = [l for l in lines
                                  if ("off" in l.lower() or "OFF" in l)
                                  and not l.startswith("₹")]
                # Rating lines: start with a number followed by "("
                rating_lines   = [l for l in lines if re.match(r'^[\d.]+ \(', l)]

                skip = set(price_lines) | set(discount_lines) | set(rating_lines) | {"ADD"}
                content_lines  = [l for l in lines if l not in skip and not _is_garbage(l)]

                # Name = first content line
                name = content_lines[0] if content_lines else "—"

                # Weight = second content line (or first line with unit tokens)
                weight = "—"
                unit_tokens = [" g", "kg", " ml", " l", " ltr", " pc",
                               " pack", " litre", " gm", " gms", "tablet"]
                if len(content_lines) > 1:
                    weight = content_lines[1]
                # Validate it actually looks like a weight
                if not any(u in weight.lower() for u in unit_tokens):
                    weight = "—"
                    for l in lines:
                        if any(u in l.lower() for u in unit_tokens) \
                                and l not in skip and len(l) <= 35:
                            weight = l
                            break

                # Prices
                price     = price_lines[0] if price_lines else "—"
                orig_price = price_lines[1] if len(price_lines) > 1 else "—"

                # Discount: prefer "X% OFF" over "₹N OFF"
                discount = "—"
                for dl in discount_lines:
                    if "%" in dl:
                        discount = dl
                        break
                if discount == "—" and discount_lines:
                    discount = discount_lines[0]

                available = ("out of stock" not in full_text.lower()
                             and "notify" not in full_text.lower())

                if name != "—":
                    products.append(ProductResult(
                        name=name, weight=weight, price=price,
                        original_price=orig_price, discount=discount,
                        delivery_time=global_delivery, available=available,
                        platform="Zepto",
                    ))
            except Exception as ex:
                warn(f"Zepto card {i} skipped: {ex}")

        ok(f"Zepto: extracted {len(products)} products")
        return products

    def _text_fallback(self, platform: str) -> list[ProductResult]:
        """Last-resort: scan body text for product name + price pairs."""
        try:
            body = self.page.inner_text("body", timeout=4000)
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            results = []
            i = 0
            while i < len(lines) - 1:
                line = lines[i]
                nxt  = lines[i + 1] if i + 1 < len(lines) else ""
                nxt2 = lines[i + 2] if i + 2 < len(lines) else ""
                if not _is_garbage(line):
                    price_cand = next(
                        (x for x in [nxt, nxt2] if x.startswith("₹")), None
                    )
                    if price_cand:
                        results.append(ProductResult(
                            name=line, weight="—", price=price_cand,
                            original_price="—", discount="—",
                            delivery_time="See page", platform=platform,
                        ))
                        i += 3
                        continue
                i += 1
            return results[:20]
        except Exception:
            return []


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORT + CSV
# ═══════════════════════════════════════════════════════════════════════════════
def print_report(report: TestReport) -> None:
    color = Fore.GREEN if report.platform == "Blinkit" else Fore.MAGENTA
    banner(f"📦 {report.platform.upper()} — Results", color)
    print(f"{color}  Platform      : {report.platform}")
    print(f"  Pincode       : {report.pincode}")
    print(f"  Location      : {report.location}")
    print(f"  Delivery Time : {report.delivery_time}")
    print(f"  Search Query  : {report.product_query}")
    print(f"  Products Found: {len(report.products)}{Style.RESET_ALL}\n")

    if report.error:
        err(f"Error: {report.error}")
        return
    if not report.products:
        warn("No products found.")
        return

    rows = []
    for p in report.products:
        status = "✅ In Stock" if p.available else "❌ Out of Stock"
        rows.append([
            p.name[:50] + ("…" if len(p.name) > 50 else ""),
            p.weight[:18],
            p.price,
            p.original_price,
            p.discount,
            p.delivery_time,
            status,
        ])

    headers = ["Product Name", "Size", "Price", "MRP", "Discount", "Delivery", "Status"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    print()


def save_report_csv(reports: list[TestReport], pincode: str, product: str) -> None:
    import csv, os
    filename = f"blinkit_zepto_{product.replace(' ', '_')}_{pincode}.csv"
    filepath = os.path.join(os.getcwd(), filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Platform", "Pincode", "Location", "Delivery Time",
                         "Product Name", "Size", "Price", "MRP", "Discount",
                         "Delivery on Card", "Available"])
        for report in reports:
            for p in report.products:
                writer.writerow([
                    report.platform, report.pincode, report.location,
                    report.delivery_time, p.name, p.weight, p.price,
                    p.original_price, p.discount, p.delivery_time,
                    "Yes" if p.available else "No",
                ])
    ok(f"Saved to: {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PLATFORM RUNNERS  — each owns its own Playwright instance (thread-safe)
# ═══════════════════════════════════════════════════════════════════════════════
def _new_context(pw, headless: bool):
    browser = pw.chromium.launch(headless=headless, slow_mo=0)
    return browser, browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )


def run_blinkit(pincode: str, product: str, headless: bool) -> TestReport:
    report = TestReport(platform="Blinkit", pincode=pincode,
                        location="—", delivery_time="—", product_query=product)
    with sync_playwright() as pw:
        browser, ctx = _new_context(pw, headless)
        page = ctx.new_page()
        try:
            s = BlinkitScraper(page)
            report.location, report.delivery_time = s.set_location(pincode)
            report.products = s.search(product)
        except Exception as e:
            report.error = str(e)
            err(f"Blinkit: {e}")
        finally:
            browser.close()
    return report


def run_zepto(pincode: str, product: str, headless: bool) -> TestReport:
    report = TestReport(platform="Zepto", pincode=pincode,
                        location="—", delivery_time="—", product_query=product)
    with sync_playwright() as pw:
        browser, ctx = _new_context(pw, headless)
        page = ctx.new_page()
        try:
            s = ZeptoScraper(page)
            report.location, report.delivery_time = s.set_location(pincode)
            report.products = s.search(product)
        except Exception as e:
            report.error = str(e)
            err(f"Zepto: {e}")
        finally:
            browser.close()
    return report


# ═══════════════════════════════════════════════════════════════════════════════
#  PARALLEL RUNNER
# ═══════════════════════════════════════════════════════════════════════════════
def run_both_parallel(pincode: str, product: str, headless: bool) -> list[TestReport]:
    banner("🚀 Running Blinkit & Zepto IN PARALLEL …", Fore.YELLOW)
    order = {"Blinkit": 0, "Zepto": 1}
    results: list[Optional[TestReport]] = [None, None]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(run_blinkit, pincode, product, headless): "Blinkit",
            pool.submit(run_zepto,   pincode, product, headless): "Zepto",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[order[name]] = future.result()
                ok(f"{name} done ✓")
            except Exception as exc:
                err(f"{name} error: {exc}")
                results[order[name]] = TestReport(
                    platform=name, pincode=pincode, location="—",
                    delivery_time="—", product_query=product, error=str(exc),
                )

    return [r for r in results if r is not None]


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    parser = argparse.ArgumentParser(
        description="🛒 Grocery Delivery Agent — Blinkit & Zepto"
    )
    parser.add_argument("--platform", "-p", choices=["blinkit", "zepto", "both"],
                        default=None)
    parser.add_argument("--pincode", "-z", default=None)
    parser.add_argument("--product", "-q", default=None)
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--save-csv", action="store_true", default=False)
    args = parser.parse_args()

    print(f"\n{Fore.CYAN}{'═' * 62}")
    print(f"  🛒  Grocery Delivery Automated Testing Agent")
    print(f"      Platforms: Blinkit | Zepto")
    print(f"{'═' * 62}{Style.RESET_ALL}")

    platform = args.platform
    if not platform:
        print(f"\n{Fore.YELLOW}  Select platform:{Style.RESET_ALL}")
        print("    1. blinkit")
        print("    2. zepto")
        print("    3. both  (parallel — faster!)")
        choice = input(
            f"{Fore.CYAN}  Enter choice [1/2/3] (default: 3): {Style.RESET_ALL}"
        ).strip()
        platform = {"1": "blinkit", "2": "zepto", "3": "both"}.get(choice, "both")

    pincode = args.pincode
    if not pincode:
        pincode = input(
            f"{Fore.CYAN}  Enter pincode (default: 700063): {Style.RESET_ALL}"
        ).strip() or "700063"

    product = args.product
    if not product:
        product = input(f"{Fore.CYAN}  Enter product name: {Style.RESET_ALL}").strip()
        if not product:
            print(f"{Fore.RED}  Product name is required!{Style.RESET_ALL}")
            sys.exit(1)

    print(f"\n{Fore.GREEN}  ► Platform : {platform.capitalize()}")
    print(f"  ► Pincode  : {pincode}")
    print(f"  ► Product  : {product}")
    print(f"  ► Headless : {args.headless}{Style.RESET_ALL}\n")

    reports: list[TestReport] = []

    if platform == "both":
        reports = run_both_parallel(pincode, product, args.headless)
        for report in reports:
            print_report(report)
    elif platform == "blinkit":
        banner("Running Blinkit …", Fore.GREEN)
        r = run_blinkit(pincode, product, args.headless)
        reports.append(r)
        print_report(r)
    else:
        banner("Running Zepto …", Fore.MAGENTA)
        r = run_zepto(pincode, product, args.headless)
        reports.append(r)
        print_report(r)

    if platform == "both" and len(reports) == 2:
        banner("📊 Comparison Summary", Fore.YELLOW)
        b = next((r for r in reports if r.platform == "Blinkit"), None)
        z = next((r for r in reports if r.platform == "Zepto"), None)
        if b and z:
            comp = [
                ["Platform",       "Blinkit 🟢",    "Zepto 🔵"],
                ["Delivery Time",  b.delivery_time,  z.delivery_time],
                ["Products Found", len(b.products),  len(z.products)],
                ["In Stock",
                 sum(1 for p in b.products if p.available),
                 sum(1 for p in z.products if p.available)],
            ]
            print(tabulate(comp[1:], headers=comp[0], tablefmt="rounded_outline"))

    if args.save_csv and reports:
        save_report_csv(reports, pincode, product)

    print(f"\n{Fore.CYAN}  ✅ Testing complete!{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
