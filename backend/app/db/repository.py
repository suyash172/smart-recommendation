import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload, sessionmaker

from app.db.models import AgentStepRecord, DecisionRecord, SystemSetting
from app.schemas.agent import AgentStep, DecisionSource, FailureCategory, NoRecommendationReason
from app.schemas.request import RetryRecommendationRequest
from app.schemas.response import RetryRecommendationResponse


class DecisionRepository:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    # ---- decisions ----
    def save_decision(
        self,
        *,
        request: RetryRecommendationRequest,
        response: RetryRecommendationResponse,
        http_status: int,
        source: DecisionSource,
        failure_category: FailureCategory,
        no_rec_reason: NoRecommendationReason | None,
        steps: list[AgentStep],
        loops_used: int,
        latency_ms: int,
    ) -> int:
        record = DecisionRecord(
            transaction_id=request.transaction_id,
            retry_count=request.retry_count,
            failure_code=request.failure_code,
            failure_category=failure_category.value,
            request_json=request.model_dump_json(),
            recommendation=response.recommendation.value,
            confidence_score=response.confidence_score,
            explanation=response.explanation,
            optimal_timing=response.optimal_timing,
            correction_suggestions_json=(
                json.dumps(response.correction_suggestions, ensure_ascii=False)
                if response.correction_suggestions
                else None
            ),
            decision_source=source.value,
            no_rec_reason=no_rec_reason.value if no_rec_reason else None,
            http_status=http_status,
            loops_used=loops_used,
            latency_ms=latency_ms,
        )
        record.steps = [
            AgentStepRecord(
                step_no=s.step,
                thought=s.thought,
                action=s.action,
                action_input_json=(
                    json.dumps(s.action_input, ensure_ascii=False) if s.action_input is not None else None
                ),
                observation=s.observation,
            )
            for s in steps
        ]
        with self._sf() as session:
            session.add(record)
            session.commit()
            return record.id

    def get_by_transaction_id(self, transaction_id: str) -> list[DecisionRecord]:
        stmt = (
            select(DecisionRecord)
            .where(DecisionRecord.transaction_id == transaction_id)
            .options(selectinload(DecisionRecord.steps))
            .order_by(DecisionRecord.id)
        )
        with self._sf() as session:
            return list(session.scalars(stmt).all())

    # ---- settings (kill switch lives here) ----
    def get_setting(self, key: str) -> SystemSetting | None:
        with self._sf() as session:
            return session.get(SystemSetting, key)

    def set_setting(self, key: str, value: str, updated_by: str) -> SystemSetting:
        with self._sf() as session:
            setting = session.get(SystemSetting, key)
            now = datetime.now(timezone.utc)
            if setting is None:
                setting = SystemSetting(key=key, value=value, updated_by=updated_by, updated_at=now)
                session.add(setting)
            else:
                setting.value, setting.updated_by, setting.updated_at = value, updated_by, now
            session.commit()
            return setting