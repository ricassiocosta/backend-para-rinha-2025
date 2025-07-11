import asyncio
from datetime import datetime
import logging

from app.queue import consume_loop
from app.processor import choose_and_send
from app.models import PaymentRequest

logging.basicConfig(level=logging.INFO, format="[worker] -  %(message)s")

async def handle_item(item: dict):
    try:
        p = PaymentRequest(**item)
        await choose_and_send(p.correlationId, p.amount)
    except Exception as e:
        logging.error(f"Error processing payment {item}: {e}")

if __name__ == "__main__":
    logging.info("Worker started.")
    asyncio.run(consume_loop(handle_item))
