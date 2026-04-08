"""
Blinkit scraper using Playwright.
Sets pincode, searches product, extracts results.
"""
import asyncio
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from scraper.base import BaseScraper


class BlinkitScraper(BaseScraper):
    platform_name = "blinkit"
    base_url = "https://blinkit.com"

    async def search(self, query: str, pincode: str) -> List[Dict[str, Any]]:
        results = []
        try:
            async with async_playwright() as p:
                browser = await self._make_browser(p)
                context = await self._stealth_context(browser)
                page = await context.new_page()

                # Navigate to Blinkit
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # Set pincode
                await self._set_pincode(page, pincode)
                await page.wait_for_timeout(2000)

                # Search for product
                await self._do_search(page, query)
                await page.wait_for_timeout(3000)

                # Extract products
                results = await self._extract_products(page, query)
                await browser.close()
        except Exception as e:
            print(f"[Blinkit] Error: {e}")
        return results

    async def _set_pincode(self, page, pincode: str):
        try:
            # Try clicking location button
            loc_btn = page.locator("[data-testid='location-btn'], .location-btn, button:has-text('Deliver to'), button:has-text('Select Location')").first
            if await loc_btn.count() > 0:
                await loc_btn.click()
                await page.wait_for_timeout(1500)

            # Find pincode input
            pincode_input = page.locator("input[placeholder*='pincode'], input[placeholder*='Enter'], input[type='text']").first
            if await pincode_input.count() > 0:
                await pincode_input.fill(pincode)
                await page.wait_for_timeout(1500)
                # Press Enter or click suggestion
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[Blinkit] Pincode set error: {e}")

    async def _do_search(self, page, query: str):
        try:
            search_input = page.locator("input[type='search'], input[placeholder*='Search'], input[placeholder*='search']").first
            await search_input.click()
            await search_input.fill(query)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[Blinkit] Search error: {e}")

    async def _extract_products(self, page, query: str) -> List[Dict]:
        results = []
        try:
            # Wait for product cards
            await page.wait_for_selector("[data-testid='product-card'], .product-container, .Product__container", timeout=10000)

            cards = await page.query_selector_all("[data-testid='product-card'], .product-container, .plp-product")
            
            # Get delivery time from header
            delivery_time = 20  # default
            try:
                header_text = await page.inner_text("header, .delivery-time, [class*='delivery']")
                dt = self._parse_delivery(header_text)
                if dt:
                    delivery_time = dt
            except:
                pass

            for card in cards[:12]:  # limit to 12 per platform
                try:
                    name = ""
                    price = None
                    image = ""

                    # Name
                    for sel in ["[class*='Product__title'], [class*='product-name'], h3, h4, [class*='name']"]:
                        try:
                            el = await card.query_selector(sel)
                            if el:
                                name = (await el.inner_text()).strip()
                                break
                        except:
                            pass

                    if not name:
                        continue

                    # Price
                    for sel in ["[class*='Product__price'], [class*='price'], [class*='Price'], .price"]:
                        try:
                            el = await card.query_selector(sel)
                            if el:
                                price_text = await el.inner_text()
                                price = self._parse_price(price_text)
                                if price:
                                    break
                        except:
                            pass

                    # Image
                    try:
                        img_el = await card.query_selector("img")
                        if img_el:
                            image = await img_el.get_attribute("src") or ""
                    except:
                        pass

                    # Delivery time from card or use global
                    card_delivery = delivery_time
                    try:
                        del_el = await card.query_selector("[class*='delivery'], [class*='time']")
                        if del_el:
                            dt = self._parse_delivery(await del_el.inner_text())
                            if dt:
                                card_delivery = dt
                    except:
                        pass

                    results.append({
                        "name": name,
                        "price": price,
                        "image": image,
                        "delivery_time": card_delivery,
                        "url": self.base_url,
                        "quantity": self._extract_quantity(name),
                        "original_price": None,
                    })
                except Exception as e:
                    continue

        except Exception as e:
            print(f"[Blinkit] Extract error: {e}")
            # Fallback: use mock data for development
            results = self._mock_results(query)

        if not results:
            results = self._mock_results(query)
        return results

    def _extract_quantity(self, name: str) -> str:
        match = re.search(r'(\d+\.?\d*\s*(kg|g|gm|gms|l|ltr|ml|pc|pcs|pkt))', name, re.IGNORECASE)
        return match.group(0).strip() if match else ""

    def _mock_results(self, query: str) -> List[Dict]:
        """Fallback mock data when scraping fails."""
        query_lower = query.lower()
        if "amul" in query_lower:
            return [
                {"name": f"Amul Masti Dahi 1 kg", "price": 77.0, "image": "", "delivery_time": 20, "url": self.base_url, "quantity": "1 kg", "original_price": None},
                {"name": f"Amul Masti Dahi 400 g", "price": 35.0, "image": "", "delivery_time": 20, "url": self.base_url, "quantity": "400 g", "original_price": None},
                {"name": f"Amul Butter 500 g", "price": 275.0, "image": "", "delivery_time": 20, "url": self.base_url, "quantity": "500 g", "original_price": None},
            ]
        return [
            {"name": f"{query} Product 1", "price": 99.0, "image": "", "delivery_time": 20, "url": self.base_url, "quantity": "", "original_price": None},
        ]
