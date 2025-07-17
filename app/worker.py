import asyncio

from app.queue import consume_loop
from app.processor import choose_and_send

_VERSION = "v0.7.1"

async def handle_item(item: dict):
    try:
        await choose_and_send(item["correlationId"], item["amount"])
    except Exception as e:
        print(f"Error processing payment {item}: {e}")
        raise e

if __name__ == "__main__":
    print(f"Worker version {_VERSION} started")
    asyncio.run(consume_loop(handle_item))
