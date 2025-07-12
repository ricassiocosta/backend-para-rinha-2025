from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import ORJSONResponse
from app.queue import add_payment
from app.models import PaymentRequest
from app.storage import get_summary, purge_payments
from datetime import datetime
import uvicorn

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, default_response_class=ORJSONResponse)

@app.post("/payments", status_code=202)
async def queue_payment(p: PaymentRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(add_payment, p)
    return {"status": "queued"}

@app.get("/payments-summary")
async def payments_summary(from_: str | None = Query(default=None, alias="from"), to: str | None = None):
    return await get_summary(datetime.fromisoformat(from_), datetime.fromisoformat(to))

@app.post("/purge-payments")
async def purge_payments_endpoint():
    await purge_payments()
    return {"status": "payments purged"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=9999, reload=False)
