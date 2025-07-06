from fastapi import FastAPI, BackgroundTasks, HTTPException
from app.queue import add_payment
from app.models import PaymentRequest
from app.storage import get_summary
from datetime import datetime
import uvicorn

app = FastAPI(title="Rinha Backend - Python")

@app.post("/payments", status_code=202)
async def queue_payment(p: PaymentRequest):
    await add_payment(p)
    return {"status": "queued"}

@app.get("/payments-summary")
async def payments_summary(from_: str | None = None, to: str | None = None):
    try:
        ts_from = datetime.fromisoformat(from_) if from_ else None
        ts_to = datetime.fromisoformat(to) if to else None
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid timestamp format")
    return await get_summary(ts_from, ts_to)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=9999, reload=False)
