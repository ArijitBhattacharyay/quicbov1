"""
Product name normalizer and fuzzy matcher.
Groups products from different platforms that refer to the same item.
Uses rapidfuzz for similarity scoring (no API key needed).
"""
import re
import uuid
from typing import List, Dict, Tuple
from rapidfuzz import fuzz, process

from normalizer.models import PlatformOffer, ProductResult

# Words to strip during normalization
FILLER_WORDS = {
    "fresh", "new", "pure", "organic", "natural", "special", "premium",
    "pack", "pouch", "bottle", "tub", "jar", "bag", "box", "sachet",
    "buy", "get", "offer", "combo"
}

# Unit synonyms map
UNIT_MAP = {
    "litre": "l", "liter": "l", "liters": "l", "litres": "l",
    "kilogram": "kg", "kilograms": "kg", "kgs": "kg",
    "gram": "g", "grams": "g", "gm": "g", "gms": "g",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml",
    "piece": "pc", "pieces": "pc", "pcs": "pc", "packet": "pkt", "packets": "pkt",
}

# Known product synonyms (platform-specific names → canonical name)
SYNONYM_MAP = {
    "dahi": "curd",
    "lassi": "lassi",
    "paneer": "paneer",
    "ghee": "ghee",
    "atta": "atta",
    "maida": "maida",
    "dal": "dal",
    "chawal": "rice",
}


def normalize_name(name: str) -> str:
    """Normalize a product name for comparison."""
    name = name.lower().strip()
    # Replace quantity patterns like "1 kg", "500g", "1.5l"
    name = re.sub(r'\d+\.?\d*\s*(kg|g|gm|gms|gram|grams|l|ltr|litre|litres|liter|ml|pc|pcs|pkt)', '', name)
    # Apply synonym map
    for src, tgt in SYNONYM_MAP.items():
        name = re.sub(r'\b' + src + r'\b', tgt, name)
    # Apply unit map
    for src, tgt in UNIT_MAP.items():
        name = re.sub(r'\b' + src + r'\b', tgt, name)
    # Remove filler words
    words = name.split()
    words = [w for w in words if w not in FILLER_WORDS]
    name = " ".join(words)
    # Remove special chars except alphanumeric and spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_quantity(name: str) -> str:
    """Extract quantity from product name."""
    match = re.search(r'(\d+\.?\d*\s*(kg|g|gm|gms|l|ltr|litre|ml|pc|pcs|pkt))', name, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return ""


def group_products(platform_results: Dict[str, List[dict]]) -> List[ProductResult]:
    """
    Group products from different platforms into unified product cards.
    
    platform_results: {
        "blinkit": [{"name": ..., "price": ..., "image": ..., "delivery_time": ..., "url": ...}],
        "zepto": [...],
        ...
    }
    """
    PLATFORM_LABELS = {
        "blinkit": "Blinkit",
        "zepto": "Zepto",
        "instamart": "Swiggy Instamart",
        "bigbasket": "BigBasket",
    }

    # Flatten all products with platform info
    all_items = []
    for platform, items in platform_results.items():
        for item in items:
            all_items.append({
                **item,
                "platform": platform,
                "platform_label": PLATFORM_LABELS.get(platform, platform),
                "normalized": normalize_name(item.get("name", "")),
                "quantity": item.get("quantity", "") or extract_quantity(item.get("name", "")),
            })

    if not all_items:
        return []

    # Cluster similar products
    groups: List[List[dict]] = []
    used = set()

    for i, item in enumerate(all_items):
        if i in used:
            continue
        group = [item]
        used.add(i)
        for j, other in enumerate(all_items):
            if j in used or j == i:
                continue
            # Don't group same platform twice per group
            if any(g["platform"] == other["platform"] for g in group):
                continue
            score = fuzz.token_sort_ratio(item["normalized"], other["normalized"])
            
            # Optimization: Ensure core tokens from the shorter string are present in the longer one
            # to prevent brand-mismatch groupings for similar products (e.g., Milk vs Silk)
            item_tokens = set(item["normalized"].split())
            other_tokens = set(other["normalized"].split())
            intersection = item_tokens.intersection(other_tokens)
            
            # Token intersection must be at least 60% of both to consider grouping
            token_match = len(intersection) >= (min(len(item_tokens), len(other_tokens)) * 0.6)

            if score >= 85 and token_match:
                group.append(other)
                used.add(j)
        groups.append(group)

    # Convert groups to ProductResult objects
    results = []
    for group in groups:
        # Pick best name (longest normalized original name)
        best_item = max(group, key=lambda x: len(x.get("name", "")))
        display_name = _clean_display_name(best_item.get("name", "Unknown Product"))
        
        # Build offers for each platform
        all_offers = []
        for item in group:
            price = item.get("price")
            delivery_time = item.get("delivery_time")
            offer = PlatformOffer(
                platform=item["platform"],
                platform_label=item["platform_label"],
                price=price,
                original_price=item.get("original_price"),
                delivery_time=delivery_time,
                delivery_label=f"{delivery_time} mins" if delivery_time else "N/A",
                available=True,
                product_url=item.get("url", ""),
                raw_name=item.get("name", ""),
            )
            all_offers.append(offer)

        # Add "Not Available" for missing platforms
        all_platforms = set(PLATFORM_LABELS.keys())
        present_platforms = {o.platform for o in all_offers}
        for missing in all_platforms - present_platforms:
            all_offers.append(PlatformOffer(
                platform=missing,
                platform_label=PLATFORM_LABELS[missing],
                available=False,
                delivery_label="Not Available",
            ))

        # Sort offers: available first, then by price
        available_offers = [o for o in all_offers if o.available and o.price is not None]
        unavailable_offers = [o for o in all_offers if not o.available]
        available_offers.sort(key=lambda x: (x.price or 9999, x.delivery_time or 9999))

        best_offer = available_offers[0] if available_offers else None

        product = ProductResult(
            id=str(uuid.uuid4()),
            name=display_name,
            image_url=best_item.get("image", ""),
            quantity=best_item.get("quantity", ""),
            best_offer=best_offer,
            all_offers=available_offers + unavailable_offers,
        )
        results.append(product)

    # Sort by number of platforms available (most popular first)
    results.sort(key=lambda p: sum(1 for o in p.all_offers if o.available), reverse=True)
    return results


def _clean_display_name(name: str) -> str:
    """Make a clean display name from raw product name."""
    # Capitalize properly
    return " ".join(word.capitalize() for word in name.strip().split())
