import asyncio
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.responses import ORJSONResponse

from app.queue_worker import add_to_queue, consume_loop
from app.models import PaymentRequest
from app.storage import get_summary, purge_payments

_VERSION = "v0.7.1"
app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, default_response_class=ORJSONResponse)

@app.post("/payments", status_code=202)
async def queue_payment(p: PaymentRequest):
    asyncio.create_task(add_to_queue(p.correlationId, p.amount))
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
    print(f"API version {_VERSION} started")

    async def main():
        config = uvicorn.Config(
            "app.main:app",
            host="0.0.0.0",
            port=9999,
            reload=False,
            loop="uvloop",
            http="httptools",
            workers=1,
            log_level="error",
        )
        server = uvicorn.Server(config)
        
        api_task = asyncio.create_task(server.serve())
        consume_task = asyncio.create_task(consume_loop())
        await asyncio.gather(consume_task, api_task)

    asyncio.run(main())
