from datetime import datetime
from app.config import get_settings
import orjson
import redis

settings = get_settings()
redis_client = redis.from_url(settings.redis_url, decode_responses=False)

ZSET_KEY = "payments_by_date"

def save_payment(cid: str, amount: float, processor: str, requested_at: datetime):
    timestamp = requested_at.timestamp() if isinstance(requested_at, datetime) else float(requested_at)

    payment_json = orjson.dumps({
        "correlation_id": cid,
        "amount": amount,
        "processor": processor,
        "requested_at": timestamp,
    }).decode()

    redis_client.zadd(ZSET_KEY, {payment_json: timestamp})

def get_summary(ts_from: datetime | None, ts_to: datetime | None):
    min_score = ts_from.timestamp() if ts_from else "-inf"
    max_score = ts_to.timestamp() if ts_to else "+inf"

    payments = redis_client.zrangebyscore(ZSET_KEY, min_score, max_score)

    summary = {
        "default": {"totalRequests": 0, "totalAmount": 0.0},
        "fallback": {"totalRequests": 0, "totalAmount": 0.0},
    }

    for payment_json in payments:
        p = orjson.loads(payment_json)
        processor = p["processor"]
        amount = p["amount"]
        summary[processor]["totalRequests"] += 1
        summary[processor]["totalAmount"] += amount

    return summary

def purge_payments():
    redis_client.delete(ZSET_KEY)
