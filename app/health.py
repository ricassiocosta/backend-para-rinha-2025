import httpx, asyncio, time
from datetime import datetime
from app.config import get_settings
import redis.asyncio as aioredis
import json
import uuid

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True)
_CACHE_KEY = "gateway_status"

def is_cache_valid(ts: float) -> bool:
    now = datetime.now().timestamp()
    return (ts + settings.health_cache_ttl) > now
async def get_health(url: str) -> dict:
    async with httpx.AsyncClient(timeout=0.5) as client:
        try:
            print(f"Checking health of {url} at {datetime.now()}")
            resp = await client.get(f"{url}/payments/service-health")
            data = resp.json()
        except Exception:
            data = {"failing": True, "minResponseTime": 10_000}

        return data

async def get_healthier_gateway() -> tuple[str, str]:
    cached = await redis.get(_CACHE_KEY)
    if cached:
        try:
            cached_obj = json.loads(cached)
            if is_cache_valid(cached_obj["ts"]):
                return tuple(cached_obj["data"])
        except Exception:
            pass

    lock_key = _CACHE_KEY + ":lock"
    lock_id = str(uuid.uuid4())
    got_lock = await redis.set(lock_key, lock_id, nx=True, ex=5) 
    if got_lock:
        try:
            cached = await redis.get(_CACHE_KEY)
            if cached:
                try:
                    cached_obj = json.loads(cached)
                    if is_cache_valid(cached_obj["ts"]):
                        return tuple(cached_obj["data"])
                except Exception:
                    pass
            default_health, fallback_health = await asyncio.gather(
                get_health(settings.pp_default),
                get_health(settings.pp_fallback)
            )

            if not default_health["failing"] and default_health["minResponseTime"] < 120:
                cache_obj = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
                await redis.set(_CACHE_KEY, json.dumps(cache_obj), ex=settings.health_cache_ttl)
                return settings.pp_default, "default"
            
            
            if fallback_health["minResponseTime"] < (default_health["minResponseTime"] * 3) :
                cache_obj = {"data": (settings.pp_fallback, "fallback"), "ts": datetime.now().timestamp()}
                await redis.set(_CACHE_KEY, json.dumps(cache_obj), ex=settings.health_cache_ttl)
                return settings.pp_fallback, "fallback"
            
            cache_obj = {"data": (settings.pp_default, "default"), "ts": datetime.now().timestamp()}
            await redis.set(_CACHE_KEY, json.dumps(cache_obj), ex=settings.health_cache_ttl)
            return settings.pp_default, "default"
        finally:
            lock_val = await redis.get(lock_key)
            if lock_val == lock_id:
                await redis.delete(lock_key)
    else:
        for _ in range(3):
            await asyncio.sleep(0.1)
            cached = await redis.get(_CACHE_KEY)
            if cached:
                try:
                    cached_obj = json.loads(cached)
                    if is_cache_valid(cached_obj["ts"]):
                        return tuple(cached_obj["data"])
                except Exception:
                    pass
        default_health = await get_health(settings.pp_default)
        if not default_health["failing"] and not (default_health["minResponseTime"] > settings.pp_max_timeout_allowed):
            return settings.pp_default, "default"
        return settings.pp_fallback, "fallback"
