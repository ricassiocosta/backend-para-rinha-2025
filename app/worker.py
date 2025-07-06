import asyncio, logging
from uuid import UUID
from app.queue import get_batch
from app.processor import choose_and_send
from app.storage import save_payment
from app.models import PaymentInDB
from datetime import datetime, timezone
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="[worker] %(message)s")
settings = get_settings()

async def process_loop():
    while True:
        batch = await get_batch(settings.worker_batch_size)
        if not batch:
            continue
        tasks = [handle_item(item) for item in batch]
        await asyncio.gather(*tasks)

async def handle_item(item: dict):
    cid = UUID(item["correlationId"])
    amount = item["amount"]
    proc = await choose_and_send(cid, amount)
    await save_payment(
        PaymentInDB(
            correlation_id=cid,
            amount=amount,
            processor=proc,
            requested_at=datetime.now(tz=timezone.utc),
        )
    )

if __name__ == "__main__":
    logging.info("Worker started.")
    asyncio.run(process_loop())
