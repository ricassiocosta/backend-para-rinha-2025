import os
import orjson
import redis.asyncio as aioredis
import asyncio

from app.config import get_settings

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=False)

PENDING_QUEUE = "payments_pending"
PROCESSING_QUEUE = "payments_processing"
MAX_PARALLELISM = int(os.getenv("MAX_PARALLELISM", 2))


async def add_payment(cid: str, amount: float):
    data = orjson.dumps({"correlationId": cid, "amount": amount}).decode()
    await redis.lpush(PENDING_QUEUE, data)

async def consume_loop(handle_item):

    async def worker(worker_id: int):
        while True:
            try:
                raw = await redis.lpop(PENDING_QUEUE)
                if not raw:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    parsed = orjson.loads(raw)
                except Exception as e:
                    print(f"[ERRO] Worker {worker_id} {e}")
                    await redis.lpush(PENDING_QUEUE, raw)
                    continue

                try:
                    await handle_item(parsed)
                except Exception as e:
                    print(f"[ERRO] Worker {worker_id}: {e}. Sending back to queue.")
                    await redis.lpush(PENDING_QUEUE, raw)

            except Exception as e:
                print(f"[ERRO] Worker {worker_id} {e}")

    tasks = [asyncio.create_task(worker(i)) for i in range(MAX_PARALLELISM)]
    await asyncio.gather(*tasks)
