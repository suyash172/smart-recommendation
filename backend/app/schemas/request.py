from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PaymentRail(str, Enum):
    RTGS = "RTGS"
    NEFT = "NEFT"
    SEPA = "SEPA"
    SWIFT = "SWIFT"
    FASTER_PAYMENTS = "Faster Payments"
    ACH = "ACH"


class PartyDetails(BaseModel):
    """Payer or beneficiary. Values are kept exactly as received:
    spaces inside an IBAN matter (scenario E3C) and name cleanup is the agent's job."""

    name: str = Field(min_length=1, max_length=300)
    account_number: str = Field(min_length=1, max_length=64)
    bic_code: str = Field(min_length=1, max_length=20)


class RetryRecommendationRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    payment_rail: PaymentRail
    failure_code: str = Field(min_length=1, max_length=100)
    failure_reason: str = Field(min_length=1, max_length=1000)
    ordering_customer: PartyDetails
    beneficiary: PartyDetails
    timestamp: datetime
    retry_count: int = Field(default=0, ge=0)