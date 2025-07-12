from datetime import datetime
from app.models import PaymentInDB
from app.config import get_settings
import json
import redis.asyncio as aioredis

settings = get_settings()
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

async def save_payment(p: PaymentInDB):
    payment_json = json.dumps({
        "correlation_id": str(p.correlation_id),
        "amount": p.amount,
        "processor": p.processor,
        "requested_at": p.requested_at.isoformat() if isinstance(p.requested_at, datetime) else p.requested_at,
    })
    await redis_client.rpush("payments", payment_json)

async def get_summary(ts_from: datetime | None, ts_to: datetime | None):
    payments = await redis_client.lrange("payments", 0, -1)
    summary = {
        "default": {"totalRequests": 0, "totalAmount": 0.0},
        "fallback": {"totalRequests": 0, "totalAmount": 0.0},
    }
    for payment_json in payments:
        p = json.loads(payment_json)
        requested_at = datetime.fromisoformat(p["requested_at"])
        if requested_at.tzinfo is not None:
            requested_at = requested_at.replace(tzinfo=None)
        if ts_from and ts_from.tzinfo is not None:
            ts_from_naive = ts_from.replace(tzinfo=None)
        else:
            ts_from_naive = ts_from
        if ts_to and ts_to.tzinfo is not None:
            ts_to_naive = ts_to.replace(tzinfo=None)
        else:
            ts_to_naive = ts_to
        if ts_from_naive and requested_at < ts_from_naive:
            continue
        if ts_to_naive and requested_at >= ts_to_naive:
            continue
        processor = p["processor"]
        if processor in summary:
            summary[processor]["totalRequests"] += 1
            summary[processor]["totalAmount"] += float(p["amount"])
    return summary

async def purge_payments():
    await redis_client.delete("payments")
