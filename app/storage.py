from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime
from app.models import PaymentInDB
from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_size=100, max_overflow=0, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

insert_stmt = text("""
    INSERT INTO payments (correlation_id, amount, processor, requested_at)
    VALUES (:cid, :amount, :processor, :requested_at)
""")

async def save_payment(p: PaymentInDB):
    async with SessionLocal() as db:
        await db.execute(insert_stmt, {
            "cid": p.correlation_id,
            "amount": p.amount,
            "processor": p.processor,
            "requested_at": p.requested_at,
        })
        await db.commit()

async def get_summary(ts_from: datetime | None, ts_to: datetime | None):
    # cache_key = f"summary:{ts_from.isoformat() if ts_from else 'null'}:{ts_to.isoformat() if ts_to else 'null'}"
    # cached = await redis.get(cache_key)
    # if cached:
    #     return json.loads(cached)

    async with SessionLocal() as db:
        base = """
            SELECT processor, COUNT(*) AS total_requests, 
                   SUM(amount)::float AS total_amount
            FROM payments
        """
        where = []
        params = {}
        if ts_from:
            where.append("requested_at >= :from")
            params["from"] = ts_from
        if ts_to:
            where.append("requested_at <= :to")
            params["to"] = ts_to
        if where:
            base += " WHERE " + " AND ".join(where)
        base += " GROUP BY processor"

        rows = (await db.execute(text(base), params)).mappings().all()

    summary = {
        "default": {"totalRequests": 0, "totalAmount": 0.0},
        "fallback": {"totalRequests": 0, "totalAmount": 0.0},
    }
    for r in rows:
        processor = r["processor"]
        if processor in summary:
            summary[processor]["totalRequests"] = r["total_requests"]
            summary[processor]["totalAmount"] = r["total_amount"] or 0.0

    # await redis.set(cache_key, json.dumps(summary), ex=5)
    return summary

async def purge_payments():
    async with SessionLocal() as db:
        await db.execute(text("DELETE FROM payments"))
        await db.commit()
