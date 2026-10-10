from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolName(str, Enum):
    VERIFY_ACCOUNT = "verify_account"
    CHECK_BALANCE = "check_balance"
    CHECK_BANK_STATUS = "check_bank_status"


class AgentStep(BaseModel):
    """One Thought -> Action -> Observation cycle, stored for the audit trail."""

    step: int = Field(ge=1)
    thought: str | None = None
    action: str                       # tool name, or "final_answer"
    action_input: dict[str, Any] | None = None
    observation: str


class NoRecommendationReason(str, Enum):
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
    LOOP_LIMIT_REACHED = "LOOP_LIMIT_REACHED"
    BANK_API_UNAVAILABLE = "BANK_API_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DecisionSource(str, Enum):
    AGENT = "AGENT"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    KILL_SWITCH = "KILL_SWITCH"
    FALLBACK = "FALLBACK"


class FailureCategory(str, Enum):
    TECHNICAL = "TECHNICAL"
    STRUCTURAL = "STRUCTURAL"