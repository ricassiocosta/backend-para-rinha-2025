import httpx
import orjson
import redis.asyncio as aioredis

from datetime import datetime

from app.config import get_settings

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True)
_CACHE_KEY = "gateway_status"
_LOCAL_CACHE = {"ts": 0, "value": None}
client = httpx.AsyncClient()

async def send_payment(dest: str, cid: str, amount: float, requested_at: datetime) -> bool:
    payload = {
        "correlationId": cid,
        "amount": amount,
        "requestedAt": requested_at.isoformat(),
    }
    r = await client.post(f"{dest}/payments", json=payload, timeout=httpx.Timeout(10, connect=1.0))
    if r.status_code == 200:
        return True

    return False

async def get_healthier_gateway() -> tuple[str, str]:
    if _LOCAL_CACHE["value"] and (datetime.now() - _LOCAL_CACHE["ts"] < 1): 
        return _LOCAL_CACHE["value"]
    
    cached = await redis.get(_CACHE_KEY)
    if cached:
        try:
            cached_obj = orjson.loads(cached)
            return tuple(cached_obj["data"])
        except Exception:
            raise RuntimeError("No valid gateway health data in cache")

    # If cache is empty or invalid, default to the primary gateway
    return settings.pp_default, "default"
