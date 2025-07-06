from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime
from app.models import PaymentInDB
from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_size=20, max_overflow=0)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def save_payment(p: PaymentInDB):
    async with SessionLocal() as db:
        await db.execute(
            text(
                "INSERT INTO payments "
                "(correlation_id, amount, processor, requested_at) "
                "VALUES (:cid, :amount, :processor, :requested_at)"
            ),
            dict(
                cid=str(p.correlation_id),
                amount=p.amount,
                processor=p.processor,
                requested_at=p.requested_at,
            ),
        )
        await db.commit()

async def get_summary(ts_from: datetime | None, ts_to: datetime | None):
    async with SessionLocal() as db:
        base = (
            "SELECT processor, COUNT(*) total_requests, "
            "COALESCE(SUM(amount),0) total_amount "
            "FROM payments "
        )
        where = []
        params = {}
        if ts_from:
            where.append("requested_at >= :from")
            params["from"] = ts_from
        if ts_to:
            where.append("requested_at <= :to")
            params["to"] = ts_to
        if where:
            base += "WHERE " + " AND ".join(where)
        base += " GROUP BY processor"
        rows = (await db.execute(text(base), params)).mappings().all()

    summary = {
        "default": {"totalRequests": 0, "totalAmount": 0.0},
        "fallback": {"totalRequests": 0, "totalAmount": 0.0},
    }
    for r in rows:
        summary[r["processor"]]["totalRequests"] = r["total_requests"]
        summary[r["processor"]]["totalAmount"] = float(r["total_amount"])
    return summary

async def purge_payments():
    async with SessionLocal() as db:
        await db.execute(text("DELETE FROM payments"))
        await db.commit()
