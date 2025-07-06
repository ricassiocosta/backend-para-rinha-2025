from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

class PaymentRequest(BaseModel):
    correlationId: UUID = Field(..., alias="correlationId")
    amount: float

class PaymentInDB(BaseModel):
    correlation_id: UUID
    amount: float
    processor: str
    requested_at: datetime
