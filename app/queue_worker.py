import os
import orjson
import redis.asyncio as aioredis
import asyncio
from datetime import datetime, timezone

from app.config import get_settings
from app.processor import get_healthier_gateway, send_payment
from app.storage import save_payment

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=False)

PENDING_QUEUE = "payments_pending"
FAILED_QUEUE = "payments_failed"
MAX_PARALLELISM = int(os.getenv("MAX_PARALLELISM", 2))

_FAILED_ITEMS = asyncio.Queue()

async def add_to_queue(cid: str, amount: float):
    data = orjson.dumps({"correlationId": cid, "amount": amount}).decode()
    await redis.lpush(PENDING_QUEUE, data)

async def _worker(worker_id: int):
    while True:
        requested_at = datetime.now(tz=timezone.utc)
        try:
            if not _FAILED_ITEMS.empty():
                raw = await _FAILED_ITEMS.get()
            else:
                result = await redis.blpop(PENDING_QUEUE, timeout=0)
                _, raw = result

            try:
                item = orjson.loads(raw)
                healthier_gateway, gateway_name = await get_healthier_gateway()
                
                if not await send_payment(healthier_gateway, item["correlationId"], item["amount"], requested_at):
                    raise RuntimeError(f"Failed to send payment for {item['correlationId']} to {healthier_gateway}")
                
                asyncio.create_task(
                    save_payment(
                        item["correlationId"], item["amount"], gateway_name, requested_at
                    )
                )
            except Exception as e:
                print(f"[ERRO] Worker {worker_id}: {e}. Sending back to queue.")
                await _FAILED_ITEMS.put(raw)

                # # If the item fails, we push it to a failed queue for later processing
                # asyncio.create_task(
                #     redis.rpush(FAILED_QUEUE, raw)
                # )

        except Exception as e:
            print(f"[ERRO] Worker {worker_id} {e}")

async def consume_loop():
    tasks = [asyncio.create_task(_worker(i)) for i in range(MAX_PARALLELISM)]
    await asyncio.gather(*tasks)
