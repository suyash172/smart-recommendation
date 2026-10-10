from app.schemas.agent import FailureCategory
from app.schemas.response import Recommendation

TECHNICAL_CODES = {
    "NETWORK_TIMEOUT", "GATEWAY_TIMEOUT", "PROCESSING_ERROR",
    "API_LATENCY", "CBS_DOWNTIME", "BANK_UNAVAILABLE", "SERVICE_UNAVAILABLE",
}
STRUCTURAL_CODES = {
    "NAME_MISMATCH", "INVALID_ACCOUNT", "INSUFFICIENT_FUNDS", "ACCOUNT_CLOSED",
    "ACCOUNT_FROZEN", "IBAN_FORMAT_ERROR", "INCORRECT_BENEFICIARY",
}


def classify_failure(failure_code: str, recommendation: Recommendation | None = None) -> FailureCategory:
    """Technical vs structural/data failure, for the dashboard's failure distribution.
    Unknown failure codes are classified from the final recommendation."""
    code = failure_code.strip().upper()
    if code in TECHNICAL_CODES:
        return FailureCategory.TECHNICAL
    if code in STRUCTURAL_CODES:
        return FailureCategory.STRUCTURAL
    if recommendation in (Recommendation.RETRY_NOW, Recommendation.RETRY_LATER):
        return FailureCategory.TECHNICAL
    return FailureCategory.STRUCTURAL