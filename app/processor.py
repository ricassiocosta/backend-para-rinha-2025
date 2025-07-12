import logging
import httpx
import json
import redis.asyncio as aioredis

from uuid import UUID
from datetime import datetime, timezone

from app.models import PaymentInDB
from app.config import get_settings
from app.storage import save_payment

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True)
_CACHE_KEY = "gateway_status"

logging.basicConfig(level=logging.INFO, format="[worker] %(message)s")

async def send_payment(dest: str, cid: UUID, amount: float, requested_at: datetime) -> bool:
    payload = {
        "correlationId": str(cid),
        "amount": amount,
        "requestedAt": requested_at.isoformat(),
    }
    async with httpx.AsyncClient() as client:
        backoff = 1
        for _ in range(3):
            try:
                r = await client.post(f"{dest}/payments", json=payload, timeout=backoff)
                if r.status_code == 200:
                    return True
            except httpx.TimeoutException:
                logging.warning(f"Timeout sending payment to {dest} for {cid}, retrying...")
                backoff *= 2
    
    return False

async def choose_and_send(cid: UUID, amount: float):
    try:
        healthier_gateway, gateway_name = await _get_healthier_gateway()
        requested_at = datetime.now(tz=timezone.utc)
        if await send_payment(healthier_gateway, cid, amount, requested_at):
            await save_payment(
                PaymentInDB(
                    correlation_id=cid,
                    amount=amount,
                    processor=gateway_name,
                    requested_at=requested_at,
                )
            )
            return
        logging.error(f"Failed to send payment to {healthier_gateway} for {cid}")
    except Exception as e:
        logging.error(f"Failed to send payment to {healthier_gateway} for {cid}")
        raise e
    
    raise Exception(f"Failed to send payment to {healthier_gateway} for {cid}")

def _is_cache_valid(ts: float) -> bool:
    now = datetime.now().timestamp()
    return (ts + settings.health_cache_ttl) > now

async def _get_healthier_gateway() -> tuple[str, str]:
    cached = await redis.get(_CACHE_KEY)
    if cached:
        try:
            cached_obj = json.loads(cached)
            if _is_cache_valid(cached_obj["ts"]):
                return tuple(cached_obj["data"])
        except Exception:
            pass
    raise RuntimeError("No valid gateway health data in cache")