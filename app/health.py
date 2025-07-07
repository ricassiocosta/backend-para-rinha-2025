import httpx, asyncio, time
from datetime import datetime
from app.config import get_settings

settings = get_settings()

_cache = {}
_lock = asyncio.Lock()
_CACHE_KEY = "gateway_status"

def is_cache_valid(timestamp: float) -> bool:
    """Check if the cache entry is still valid based on the TTL."""
    return (datetime.now().timestamp() - timestamp) < settings.health_cache_ttl

async def get_health(url: str) -> dict:
    async with httpx.AsyncClient(timeout=1.5) as client:
        try:
            print(f"Checking health of {url} at {datetime.now()}")
            resp = await client.get(f"{url}/payments/service-health")
            data = resp.json()
        except Exception:
            data = {"failing": True, "minResponseTime": 10_000}

        return data

async def get_healthier_gateway() -> tuple[str, str]:
    async with _lock:
        saved = _cache.get(_CACHE_KEY)
        if saved and is_cache_valid(saved["ts"]):
            return saved["data"]
        
        # default_health, fallback_health = await asyncio.gather(
        #     get_health(settings.pp_default),
        #     get_health(settings.pp_fallback)
        # )

        # if not default_health["failing"] and default_health["minResponseTime"] <= fallback_health["minResponseTime"]:
        #     _cache[_CACHE_KEY] = {"data": default_health, "ts": datetime.now().timestamp()}
        #     return settings.pp_default, "default"
        
        # _cache[_CACHE_KEY] = {"data": fallback_health, "ts": datetime.now().timestamp()}
        # return settings.pp_fallback, "fallback"

        default_health = await get_health(settings.pp_default)

        if not default_health["failing"] and default_health["minResponseTime"] <= settings.pp_timeout_ms:
            _cache[_CACHE_KEY] = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
            return settings.pp_default, "default"
        
        return settings.pp_fallback, "fallback"
