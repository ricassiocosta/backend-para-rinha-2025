import asyncio
import logging
from uuid import UUID
from datetime import datetime, timezone

from app.queue import consume_loop
from app.processor import choose_and_send
from app.storage import save_payment
from app.models import PaymentInDB, PaymentRequest

logging.basicConfig(level=logging.INFO, format="[worker] %(message)s")


async def handle_item(item: dict):
    try:
        p = PaymentRequest(**item)
        processor = await choose_and_send(p.correlationId, p.amount)

        await save_payment(
            PaymentInDB(
                correlation_id=p.correlationId,
                amount=p.amount,
                processor=processor,
                requested_at=datetime.now(tz=timezone.utc),
            )
        )
    except Exception as e:
        logging.error(f"Error processing payment {item}: {e}")


if __name__ == "__main__":
    logging.info("Worker started.")
    asyncio.run(consume_loop(handle_item))
