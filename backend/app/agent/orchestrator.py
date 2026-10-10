from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.agent import AgentStep, DecisionSource, NoRecommendationReason
from app.schemas.request import RetryRecommendationRequest
from app.schemas.response import RetryRecommendationResponse, no_recommendation


@dataclass
class AgentResult:
    response: RetryRecommendationResponse
    steps: list[AgentStep] = field(default_factory=list)
    loops_used: int = 0
    source: DecisionSource = DecisionSource.AGENT
    no_rec_reason: NoRecommendationReason | None = None


class DecisionAgent(Protocol):
    def decide(self, request: RetryRecommendationRequest) -> AgentResult: ...


class NotConfiguredAgent:
    """Used until the real ReAct agent is built (Step 7)."""

    def decide(self, request: RetryRecommendationRequest) -> AgentResult:
        return AgentResult(
            response=no_recommendation(request.transaction_id, "the decision agent is not configured yet"),
            source=DecisionSource.FALLBACK,
            no_rec_reason=NoRecommendationReason.LLM_UNAVAILABLE,
        )