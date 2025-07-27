import httpx
import orjson
import redis

from datetime import datetime

from app.config import get_settings

settings = get_settings()
redis = redis.from_url(settings.redis_url, decode_responses=True)
_CACHE_KEY = "gateway_status"

local_cache = {
    "cache": None
}

client = httpx.AsyncClient()

async def get_health(url: str) -> dict:
    try:
        resp = await client.get(f"{url}/payments/service-health", timeout=httpx.Timeout(1.0))
        if resp.status_code != 200:
            return {"failing": True, "minResponseTime": 10_000}

        return resp.json()
    
    except httpx.ReadTimeout:
        print(f"[WARN] Timeout while checking health for {url}")
        return {"failing": True, "minResponseTime": 10_000}


async def send_payment(dest: str, cid: str, amount: float, requested_at: datetime) -> bool:
    payload = {
        "correlationId": cid,
        "amount": amount,
        "requestedAt": requested_at.isoformat(),
    }
    r = await client.post(f"{dest}/payments", json=payload, timeout=httpx.Timeout(30, connect=1.0))
    if r.status_code == 200:
        return True

    return False

async def get_healthier_gateway() -> tuple[str, str]:
    if local_cache["cache"] and (datetime.now().timestamp() - local_cache["cache"]["ts"] < 5):
        return local_cache["cache"]["data"]

    cached = redis.get(_CACHE_KEY)
    if cached:
        try:
            cached_obj = orjson.loads(cached)
            local_cache["cache"] = cached_obj
            return tuple(cached_obj["data"])
        except Exception:
            raise RuntimeError("No valid gateway health data in cache")

    # If cache is empty or invalid, default to the primary gateway
    return settings.pp_default, "default"
