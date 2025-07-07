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
        if len(batch) == 0:
            continue
        tasks = [handle_item(item) for item in batch]
        await asyncio.gather(*tasks)

async def handle_item(item: dict):
    try:
        cid = UUID(item["correlationId"])
        amount = item["amount"]
        print(f"Processing payment {cid} for amount {amount}")
        proc = await choose_and_send(cid, amount)
        await save_payment(
            PaymentInDB(
                correlation_id=cid,
                amount=amount,
                processor=proc,
                requested_at=datetime.now(tz=timezone.utc),
            )
        )
    except Exception as e:
        logging.error(f"Error processing payment {item}: {e}")
        try:
            await handle_item(item)
        except Exception as retry_error:
            logging.error(f"Retry failed for payment {item}: {retry_error}")

if __name__ == "__main__":
    logging.info("Worker started.")
    asyncio.run(process_loop())
