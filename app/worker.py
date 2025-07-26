import os
import orjson
import asyncio
import redis.asyncio as aioredis

from datetime import datetime, timezone

from app.config import get_settings, get_version
from app.processor import get_healthier_gateway, send_payment
from app.storage import save_payment

settings = get_settings()
redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)

MAX_PARALLELISM = int(os.getenv("MAX_PARALLELISM", 2))

async def _worker(worker_id: int):
    while True:
        requested_at = datetime.now(tz=timezone.utc)
        try:
            result = await redis_client.blpop(settings.PENDING_QUEUE, timeout=0)
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
                asyncio.create_task(
                    redis_client.rpush(settings.PENDING_QUEUE, raw)
                )

        except Exception as e:
            print(f"[ERRO] Worker {worker_id} {e}")

async def consume_loop():
    tasks = [asyncio.create_task(_worker(i)) for i in range(MAX_PARALLELISM)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    print(f"Worker version {get_version()} started")
    asyncio.run(consume_loop())