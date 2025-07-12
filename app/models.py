from uuid import UUID
from pydantic import BaseModel

class PaymentRequest(BaseModel):
    correlationId: str
    amount: float

