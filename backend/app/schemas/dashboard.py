from datetime import datetime

from pydantic import BaseModel, Field


class DashboardMetrics(BaseModel):
    # fields from the organisers' contract
    stp_rate_enhancement: float
    automation_savings_pct: float
    failure_distribution: dict[str, int] = Field(default_factory=dict)
    # extras for the executive view
    total_transactions: int = 0
    recovery_success_rate: float = 0.0
    recommendation_counts: dict[str, int] = Field(default_factory=dict)
    kill_switch_active: bool = False


class TransactionAuditRecord(BaseModel):
    transaction_id: str
    timestamp: datetime
    recommendation: str
    status: str
    confidence_score: float | None = None


class ReasoningStepOut(BaseModel):
    step: int
    thought: str | None = None
    action: str
    observation: str


class AgentReasoning(BaseModel):
    transaction_id: str
    thought_process: list[ReasoningStepOut] = Field(default_factory=list)
    tool_logs: list[str] = Field(default_factory=list)


class TimeSeriesPoint(BaseModel):
    period: str            # e.g. "2026-W41" or "2026-10"
    total: int
    successful: int


class SavingsByType(BaseModel):
    failure_type: str
    count: int
    minutes_saved: float


class SavingsReport(BaseModel):
    transactions_assisted: int
    total_minutes_saved: float
    by_failure_type: list[SavingsByType] = Field(default_factory=list)


class ExceptionBreakdown(BaseModel):
    total: int
    by_reason: dict[str, int] = Field(default_factory=dict)
    recent: list[TransactionAuditRecord] = Field(default_factory=list)