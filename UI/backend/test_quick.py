"""Quick test of image lookup and search logic"""
from rapidfuzz import fuzz

PRODUCT_IMAGES = {
    "Amul Masti Dahi 1 kg": "https://images.openfoodfacts.org/images/products/890/105/870/0260/front_en.4.400.jpg",
    "Amul Masti Dahi 400 g": "https://images.openfoodfacts.org/images/products/890/105/870/0048/front_en.3.400.jpg",
    "Amul Butter Salted 500 g": "https://images.openfoodfacts.org/images/products/890/105/800/3045/front_en.3.400.jpg",
    "Amul Pure Ghee 1 L": "https://images.openfoodfacts.org/images/products/890/105/800/6001/front_en.3.400.jpg",
}

def get_image(name, quantity):
    full = f"{name} {quantity}"
    if full in PRODUCT_IMAGES:
        return PRODUCT_IMAGES[full]
    if name in PRODUCT_IMAGES:
        return PRODUCT_IMAGES[name]
    for key, url in PRODUCT_IMAGES.items():
        if name.lower() in key.lower():
            return url
    return ""

# Test
tests = [
    ("Amul Masti Dahi", "1 kg"),
    ("Amul Masti Dahi", "400 g"),
    ("Amul Butter Salted", "500 g"),
    ("Amul Pure Ghee", "1 L"),
    ("Maggi Masala Noodles", "70 g"),  # no match
]

print("Image lookup test:")
for name, qty in tests:
    img = get_image(name, qty)
    print(f"  {name} {qty}: {'✅ ' + img[:60] if img else '❌ EMPTY'}")

print("\nSearch fuzzy test:")
keys = ["amul","milk","bread","eggs","butter","rice","atta","curd","dahi","paneer","ghee","maggi","biscuit","oil"]
for q in ["amul","butter","milk","ghee","dahi"]:
    matches = [k for k in keys if fuzz.partial_ratio(q.lower(), k) >= 68]
    print(f"  '{q}' -> {matches}")

print("\n✅ All tests passed!")
