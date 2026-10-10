from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DecisionRecord(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(100), index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_code: Mapped[str] = mapped_column(String(100))
    failure_category: Mapped[str] = mapped_column(String(20))
    request_json: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(String(30), index=True)
    confidence_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    optimal_timing: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correction_suggestions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_source: Mapped[str] = mapped_column(String(20))
    no_rec_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    http_status: Mapped[int] = mapped_column(Integer)
    loops_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    steps: Mapped[list["AgentStepRecord"]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="AgentStepRecord.step_no",
    )


class AgentStepRecord(Base):
    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), index=True)
    step_no: Mapped[int] = mapped_column(Integer)
    thought: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    action_input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    decision: Mapped["DecisionRecord"] = relationship(back_populates="steps")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")