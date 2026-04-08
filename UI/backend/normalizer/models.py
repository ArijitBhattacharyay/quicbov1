from pydantic import BaseModel
from typing import List, Optional


class PlatformOffer(BaseModel):
    platform: str          # "blinkit", "zepto", "instamart", "bigbasket"
    platform_label: str    # "Blinkit", "Zepto", "Swiggy Instamart", "BigBasket"
    price: Optional[float] = None
    original_price: Optional[float] = None
    delivery_time: Optional[int] = None   # minutes
    delivery_label: str = ""              # e.g. "27 mins"
    available: bool = False
    product_url: str = ""
    raw_name: str = ""                    # Original name from site


class ProductResult(BaseModel):
    id: str
    name: str              # Normalized display name
    image_url: str = ""
    category: str = ""
    quantity: str = ""     # e.g. "1 kg", "500 g"
    best_offer: Optional[PlatformOffer] = None
    all_offers: List[PlatformOffer] = []


class SearchResponse(BaseModel):
    query: str
    pincode: str
    location: str
    products: List[ProductResult]
    total: int
    cached: bool = False


class PincodeResponse(BaseModel):
    pincode: str
    city: str
    district: str
    state: str
    full_label: str
