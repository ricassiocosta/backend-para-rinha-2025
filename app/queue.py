import redis.asyncio as aioredis
import json
from app.config import get_settings
from app.models import PaymentRequest

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True)
STREAM = "payments_stream"

async def add_payment(p: PaymentRequest):
    await redis.xadd(STREAM, {"data": p.model_dump_json()})

async def get_batch(count: int = 100):
    entries = await redis.xread({STREAM: "0"}, count=count, block=1000)
    print(f"Fetched {len(entries)} entries from stream {STREAM}")
    if not entries:
        return []
    _, items = entries[0]
    ids, data = zip(*items)
    await redis.xdel(STREAM, *ids)
    return [json.loads(d["data"]) for d in data]
