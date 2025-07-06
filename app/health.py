import httpx, asyncio, time
from app.config import get_settings

settings = get_settings()

_cache = {}
_lock = asyncio.Lock()

async def get_health(url: str) -> dict:
    async with _lock:
        saved = _cache.get(url)
        if saved and time.time() - saved["ts"] < settings.health_cache_ttl:
            return saved["data"]

    async with httpx.AsyncClient(timeout=1.5) as client:
        try:
            resp = await client.get(f"{url}/payments/service-health")
            data = resp.json()
        except Exception:
            data = {"failing": True, "minResponseTime": 10_000}

    async with _lock:
        _cache[url] = {"data": data, "ts": time.time()}
    return data
