from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Recommendation(str, Enum):
    RETRY_NOW = "RETRY_NOW"
    RETRY_LATER = "RETRY_LATER"
    RETRY_AFTER_UPDATE = "RETRY_AFTER_UPDATE"
    DONT_RETRY = "DONT_RETRY"
    NO_RECOMMENDATION = "NO_RECOMMENDATION"


class RecommendationCore(BaseModel):
    """What the agent must produce. Also the base of the API response."""

    recommendation: Recommendation
    confidence_score: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1)
    optimal_timing: datetime | None = None
    correction_suggestions: list[str] | None = None

    @model_validator(mode="after")
    def check_conditional_fields(self):
        rec = self.recommendation

        if rec == Recommendation.RETRY_LATER:
            if self.optimal_timing is None:
                raise ValueError("optimal_timing is required when recommendation is RETRY_LATER")
        elif self.optimal_timing is not None:
            raise ValueError("optimal_timing must be null unless recommendation is RETRY_LATER")

        if rec == Recommendation.RETRY_AFTER_UPDATE:
            suggestions = self.correction_suggestions
            if not suggestions or any(not s.strip() for s in suggestions):
                raise ValueError(
                    "correction_suggestions must be a non-empty list of non-empty strings "
                    "when recommendation is RETRY_AFTER_UPDATE"
                )
        elif self.correction_suggestions:
            raise ValueError(
                "correction_suggestions must be null unless recommendation is RETRY_AFTER_UPDATE"
            )
        else:
            self.correction_suggestions = None  # normalise [] to null

        return self


class RetryRecommendationResponse(RecommendationCore):
    transaction_id: str


# ---- Deterministic responses (no LLM involved) ----

def dont_retry_max_retries(transaction_id: str, retry_count: int, max_retry_count: int) -> RetryRecommendationResponse:
    return RetryRecommendationResponse(
        transaction_id=transaction_id,
        recommendation=Recommendation.DONT_RETRY,
        confidence_score=1.0,
        explanation=(
            f"Max retry limit reached: retry_count {retry_count} >= limit {max_retry_count}. "
            "Escalate to operations; automated retries are stopped."
        ),
    )


def no_recommendation(transaction_id: str, detail: str) -> RetryRecommendationResponse:
    return RetryRecommendationResponse(
        transaction_id=transaction_id,
        recommendation=Recommendation.NO_RECOMMENDATION,
        confidence_score=0.0,
        explanation=f"Unable to produce a recommendation: {detail}. Manual handling required.",
    )