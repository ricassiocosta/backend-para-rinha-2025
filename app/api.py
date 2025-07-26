import asyncio
import uvicorn

from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import ORJSONResponse

from app.storage import add_to_queue
from app.models import PaymentRequest
from app.storage import get_summary, purge_payments
from app.config import get_version

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, default_response_class=ORJSONResponse)

@app.post("/payments", status_code=202)
async def queue_payment(p: PaymentRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(add_to_queue, p.correlationId, p.amount)
    return {"status": "queued"}

@app.get("/payments-summary")
async def payments_summary(from_: str | None = Query(default=None, alias="from"), to: str | None = None):
    if from_ is not None:
        from_ = datetime.fromisoformat(from_)
    if to is not None:
        to = datetime.fromisoformat(to)

    return await get_summary(from_, to)

@app.post("/purge-payments")
async def purge_payments_endpoint():
    await purge_payments()
    return {"status": "payments purged"}

if __name__ == "__main__":
    print(f"API version {get_version()} started")

    config = uvicorn.Config(
        "app.api:app",
        host="0.0.0.0",
        port=9999,
        reload=False,
        loop="uvloop",
        http="httptools",
        workers=1,
        log_level="error",
    )

    server = uvicorn.Server(config)
    asyncio.run(server.serve())
