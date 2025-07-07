import time
import httpx, asyncio
from datetime import datetime, timezone
from app.health import get_healthier_gateway
from app.config import get_settings
from uuid import UUID

settings = get_settings()
_MAX_RETRIES = 3

async def send_payment(dest: str, cid: UUID, amount: float) -> bool:
    payload = {
        "correlationId": str(cid),
        "amount": amount,
        "requestedAt": datetime.now(tz=timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=3) as client:
        r = await client.post(f"{dest}/payments", json=payload)
        return r.status_code < 300

async def choose_and_send(cid: UUID, amount: float) -> str:
    for _ in range(_MAX_RETRIES):
        try:
            healthier_gateway, gateway_name = await get_healthier_gateway()
        except Exception as e:
            print(f"Error getting healthier gateway: {e}")
            continue

        if await send_payment(healthier_gateway, cid, amount):
            return gateway_name
        
        time.sleep(0.1)
    
    raise RuntimeError("Failed to send payment after retries")
