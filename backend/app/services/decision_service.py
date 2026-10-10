import logging
import time

from app.agent.orchestrator import AgentResult, DecisionAgent
from app.config import Settings
from app.db.repository import DecisionRepository
from app.schemas.agent import AgentStep, DecisionSource, NoRecommendationReason
from app.schemas.request import RetryRecommendationRequest
from app.schemas.response import (
    Recommendation,
    RetryRecommendationResponse,
    dont_retry_max_retries,
    no_recommendation,
)
from app.services.circuit_breaker import is_retry_budget_exhausted
from app.services.failure_classifier import classify_failure
from app.services.kill_switch import KillSwitch

logger = logging.getLogger(__name__)


class DecisionService:
    def __init__(
        self,
        settings: Settings,
        repo: DecisionRepository,
        kill_switch: KillSwitch,
        agent: DecisionAgent,
    ):
        self._settings = settings
        self._repo = repo
        self._kill_switch = kill_switch
        self._agent = agent

    def process(self, request: RetryRecommendationRequest) -> tuple[RetryRecommendationResponse, int]:
        """Returns (response, http_status). Order matters:
        1) kill switch  2) retry budget  3) agent.  Steps 1 and 2 never call the LLM."""
        started = time.perf_counter()

        if self._kill_switch.is_active():
            response = no_recommendation(
                request.transaction_id, "kill switch is active - all automated decisions are stopped"
            )
            return self._finish(
                request, response, 200, DecisionSource.KILL_SWITCH,
                NoRecommendationReason.KILL_SWITCH_ACTIVE, [], 0, started,
            )

        if is_retry_budget_exhausted(request.retry_count, self._settings.max_retry_count):
            response = dont_retry_max_retries(
                request.transaction_id, request.retry_count, self._settings.max_retry_count
            )
            return self._finish(
                request, response, 429, DecisionSource.CIRCUIT_BREAKER, None, [], 0, started
            )

        try:
            result = self._agent.decide(request)
        except Exception:
            logger.exception("Agent crashed for transaction %s", request.transaction_id)
            result = AgentResult(
                response=no_recommendation(request.transaction_id, "internal error while evaluating"),
                source=DecisionSource.FALLBACK,
                no_rec_reason=NoRecommendationReason.INTERNAL_ERROR,
            )

        reason = result.no_rec_reason
        if result.response.recommendation == Recommendation.NO_RECOMMENDATION:
            reason = reason or NoRecommendationReason.INTERNAL_ERROR
        else:
            reason = None

        return self._finish(
            request, result.response, 200, result.source, reason,
            result.steps, result.loops_used, started,
        )

    def _finish(
        self,
        request: RetryRecommendationRequest,
        response: RetryRecommendationResponse,
        http_status: int,
        source: DecisionSource,
        no_rec_reason: NoRecommendationReason | None,
        steps: list[AgentStep],
        loops_used: int,
        started: float,
    ) -> tuple[RetryRecommendationResponse, int]:
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            self._repo.save_decision(
                request=request,
                response=response,
                http_status=http_status,
                source=source,
                failure_category=classify_failure(request.failure_code, response.recommendation),
                no_rec_reason=no_rec_reason,
                steps=steps,
                loops_used=loops_used,
                latency_ms=latency_ms,
            )
        except Exception:
            # Never fail the payment engine because the audit write failed.
            logger.exception("Could not persist decision for %s", request.transaction_id)

        logger.info(
            "txn=%s retry_count=%s -> %s (conf=%.2f, source=%s, http=%s, %d ms)",
            request.transaction_id, request.retry_count, response.recommendation.value,
            response.confidence_score, source.value, http_status, latency_ms,
        )
        return response, http_status