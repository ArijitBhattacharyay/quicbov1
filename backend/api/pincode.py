"""
Pincode resolver using api.postalpincode.in (free Indian pincode API).
"""
import httpx
from typing import Optional
from normalizer.models import PincodeResponse

PINCODE_API = "https://api.postalpincode.in/pincode/{}"

# Simple cache for pincode lookups
_pincode_cache: dict = {}


async def resolve_pincode(pincode: str) -> PincodeResponse:
    """Resolve an Indian pincode to city/district/state info."""
    pincode = pincode.strip()
    
    if pincode in _pincode_cache:
        return _pincode_cache[pincode]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(PINCODE_API.format(pincode))
            data = resp.json()

        if data and data[0].get("Status") == "Success":
            post_offices = data[0].get("PostOffice", [])
            if post_offices:
                po = post_offices[0]
                city = po.get("Division", "") or po.get("Name", "")
                district = po.get("District", "")
                state = po.get("State", "")
                result = PincodeResponse(
                    pincode=pincode,
                    city=city,
                    district=district,
                    state=state,
                    full_label=f"{district} {pincode}"
                )
                _pincode_cache[pincode] = result
                return result
    except Exception as e:
        print(f"[Pincode] Error resolving {pincode}: {e}")

    # Fallback
    return PincodeResponse(
        pincode=pincode,
        city="Your Location",
        district="",
        state="",
        full_label=pincode
    )
