"""
In-memory TTL cache for search results.
Caches results for 10 minutes per (query, pincode) pair.
"""
import time
from typing import Any, Optional, Dict, Tuple

CACHE_TTL_SECONDS = 600  # 10 minutes


class TTLCache:
    def __init__(self, ttl: int = CACHE_TTL_SECONDS):
        self.ttl = ttl
        self._store: Dict[str, Tuple[Any, float]] = {}

    def _make_key(self, query: str, pincode: str) -> str:
        return f"{query.lower().strip()}::{pincode.strip()}"

    def get(self, query: str, pincode: str) -> Optional[Any]:
        key = self._make_key(query, pincode)
        if key in self._store:
            value, ts = self._store[key]
            if time.time() - ts < self.ttl:
                return value
            else:
                del self._store[key]
        return None

    def set(self, query: str, pincode: str, value: Any):
        key = self._make_key(query, pincode)
        self._store[key] = (value, time.time())

    def clear(self):
        self._store.clear()

    def size(self) -> int:
        # Cleanup expired
        now = time.time()
        expired = [k for k, (_, ts) in self._store.items() if now - ts >= self.ttl]
        for k in expired:
            del self._store[k]
        return len(self._store)


# Global cache instance
cache = TTLCache()
