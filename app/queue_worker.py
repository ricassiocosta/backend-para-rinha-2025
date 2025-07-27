import os
import asyncio
from datetime import datetime, timezone

from app.config import get_settings
from app.client import get_healthier_gateway, send_payment
from app.storage import save_payment

settings = get_settings()

PENDING_QUEUE = "payments_pending"
FAILED_QUEUE = "payments_failed"
MAX_PARALLELISM = int(os.getenv("MAX_PARALLELISM", 2))

payments_queue = asyncio.Queue(maxsize=50000)

async def add_to_queue(cid: str, amount: float):
    data = {"correlationId": cid, "amount": amount}
    await payments_queue.put(data)

async def _worker(worker_id: int):
    while True:
        requested_at = datetime.now(tz=timezone.utc)
        try:
            item = await payments_queue.get()

            try:
                healthier_gateway, gateway_name = await get_healthier_gateway()
                
                if not await send_payment(healthier_gateway, item["correlationId"], item["amount"], requested_at):
                    raise RuntimeError(f"Failed to send payment for {item['correlationId']} to {healthier_gateway}")

                await save_payment(
                    item["correlationId"], item["amount"], gateway_name, requested_at
                )
            except Exception as e:
                print(f"[ERRO] Worker {worker_id}: {e}. Sending back to queue.")
                await payments_queue.put(item)

        except Exception as e:
            print(f"[ERRO] Worker {worker_id} {e}")

async def consume_loop():
    tasks = [asyncio.create_task(_worker(i)) for i in range(MAX_PARALLELISM)]
    await asyncio.gather(*tasks)
