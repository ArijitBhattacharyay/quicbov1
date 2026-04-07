"""
Quicbo Backend — FastAPI with Mock Data + Hardcoded Real Product Images
"""
import uuid
import httpx
import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from rapidfuzz import fuzz
import time
import live_agent

app = FastAPI(title="Quicbo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Caches ───────────────────────────────────────────────────────────────────
_search_cache: dict = {}
_pin_cache: dict = {}

def cache_get(q, pin):
    key = f"{q.lower().strip()}::{pin.strip()}"
    if key in _search_cache:
        val, ts = _search_cache[key]
        if time.time() - ts < 600:
            return val
    return None

def cache_set(q, pin, val):
    _search_cache[f"{q.lower().strip()}::{pin.strip()}"] = (val, time.time())

# ─── Pincode Lookup ───────────────────────────────────────────────────────────
async def resolve_pincode(pincode: str) -> dict:
    if pincode in _pin_cache:
        return _pin_cache[pincode]
    try:
        async with httpx.AsyncClient(timeout=0.8) as client:
            r = await client.get(f"https://api.postalpincode.in/pincode/{pincode}")
            data = r.json()
        if data and data[0].get("Status") == "Success":
            po = data[0]["PostOffice"][0]
            result = {
                "pincode": pincode,
                "city": po.get("Division", "") or po.get("Name", ""),
                "district": po.get("District", ""),
                "state": po.get("State", ""),
                "full_label": f"{po.get('District', '')} {pincode}"
            }
            _pin_cache[pincode] = result
            return result
    except Exception as e:
        print(f"[Pincode] {e}")
    fallback = {"pincode": pincode, "city": "", "district": "", "state": "", "full_label": pincode}
    _pin_cache[pincode] = fallback
    return fallback

# ─── Real Product Image URLs (Direct Static CDNs - Extremely Fast) ────────────
# These are exact real product shots with white backgrounds (like Blinkit/Zepto)
PRODUCT_IMAGES = {
    # Amul products
    "Amul Masti Dahi 1 kg": "https://www.bigbasket.com/media/uploads/p/l/104443_6-amul-masti-dahi.jpg",
    "Amul Masti Dahi 400 g": "https://www.bigbasket.com/media/uploads/p/l/104443_6-amul-masti-dahi.jpg",
    "Amul Butter Salted 500 g": "https://www.bigbasket.com/media/uploads/p/l/104711_8-amul-butter-pasteurised.jpg",
    "Amul Butter Unsalted 100 g": "https://www.bigbasket.com/media/uploads/p/l/202685_3-amul-butter-pasteurised-unsalted.jpg",
    "Amul Gold Full Cream Milk 1 L": "https://www.bigbasket.com/media/uploads/p/l/104689_3-amul-gold-homogenised-standardised-milk.jpg",
    "Amul Taaza Toned Milk 500 ml": "https://www.bigbasket.com/media/uploads/p/l/11566_2-amul-taaza-homogenised-toned-milk.jpg",
    "Amul Processed Cheese Slices 200 g (10 slices)": "https://www.bigbasket.com/media/uploads/p/l/104618_8-amul-processed-cheese-slices.jpg",
    "Amul Pure Ghee 1 L": "https://www.bigbasket.com/media/uploads/p/l/216503_8-amul-pure-ghee.jpg",
    "Amul Kool Kafe Cold Coffee 200 ml": "https://www.bigbasket.com/media/uploads/p/l/40194883_3-amul-kool-kafe-milk-beverage.jpg",
    "Amul Fresh Paneer 200 g": "https://www.bigbasket.com/media/uploads/p/l/104444_6-amul-fresh-paneer.jpg",
    
    # Other brands
    "Mother Dairy Full Cream Milk 1 L": "https://www.bigbasket.com/media/uploads/p/l/40149454_6-mother-dairy-milk-full-cream.jpg",
    "Mother Dairy Dahi 1 kg": "https://www.bigbasket.com/media/uploads/p/l/40051871_4-mother-dairy-classic-dahi.jpg",
    "Mother Dairy Paneer 200 g": "https://www.bigbasket.com/media/uploads/p/l/40051869_4-mother-dairy-paneer.jpg",
    "Britannia Brown Bread 400 g": "https://www.bigbasket.com/media/uploads/p/l/40008544_9-britannia-100-whole-wheat-bread.jpg",
    "English Oven White Sandwich Bread 400 g": "https://www.bigbasket.com/media/uploads/p/l/40009419_6-english-oven-sandwich-bread.jpg",
    "India Gate Basmati Rice Classic 5 kg": "https://www.bigbasket.com/media/uploads/p/l/20000523_5-india-gate-basmati-rice-classic.jpg",
    "Daawat Rozana Basmati Rice 1 kg": "https://www.bigbasket.com/media/uploads/p/l/40051866_4-daawat-rozana-super-basmati-rice.jpg",
    "Aashirvaad Select Sharbati Atta 5 kg": "https://www.bigbasket.com/media/uploads/p/l/161962_6-aashirvaad-select-premium-sharbati-atta.jpg",
    "Pillsbury Chakki Fresh Atta 5 kg": "https://www.bigbasket.com/media/uploads/p/l/1214041_1-pillsbury-chakki-fresh-atta.jpg",
    "Maggi 2-Minute Noodles Masala 560 g (8 packs)": "https://www.bigbasket.com/media/uploads/p/l/266160_19-maggi-2-minute-instant-noodles-masala.jpg",
    "Maggi Masala Noodles 70 g (single pack)": "https://www.bigbasket.com/media/uploads/p/l/266160_19-maggi-2-minute-instant-noodles-masala.jpg",
    "Parle-G Original Gluco Biscuits 800 g": "https://www.bigbasket.com/media/uploads/p/l/102040_8-parle-g-biscuits-original-gluco.jpg",
    "Britannia Good Day Cashew Cookies 600 g": "https://www.bigbasket.com/media/uploads/p/l/1202864_1-britannia-good-day-cashew-cookies.jpg",
    "Fortune Sunflower Oil 1 L": "https://www.bigbasket.com/media/uploads/p/l/274145_14-fortune-sunlite-refined-sunflower-oil.jpg",
    "Saffola Gold Refined Cooking Oil 1 L": "https://www.bigbasket.com/media/uploads/p/l/104239_5-saffola-gold-refined-cooking-oil-blend-of-rice-bran-sunflower-oil.jpg",
    "Nestle A+ Slim Milk 500 ml": "https://www.bigbasket.com/media/uploads/p/l/40003056_7-nestle-a-slim-milk.jpg",
    "Fresh White Eggs 12 pieces": "https://www.bigbasket.com/media/uploads/p/l/150502_6-fresho-farm-eggs-table-tray.jpg",
    "Country Delight Free Range Eggs 6 pieces": "https://www.bigbasket.com/media/uploads/p/l/40191834_4-fresho-free-range-eggs.jpg",
    "Patanjali Cow Ghee 1 L": "https://www.bigbasket.com/media/uploads/p/l/40008982_6-patanjali-cow-ghee.jpg",
    "Sunfeast Dark Fantasy Choco Fills": "https://www.bigbasket.com/media/uploads/p/l/40099240_8-sunfeast-dark-fantasy-choco-fills.jpg",
    "Sunfeast Farmlite Digestive Biscuits": "https://www.bigbasket.com/media/uploads/p/l/40129206_4-sunfeast-farmlite-digestive-biscuits.jpg",
}
# Fast, attractive fallback images using generic Unsplash food photos
UNSPLASH_FALLBACK = {
    "dahi": "https://images.unsplash.com/photo-1590135804368-ffdb912fa84e?w=400&q=80",
    "butter": "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=400&q=80",
    "milk": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&q=80",
    "paneer": "https://images.unsplash.com/photo-1631452180519-c014fe946bc0?w=400&q=80",
    "ghee": "https://images.unsplash.com/photo-1596791244837-7f8ca311fe52?w=400&q=80",
    "rice": "https://images.unsplash.com/photo-1586201375761-83865001e8ac?w=400&q=80",
    "atta": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&q=80",
    "bread": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&q=80",
    "eggs": "https://images.unsplash.com/photo-1491524062933-cb02b5f19c43?w=400&q=80",
    "maggi": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=400&q=80",
    "biscuit": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400&q=80",
    "oil": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&q=80",
    "sunfeast": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400&q=80"
}

def get_image(name: str, quantity: str) -> str:
    """Get product image URL. Uses OFF if perfectly mapped, otherwise Unsplash fallback."""
    full_key = f"{name} {quantity}"
    if full_key in PRODUCT_IMAGES:
        return PRODUCT_IMAGES[full_key]
    if name in PRODUCT_IMAGES:
        return PRODUCT_IMAGES[name]

    name_lower = name.lower()
    # Try partial name match for OFF
    for key, url in PRODUCT_IMAGES.items():
        if name_lower in key.lower() or key.lower().split(" ")[0:3] == name_lower.split(" ")[0:3]:
            return url

    # Default to absolutely gorgeous Unsplash images based on category keyword
    for key, url in UNSPLASH_FALLBACK.items():
        if key in name_lower:
            return url

    return "https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&q=80" # Beautiful generic grocery image


# ─── Mock Product Database ────────────────────────────────────────────────────
MOCK_DB = {
    "amul": [
        {"name": "Amul Masti Dahi",         "quantity": "1 kg",
         "emoji": "🍶",
         "platforms": {
             "blinkit":   {"price": 65,  "delivery": 20, "available": True},
             "zepto":     {"price": 63,  "delivery": 14, "available": True},
             "instamart": {"price": 67,  "delivery": 18, "available": True},
             "bigbasket": {"price": 62,  "delivery": 25, "available": True},
         }},
        {"name": "Amul Masti Dahi",         "quantity": "400 g",
         "emoji": "🍶",
         "platforms": {
             "blinkit":   {"price": 30,  "delivery": 20, "available": True},
             "zepto":     {"price": 28,  "delivery": 14, "available": True},
             "instamart": {"price": 31,  "delivery": 18, "available": False},
             "bigbasket": {"price": 29,  "delivery": 25, "available": True},
         }},
        {"name": "Amul Butter Salted",      "quantity": "500 g",
         "emoji": "🧈",
         "platforms": {
             "blinkit":   {"price": 285, "delivery": 20, "available": True},
             "zepto":     {"price": 282, "delivery": 14, "available": True},
             "instamart": {"price": 288, "delivery": 18, "available": True},
             "bigbasket": {"price": 279, "delivery": 25, "available": True},
         }},
        {"name": "Amul Gold Full Cream Milk","quantity": "1 L",
         "emoji": "🥛",
         "platforms": {
             "blinkit":   {"price": 68,  "delivery": 20, "available": True},
             "zepto":     {"price": 66,  "delivery": 14, "available": True},
             "instamart": {"price": 70,  "delivery": 18, "available": True},
             "bigbasket": {"price": 67,  "delivery": 25, "available": False},
         }},
        {"name": "Amul Taaza Toned Milk",   "quantity": "500 ml",
         "emoji": "🥛",
         "platforms": {
             "blinkit":   {"price": 28,  "delivery": 20, "available": True},
             "zepto":     {"price": 27,  "delivery": 14, "available": True},
             "instamart": {"price": 29,  "delivery": 18, "available": True},
             "bigbasket": {"price": 27,  "delivery": 25, "available": True},
         }},
        {"name": "Amul Processed Cheese Slices","quantity": "200 g (10 slices)",
         "emoji": "🧀",
         "platforms": {
             "blinkit":   {"price": 120, "delivery": 20, "available": True},
             "zepto":     {"price": 118, "delivery": 14, "available": True},
             "instamart": {"price": 122, "delivery": 18, "available": False},
             "bigbasket": {"price": 115, "delivery": 25, "available": True},
         }},
        {"name": "Amul Pure Ghee",          "quantity": "1 L",
         "emoji": "🫙",
         "platforms": {
             "blinkit":   {"price": 620, "delivery": 20, "available": True},
             "zepto":     {"price": 605, "delivery": 14, "available": True},
             "instamart": {"price": 615, "delivery": 18, "available": True},
             "bigbasket": {"price": 598, "delivery": 25, "available": True},
         }},
        {"name": "Amul Fresh Paneer",       "quantity": "200 g",
         "emoji": "🧀",
         "platforms": {
             "blinkit":   {"price": 95,  "delivery": 20, "available": True},
             "zepto":     {"price": 92,  "delivery": 14, "available": True},
             "instamart": {"price": 97,  "delivery": 18, "available": True},
             "bigbasket": {"price": 89,  "delivery": 25, "available": True},
         }},
        {"name": "Amul Kool Kafe Cold Coffee","quantity": "200 ml",
         "emoji": "☕",
         "platforms": {
             "blinkit":   {"price": 30,  "delivery": 20, "available": True},
             "zepto":     {"price": 28,  "delivery": 14, "available": True},
             "instamart": {"price": 30,  "delivery": 18, "available": True},
             "bigbasket": {"price": 29,  "delivery": 25, "available": False},
         }},
        {"name": "Amul Butter Unsalted",    "quantity": "100 g",
         "emoji": "🧈",
         "platforms": {
             "blinkit":   {"price": 58,  "delivery": 20, "available": True},
             "zepto":     {"price": 55,  "delivery": 14, "available": True},
             "instamart": {"price": 60,  "delivery": 18, "available": True},
             "bigbasket": {"price": 54,  "delivery": 25, "available": True},
         }},
    ],
    "milk": [
        {"name": "Amul Gold Full Cream Milk","quantity": "1 L",
         "emoji": "🥛",
         "platforms": {
             "blinkit":   {"price": 68,  "delivery": 20, "available": True},
             "zepto":     {"price": 66,  "delivery": 14, "available": True},
             "instamart": {"price": 70,  "delivery": 18, "available": True},
             "bigbasket": {"price": 67,  "delivery": 25, "available": True},
         }},
        {"name": "Mother Dairy Full Cream Milk","quantity": "1 L",
         "emoji": "🥛",
         "platforms": {
             "blinkit":   {"price": 65,  "delivery": 20, "available": True},
             "zepto":     {"price": 63,  "delivery": 14, "available": True},
             "instamart": {"price": 67,  "delivery": 18, "available": True},
             "bigbasket": {"price": 64,  "delivery": 25, "available": True},
         }},
        {"name": "Nestle A+ Slim Milk",     "quantity": "500 ml",
         "emoji": "🥛",
         "platforms": {
             "blinkit":   {"price": 36,  "delivery": 20, "available": True},
             "zepto":     {"price": 34,  "delivery": 14, "available": True},
             "instamart": {"price": 37,  "delivery": 18, "available": False},
             "bigbasket": {"price": 33,  "delivery": 25, "available": True},
         }},
    ],
    "bread": [
        {"name": "Britannia Brown Bread",   "quantity": "400 g",
         "emoji": "🍞",
         "platforms": {
             "blinkit":   {"price": 44,  "delivery": 20, "available": True},
             "zepto":     {"price": 42,  "delivery": 14, "available": True},
             "instamart": {"price": 45,  "delivery": 18, "available": True},
             "bigbasket": {"price": 41,  "delivery": 25, "available": True},
         }},
        {"name": "English Oven White Sandwich Bread","quantity": "400 g",
         "emoji": "🍞",
         "platforms": {
             "blinkit":   {"price": 40,  "delivery": 20, "available": True},
             "zepto":     {"price": 38,  "delivery": 14, "available": True},
             "instamart": {"price": 42,  "delivery": 18, "available": True},
             "bigbasket": {"price": 37,  "delivery": 25, "available": True},
         }},
    ],
    "eggs": [
        {"name": "Fresh White Eggs",        "quantity": "12 pieces",
         "emoji": "🥚",
         "platforms": {
             "blinkit":   {"price": 84,  "delivery": 20, "available": True},
             "zepto":     {"price": 80,  "delivery": 14, "available": True},
             "instamart": {"price": 86,  "delivery": 18, "available": True},
             "bigbasket": {"price": 79,  "delivery": 25, "available": True},
         }},
        {"name": "Country Delight Free Range Eggs","quantity": "6 pieces",
         "emoji": "🥚",
         "platforms": {
             "blinkit":   {"price": 60,  "delivery": 20, "available": True},
             "zepto":     {"price": 57,  "delivery": 14, "available": True},
             "instamart": {"price": 62,  "delivery": 18, "available": False},
             "bigbasket": {"price": 56,  "delivery": 25, "available": True},
         }},
    ],
    "butter": [
        {"name": "Amul Butter Salted",      "quantity": "500 g",
         "emoji": "🧈",
         "platforms": {
             "blinkit":   {"price": 285, "delivery": 20, "available": True},
             "zepto":     {"price": 282, "delivery": 14, "available": True},
             "instamart": {"price": 288, "delivery": 18, "available": True},
             "bigbasket": {"price": 279, "delivery": 25, "available": True},
         }},
        {"name": "Amul Butter Unsalted",    "quantity": "100 g",
         "emoji": "🧈",
         "platforms": {
             "blinkit":   {"price": 58,  "delivery": 20, "available": True},
             "zepto":     {"price": 55,  "delivery": 14, "available": True},
             "instamart": {"price": 60,  "delivery": 18, "available": True},
             "bigbasket": {"price": 54,  "delivery": 25, "available": True},
         }},
    ],
    "rice": [
        {"name": "India Gate Basmati Rice Classic","quantity": "5 kg",
         "emoji": "🍚",
         "platforms": {
             "blinkit":   {"price": 545, "delivery": 20, "available": True},
             "zepto":     {"price": 530, "delivery": 14, "available": True},
             "instamart": {"price": 555, "delivery": 18, "available": True},
             "bigbasket": {"price": 519, "delivery": 25, "available": True},
         }},
        {"name": "Daawat Rozana Basmati Rice","quantity": "1 kg",
         "emoji": "🍚",
         "platforms": {
             "blinkit":   {"price": 98,  "delivery": 20, "available": True},
             "zepto":     {"price": 93,  "delivery": 14, "available": True},
             "instamart": {"price": 100, "delivery": 18, "available": False},
             "bigbasket": {"price": 90,  "delivery": 25, "available": True},
         }},
    ],
    "atta": [
        {"name": "Aashirvaad Select Sharbati Atta","quantity": "5 kg",
         "emoji": "🌾",
         "platforms": {
             "blinkit":   {"price": 285, "delivery": 20, "available": True},
             "zepto":     {"price": 278, "delivery": 14, "available": True},
             "instamart": {"price": 289, "delivery": 18, "available": True},
             "bigbasket": {"price": 272, "delivery": 25, "available": True},
         }},
        {"name": "Pillsbury Chakki Fresh Atta","quantity": "5 kg",
         "emoji": "🌾",
         "platforms": {
             "blinkit":   {"price": 265, "delivery": 20, "available": True},
             "zepto":     {"price": 259, "delivery": 14, "available": True},
             "instamart": {"price": 268, "delivery": 18, "available": True},
             "bigbasket": {"price": 255, "delivery": 25, "available": True},
         }},
    ],
    "curd": [
        {"name": "Amul Masti Dahi",         "quantity": "1 kg",
         "emoji": "🍶",
         "platforms": {
             "blinkit":   {"price": 65,  "delivery": 20, "available": True},
             "zepto":     {"price": 63,  "delivery": 14, "available": True},
             "instamart": {"price": 67,  "delivery": 18, "available": True},
             "bigbasket": {"price": 62,  "delivery": 25, "available": True},
         }},
        {"name": "Mother Dairy Dahi",       "quantity": "1 kg",
         "emoji": "🍶",
         "platforms": {
             "blinkit":   {"price": 62,  "delivery": 20, "available": True},
             "zepto":     {"price": 60,  "delivery": 14, "available": True},
             "instamart": {"price": 64,  "delivery": 18, "available": True},
             "bigbasket": {"price": 59,  "delivery": 25, "available": True},
         }},
    ],
    "dahi": [
        {"name": "Amul Masti Dahi",         "quantity": "1 kg",
         "emoji": "🍶",
         "platforms": {
             "blinkit":   {"price": 65,  "delivery": 20, "available": True},
             "zepto":     {"price": 63,  "delivery": 14, "available": True},
             "instamart": {"price": 67,  "delivery": 18, "available": True},
             "bigbasket": {"price": 62,  "delivery": 25, "available": True},
         }},
        {"name": "Mother Dairy Dahi",       "quantity": "1 kg",
         "emoji": "🍶",
         "platforms": {
             "blinkit":   {"price": 62,  "delivery": 20, "available": True},
             "zepto":     {"price": 60,  "delivery": 14, "available": True},
             "instamart": {"price": 64,  "delivery": 18, "available": True},
             "bigbasket": {"price": 59,  "delivery": 25, "available": True},
         }},
    ],
    "paneer": [
        {"name": "Amul Fresh Paneer",       "quantity": "200 g",
         "emoji": "🧀",
         "platforms": {
             "blinkit":   {"price": 95,  "delivery": 20, "available": True},
             "zepto":     {"price": 92,  "delivery": 14, "available": True},
             "instamart": {"price": 97,  "delivery": 18, "available": True},
             "bigbasket": {"price": 89,  "delivery": 25, "available": True},
         }},
        {"name": "Mother Dairy Paneer",     "quantity": "200 g",
         "emoji": "🧀",
         "platforms": {
             "blinkit":   {"price": 88,  "delivery": 20, "available": True},
             "zepto":     {"price": 85,  "delivery": 14, "available": True},
             "instamart": {"price": 90,  "delivery": 18, "available": False},
             "bigbasket": {"price": 82,  "delivery": 25, "available": True},
         }},
    ],
    "ghee": [
        {"name": "Amul Pure Ghee",          "quantity": "1 L",
         "emoji": "🫙",
         "platforms": {
             "blinkit":   {"price": 620, "delivery": 20, "available": True},
             "zepto":     {"price": 605, "delivery": 14, "available": True},
             "instamart": {"price": 615, "delivery": 18, "available": True},
             "bigbasket": {"price": 598, "delivery": 25, "available": True},
         }},
        {"name": "Patanjali Cow Ghee",      "quantity": "1 L",
         "emoji": "🫙",
         "platforms": {
             "blinkit":   {"price": 470, "delivery": 20, "available": True},
             "zepto":     {"price": 458, "delivery": 14, "available": True},
             "instamart": {"price": 475, "delivery": 18, "available": False},
             "bigbasket": {"price": 450, "delivery": 25, "available": True},
         }},
    ],
    "maggi": [
        {"name": "Maggi 2-Minute Noodles Masala","quantity": "560 g (8 packs)",
         "emoji": "🍜",
         "platforms": {
             "blinkit":   {"price": 116, "delivery": 20, "available": True},
             "zepto":     {"price": 112, "delivery": 14, "available": True},
             "instamart": {"price": 118, "delivery": 18, "available": True},
             "bigbasket": {"price": 109, "delivery": 25, "available": True},
         }},
        {"name": "Maggi Masala Noodles",    "quantity": "70 g (single pack)",
         "emoji": "🍜",
         "platforms": {
             "blinkit":   {"price": 14,  "delivery": 20, "available": True},
             "zepto":     {"price": 14,  "delivery": 14, "available": True},
             "instamart": {"price": 15,  "delivery": 18, "available": True},
             "bigbasket": {"price": 14,  "delivery": 25, "available": True},
         }},
    ],
    "biscuit": [
        {"name": "Sunfeast Dark Fantasy Choco Fills", "quantity": "300 g",
         "emoji": "🍪",
         "platforms": {
             "blinkit":   {"price": 120, "delivery": 20, "available": True},
             "zepto":     {"price": 115, "delivery": 14, "available": True},
             "instamart": {"price": 118, "delivery": 18, "available": True},
             "bigbasket": {"price": 110, "delivery": 25, "available": True},
         }},
        {"name": "Sunfeast Farmlite Digestive Biscuits", "quantity": "250 g",
         "emoji": "🍪",
         "platforms": {
             "blinkit":   {"price": 60,  "delivery": 20, "available": True},
             "zepto":     {"price": 58,  "delivery": 14, "available": True},
             "instamart": {"price": 62,  "delivery": 18, "available": True},
             "bigbasket": {"price": 55,  "delivery": 25, "available": True},
         }},
        {"name": "Parle-G Original Gluco Biscuits","quantity": "800 g",
         "emoji": "🍪",
         "platforms": {
             "blinkit":   {"price": 60,  "delivery": 20, "available": True},
             "zepto":     {"price": 57,  "delivery": 14, "available": True},
             "instamart": {"price": 62,  "delivery": 18, "available": True},
             "bigbasket": {"price": 55,  "delivery": 25, "available": True},
         }},
        {"name": "Britannia Good Day Cashew Cookies","quantity": "600 g",
         "emoji": "🍪",
         "platforms": {
             "blinkit":   {"price": 79,  "delivery": 20, "available": True},
             "zepto":     {"price": 76,  "delivery": 14, "available": True},
             "instamart": {"price": 82,  "delivery": 18, "available": True},
             "bigbasket": {"price": 74,  "delivery": 25, "available": True},
         }},
    ],
    "oil": [
        {"name": "Fortune Sunflower Oil",   "quantity": "1 L",
         "emoji": "🫙",
         "platforms": {
             "blinkit":   {"price": 145, "delivery": 20, "available": True},
             "zepto":     {"price": 140, "delivery": 14, "available": True},
             "instamart": {"price": 148, "delivery": 18, "available": True},
             "bigbasket": {"price": 135, "delivery": 25, "available": True},
         }},
        {"name": "Saffola Gold Refined Cooking Oil","quantity": "1 L",
         "emoji": "🫙",
         "platforms": {
             "blinkit":   {"price": 175, "delivery": 20, "available": True},
             "zepto":     {"price": 170, "delivery": 14, "available": True},
             "instamart": {"price": 178, "delivery": 18, "available": True},
             "bigbasket": {"price": 165, "delivery": 25, "available": True},
         }},
    ],
}

# ─── Search Aliases (expand what users can search) ───────────────────────────
ALIASES = {
    "noodles":       "maggi",
    "instant noodles":"maggi",
    "biscuits":      "biscuit",
    "cookies":       "biscuit",
    "parle":         "biscuit",
    "britannia":     "bread",
    "flour":         "atta",
    "wheat":         "atta",
    "maida":         "atta",
    "yogurt":        "curd",
    "dairy":         "milk",
    "toned":         "milk",
    "full cream":    "milk",
    "sunflower":     "oil",
    "refined oil":   "oil",
    "cooking oil":   "oil",
    "mustard":       "oil",
    "saffola":       "oil",
    "fortune":       "oil",
    "chawal":        "rice",
    "basmati":       "rice",
    "anda":          "eggs",
    "egg":           "eggs",
    "cheese":        "amul",
    "cold coffee":   "amul",
    "kool":          "amul",
    "masti":         "dahi",
    "taaza":         "milk",
    "gold milk":     "milk",
    "india gate":    "rice",
    "daawat":        "rice",
    "aashirvaad":    "atta",
    "pillsbury":     "atta",
    "patanjali":     "ghee",
    "mother dairy":  "curd",
    "parle g":       "biscuit",
    "good day":      "biscuit",
    "nestle":        "milk",
}

PLATFORM_LABELS = {
    "blinkit":   "Blinkit",
    "zepto":     "Zepto",
    "instamart": "Swiggy Instamart",
    "bigbasket": "BigBasket",
}
PLATFORM_URLS = {
    "blinkit":   "https://blinkit.com",
    "zepto":     "https://www.zepto.com",
    "instamart": "https://www.swiggy.com/instamart",
    "bigbasket": "https://www.bigbasket.com",
}

# ─── Search Logic ─────────────────────────────────────────────────────────────
def find_products(query: str):
    q_org = query.lower().strip()
    results, seen = [], set()

    # Split query into words
    q_words = q_org.split()

    # Check aliases first
    resolved_key = ALIASES.get(q_org)
    if resolved_key and resolved_key in MOCK_DB:
        for p in MOCK_DB[resolved_key]:
            uid = f"{p['name'].lower()}::{p['quantity'].lower()}"
            if uid not in seen:
                seen.add(uid)
                results.append(p)

    # Fuzzy match aliases using token_set_ratio which is much safer for exact word boundaries
    for alias, target_key in ALIASES.items():
        if fuzz.token_set_ratio(q_org, alias) >= 85 and target_key in MOCK_DB:
            for p in MOCK_DB[target_key]:
                uid = f"{p['name'].lower()}::{p['quantity'].lower()}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(p)

    # Direct key exact word match
    for key, products in MOCK_DB.items():
        # Only match if the key is explicitly found inside the query words or query inside key
        if key in q_words or any(w in key for w in q_words) or fuzz.token_set_ratio(q_org, key) >= 85:
            for p in products:
                uid = f"{p['name'].lower()}::{p['quantity'].lower()}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(p)

    # Product name match
    # Instead of partial_ratio which causes "oil" to match "amul gold full cream milk" (because it has o, i, l in order),
    # we use simple subset matching and token_set_ratio.
    for key, products in MOCK_DB.items():
        for p in products:
            uid = f"{p['name'].lower()}::{p['quantity'].lower()}"
            if uid in seen:
                continue
            p_name_lower = p["name"].lower()
            
            # Strong match: all query words are present in the product name
            if all(w in p_name_lower for w in q_words) or fuzz.token_set_ratio(q_org, p_name_lower) >= 85:
                seen.add(uid)
                results.append(p)

    return results


def build_response(products, query, pincode, location, cached=False):
    out = []
    for p in products:
        raw_img = get_image(p["name"], p["quantity"])
        # Wrap via proxy so images are cached on localhost (fast after first load)
        img = f"/api/image?url={urllib.parse.quote(raw_img, safe='')}" if raw_img else ""
        offers = []
        for platform, data in p["platforms"].items():
            offers.append({
                "platform": platform,
                "platform_label": PLATFORM_LABELS[platform],
                "price": data["price"] if data["available"] else None,
                "delivery_time": data["delivery"] if data["available"] else None,
                "delivery_label": f"{data['delivery']} mins" if data["available"] else "Not Available",
                "available": data["available"],
                "product_url": PLATFORM_URLS[platform],
                "raw_name": p["name"],
            })
        available = sorted([o for o in offers if o["available"]], key=lambda x: (x["price"] or 9999, x["delivery_time"] or 999))
        unavailable = [o for o in offers if not o["available"]]
        out.append({
            "id": str(uuid.uuid4()),
            "name": p["name"],
            "image_url": img,
            "quantity": p["quantity"],
            "emoji": p.get("emoji", "🛒"),
            "best_offer": available[0] if available else None,
            "all_offers": available + unavailable,
        })
    return {"query": query, "pincode": pincode, "location": location,
            "products": out, "total": len(out), "cached": cached}


# ─── Image Proxy (caches images from OFF CDN, serves from localhost) ─────────
_image_cache: dict = {}  # url -> bytes
import urllib.parse
from fastapi.responses import Response

@app.get("/api/image")
async def proxy_image(url: str = Query(...)):
    """Proxy and cache product images from OFF CDN. Serves from memory after first fetch."""
    if url in _image_cache:
        return Response(content=_image_cache[url], media_type="image/jpeg",
                       headers={"Cache-Control": "public, max-age=86400"})
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 Quicbo/1.0"})
            if r.status_code == 200 and len(r.content) > 500:
                ct = r.headers.get("content-type", "image/jpeg")
                _image_cache[url] = r.content
                return Response(content=r.content, media_type=ct,
                               headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        print(f"[Image proxy] {url[:60]} → {e}")
    raise HTTPException(404, "Image unavailable")


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Quicbo API", "version": "1.0.0"}


@app.get("/api/pincode/{pincode}")
async def get_pincode(pincode: str):
    if not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(400, "Invalid pincode — must be 6 digits")
    return await resolve_pincode(pincode)


@app.get("/api/search")
async def search_api(
    q: str = Query(..., min_length=1),
    pincode: str = Query(..., min_length=6, max_length=6),
):
    if not pincode.isdigit():
        raise HTTPException(400, "Pincode must be numeric")

    # For speed during repeat testing
    cached = cache_get(q, pincode)
    if cached:
        cached["cached"] = True
        return JSONResponse(content=cached)

    try:
        loc = await asyncio.wait_for(resolve_pincode(pincode), timeout=1.0)
        location_label = loc.get("full_label", pincode)
    except Exception:
        location_label = pincode

    # ── LIVE SCRAPING (ACCURATE DATA) ──
    print(f"[LIVE SEARCH] Running 4 scrapers for: {q} at {pincode}")
    reports = await asyncio.to_thread(live_agent.run_all_parallel, pincode, q)
    
    # ── AGGREGATE RESULTS ──
    grouped_products = []
    
    for report in reports:
        plat_lower = report.platform.lower()  # "blinkit" or "zepto"
        for p in report.products:
            # Fuzzy match to group same products across platforms
            matched = False
            for g in grouped_products:
                if fuzz.token_set_ratio(g["name"].lower(), p.name.lower()) > 85 and g["quantity"] == p.weight:
                    g["platforms"][plat_lower] = {
                        "price": p.price,
                        "delivery": p.delivery_time,
                        "available": p.available
                    }
                    if not g["image"] and p.image:
                        g["image"] = p.image
                    matched = True
                    break
            
            if not matched:
                new_group = {
                    "name": p.name,
                    "quantity": p.weight,
                    "image": p.image,
                    "emoji": "🛒",
                    "platforms": {
                        "blinkit": {"price": 0, "delivery": 0, "available": False},
                        "zepto": {"price": 0, "delivery": 0, "available": False},
                        "instamart": {"price": 0, "delivery": 0, "available": False},
                        "bigbasket": {"price": 0, "delivery": 0, "available": False},
                    }
                }
                new_group["platforms"][plat_lower] = {
                    "price": p.price,
                    "delivery": p.delivery_time,
                    "available": p.available
                }
                grouped_products.append(new_group)

    # ── BUILD API RESPONSE ──
    out = []
    for g in grouped_products:
        offers = []
        for platform_id, data in g["platforms"].items():
            offers.append({
                "platform": platform_id,
                "platform_label": PLATFORM_LABELS.get(platform_id, platform_id.capitalize()),
                "price": data["price"] if data["available"] else None,
                "delivery_time": data["delivery"] if data["available"] else None,
                "delivery_label": f"{data['delivery']} mins" if data["available"] else "Not Available",
                "available": data["available"],
                "product_url": PLATFORM_URLS.get(platform_id, ""),
                "raw_name": g["name"],
            })
            
        available_offers = sorted([o for o in offers if o["available"]], key=lambda x: (x["price"] or 9999, x["delivery_time"] or 999))
        unavailable_offers = [o for o in offers if not o["available"]]
        
        # Determine actual image: Try to use scraper image, otherwise use get_image fallback
        final_img_url = g.get("image", "")
        if not final_img_url or len(final_img_url) < 10:
            raw_fallback = get_image(g["name"], g["quantity"])
            if raw_fallback:
                final_img_url = raw_fallback

        encoded_img_url = f"/api/image?url={urllib.parse.quote(final_img_url, safe='')}" if final_img_url else ""
        
        out.append({
            "id": str(uuid.uuid4()),
            "name": g["name"],
            "image_url": encoded_img_url,
            "quantity": g["quantity"],
            "emoji": g["emoji"],
            "best_offer": available_offers[0] if available_offers else None,
            "all_offers": available_offers + unavailable_offers,
        })

    response = {
        "query": q,
        "pincode": pincode,
        "location": location_label,
        "products": out,
        "total": len(out),
        "cached": False
    }
    
    cache_set(q, pincode, response)
    return JSONResponse(content=response)


@app.get("/api/platforms")
async def platforms():
    return {"platforms": [
        {"id": "blinkit",   "label": "Blinkit",         "color": "#F8D000", "url": "https://blinkit.com"},
        {"id": "zepto",     "label": "Zepto",            "color": "#8025FB", "url": "https://www.zepto.com"},
        {"id": "instamart", "label": "Swiggy Instamart", "color": "#FC8019", "url": "https://www.swiggy.com/instamart"},
        {"id": "bigbasket", "label": "BigBasket",        "color": "#84B527", "url": "https://www.bigbasket.com"},
    ]}
