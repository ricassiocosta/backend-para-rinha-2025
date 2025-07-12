import asyncio

from app.queue import consume_loop
from app.processor import choose_and_send

async def handle_item(item: dict):
    try:
        await choose_and_send(item["correlationId"], item["amount"])
    except Exception as e:
        print(f"Error processing payment {item}: {e}")

if __name__ == "__main__":
    print("Worker started.")
    asyncio.run(consume_loop(handle_item))
