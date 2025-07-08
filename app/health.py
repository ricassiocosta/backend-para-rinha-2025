import redis.asyncio as aioredis
import json
from app.config import get_settings
from datetime import datetime

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True)
_CACHE_KEY = "gateway_status"
_LOCAL_CACHE = {}

def is_cache_valid(ts: float) -> bool:
    now = datetime.now().timestamp()
    return (ts + settings.health_cache_ttl) > now

async def get_healthier_gateway() -> tuple[str, str]:
    cached = _LOCAL_CACHE.get(_CACHE_KEY)
    if cached:
        if is_cache_valid(cached["ts"]):
            return tuple(cached["data"])
    cached = await redis.get(_CACHE_KEY)
    if cached:
        try:
            cached_obj = json.loads(cached)
            if is_cache_valid(cached_obj["ts"]):
                _LOCAL_CACHE[_CACHE_KEY] = cached_obj
                return tuple(cached_obj["data"])
        except Exception:
            pass
    raise RuntimeError("No valid gateway health data in cache")
