import httpx
import asyncio
from typing import Optional
from datetime import datetime, timezone
from app.health import get_healthier_gateway
from app.config import get_settings
from uuid import UUID

settings = get_settings()

async def send_payment(dest: str, cid: UUID, amount: float) -> bool:
    payload = {
        "correlationId": str(cid),
        "amount": amount,
        "requestedAt": datetime.now(tz=timezone.utc).isoformat(),
    }
    timeout = httpx.Timeout(3)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{dest}/payments", json=payload)
            return r.status_code < 300
    except httpx.TimeoutException:
        await asyncio.sleep(5)
        async with httpx.AsyncClient(timeout=timeout) as client:
            get_resp = await client.get(f"{dest}/payments/{cid}")
            return get_resp.status_code == 200

async def choose_and_send(cid: UUID, amount: float) -> Optional[str]:
    try:
        healthier_gateway, gateway_name = await get_healthier_gateway()
    except Exception as e:
        print(f"Error getting healthier gateway: {e}")
        return None

    try:
        if await send_payment(healthier_gateway, cid, amount):
            return gateway_name
        raise RuntimeError("Default processor failed")
    except Exception as e:
        # fallback_gateway = settings.pp_fallback if healthier_gateway == settings.pp_default else settings.pp_default
        # if await send_payment(fallback_gateway, cid, amount):
        #     return "fallback" if fallback_gateway == settings.pp_fallback else "default"
        return None
