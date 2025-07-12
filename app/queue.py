import os
import orjson
import redis.asyncio as aioredis
from redis.exceptions import ResponseError
from app.config import get_settings
import asyncio

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True, max_connections=500)

STREAM = "payments_stream"
GROUP = "payment_consumers"
CONSUMER = os.getenv("CONSUMER_NAME", "worker-default")
MAX_PARALLELISM = int(os.getenv("MAX_PARALLELISM", 10))

async def setup_stream():
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            pass 
        else:
            raise

async def add_payment(cid: str, amount: float):
    await redis.xadd(STREAM, {"data": orjson.dumps({"correlationId": cid, "amount": amount})})

async def consume_loop(handle_item):
    await setup_stream()
    sem = asyncio.Semaphore(MAX_PARALLELISM)

    async def handle_with_ack(entry_id, data):
        async with sem:
            try:
                await handle_item(data)
                await redis.xack(STREAM, GROUP, entry_id)
            except Exception as e:
                print(e)

    while True:
        entries = await redis.xreadgroup(
            groupname=GROUP,
            consumername=CONSUMER,
            streams={STREAM: ">"},
            count=(MAX_PARALLELISM * 2),
        )

        if not entries:
            await asyncio.sleep(0.001)
            continue

        async with asyncio.TaskGroup() as tg:
            for _, items in entries:
                for entry_id, entry_data in items:
                    raw = entry_data.get("data")
                    try:
                        parsed = orjson.loads(raw)
                        tg.create_task(handle_with_ack(entry_id, parsed))
                    except Exception as e:
                        print(e)
