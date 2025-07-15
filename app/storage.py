from datetime import datetime
from app.config import get_settings
import orjson
import redis.asyncio as aioredis

settings = get_settings()
redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)

ZSET_KEY = "payments_by_date"

async def save_payment(cid: str, amount: float, processor: str, requested_at: datetime):
    timestamp = requested_at.timestamp() if isinstance(requested_at, datetime) else float(requested_at)

    payment_json = orjson.dumps({
        "correlation_id": cid,
        "amount": amount,
        "processor": processor,
        "requested_at": timestamp,
    }).decode()

    await redis_client.zadd(ZSET_KEY, {payment_json: timestamp})

async def get_summary(ts_from: datetime | None, ts_to: datetime | None):
    min_score = ts_from.timestamp() if ts_from else "-inf"
    max_score = ts_to.timestamp() if ts_to else "+inf"

    payments = await redis_client.zrangebyscore(ZSET_KEY, min_score, max_score)

    summary = {
        "default": {"totalRequests": 0, "totalAmount": 0.0},
        "fallback": {"totalRequests": 0, "totalAmount": 0.0},
    }

    for payment_json in payments:
        p = orjson.loads(payment_json)
        processor = p.get("processor")
        if processor in summary:
            summary[processor]["totalRequests"] += 1
            summary[processor]["totalAmount"] += float(p.get("amount", 0.0))

    return summary

async def purge_payments():
    await redis_client.delete(ZSET_KEY)
