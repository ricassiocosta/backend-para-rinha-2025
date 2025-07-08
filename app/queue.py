import os
import redis.asyncio as aioredis
from redis.exceptions import ResponseError
import json
from app.config import get_settings
from app.models import PaymentRequest
import asyncio

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True, max_connections=100)

STREAM = "payments_stream"
GROUP = "payment_consumers"
CONSUMER = os.getenv("CONSUMER_NAME", "worker-default")
MAX_PARALLELISM = 8

async def setup_stream():
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            pass 
        else:
            raise

async def add_payment(p: PaymentRequest):
    await redis.xadd(STREAM, {"data": p.model_dump_json()})

async def consume_loop(handle_item):
    await setup_stream()
    sem = asyncio.Semaphore(MAX_PARALLELISM)

    async def handle_with_ack(entry_id, data):
        async with sem:
            try:
                await handle_item(data)
                await redis.xack(STREAM, GROUP, entry_id)
            except Exception as e:
                print(f"Erro ao processar {entry_id}: {e}")

    while True:
        entries = await redis.xreadgroup(
            groupname=GROUP,
            consumername=CONSUMER,
            streams={STREAM: ">"},
            count=MAX_PARALLELISM,
            block=2000 
        )

        if not entries:
            continue

        tasks = []
        for _, items in entries:
            for entry_id, entry_data in items:
                try:
                    raw = entry_data.get("data")
                    parsed = json.loads(raw)
                    tasks.append(handle_with_ack(entry_id, parsed))
                except Exception as e:
                    print(f"Erro ao decodificar item {entry_id}: {e}")

        await asyncio.gather(*tasks)
