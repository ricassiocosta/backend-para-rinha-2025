import httpx
import orjson
import redis.asyncio as aioredis

from datetime import datetime, timezone

from app.config import get_settings
from app.storage import save_payment

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
    r = await client.post(f"{dest}/payments", json=payload, timeout=httpx.Timeout(3.0, connect=1.0))
    if r.status_code == 200:
        return True

    return False

async def choose_and_send(cid: str, amount: float):
    try:
        healthier_gateway, gateway_name = await _get_healthier_gateway()
        requested_at = datetime.now(tz=timezone.utc)
        if await send_payment(healthier_gateway, cid, amount, requested_at):
            await save_payment(
                cid, amount, gateway_name, requested_at
            )
            return
        print(f"Failed to send payment to {healthier_gateway} for {cid}")
    except Exception as e:
        print(f"Failed to send payment to {healthier_gateway} for {cid}")
        raise e
    
    raise Exception(f"Failed to send payment to {healthier_gateway} for {cid}")

def _is_cache_valid(ts: float) -> bool:
    now = datetime.now().timestamp()
    return (ts + settings.health_cache_ttl) > now

async def _get_healthier_gateway() -> tuple[str, str]:
    if _LOCAL_CACHE["value"] and (datetime.now() - _LOCAL_CACHE["ts"] < 1): 
        return _LOCAL_CACHE["value"]
    
    cached = await redis.get(_CACHE_KEY)
    if cached:
        try:
            cached_obj = orjson.loads(cached)
            if _is_cache_valid(cached_obj["ts"]):
                return tuple(cached_obj["data"])
        except Exception:
            pass
    raise RuntimeError("No valid gateway health data in cache")