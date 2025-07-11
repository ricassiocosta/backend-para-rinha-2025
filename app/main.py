from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import ORJSONResponse
from app.queue import add_payment
from app.models import PaymentRequest
from app.storage import get_summary, purge_payments
from datetime import datetime
from app.storage import SessionLocal
from sqlalchemy import text
import uvicorn

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, default_response_class=ORJSONResponse)

@app.post("/payments", status_code=202)
async def queue_payment(p: PaymentRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(add_payment, p)
    return {"status": "queued"}

@app.get("/payments-summary")
async def payments_summary(from_: str | None = Query(default=None, alias="from"), to: str | None = None):
    return await get_summary(datetime.fromisoformat(from_), datetime.fromisoformat(to))

@app.get("/payments/{correlation_id}")
async def get_payment_status(correlation_id: str):
    async with SessionLocal() as db:
        result = await db.execute(
            text("SELECT * FROM payments WHERE correlation_id = :cid"),
            {"cid": correlation_id}
        )
        payment = result.mappings().first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "correlationId": payment["correlation_id"],
        "amount": payment["amount"],
        "processor": payment["processor"],
        "requestedAt": payment["requested_at"].isoformat(),
    }

@app.post("/purge-payments")
async def purge_payments_endpoint():
    await purge_payments()
    return {"status": "payments purged"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=9999, reload=False)
