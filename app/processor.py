import httpx, asyncio
from datetime import datetime, timezone
from app.health import get_health
from app.config import get_settings
from uuid import UUID

settings = get_settings()

async def send_payment(dest: str, cid: UUID, amount: float) -> bool:
    payload = {
        "correlationId": str(cid),
        "amount": amount,
        "requestedAt": datetime.now(tz=timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=1.5) as client:
        r = await client.post(f"{dest}/payments", json=payload)
        return r.status_code < 300

async def choose_and_send(cid: UUID, amount: float) -> str:
    default_health = await get_health(settings.pp_default)
    use_default = not default_health["failing"] and default_health["minResponseTime"] <= settings.pp_timeout_ms
    primary = settings.pp_default if use_default else settings.pp_fallback
    secondary = settings.pp_fallback if use_default else settings.pp_default
    if await send_payment(primary, cid, amount):
        return "default" if use_default else "fallback"
    await send_payment(secondary, cid, amount)
    return "fallback" if use_default else "default"
