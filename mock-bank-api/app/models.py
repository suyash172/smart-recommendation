from typing import Any

from pydantic import BaseModel, Field


class FaultInjection(BaseModel):
    forced_status_code: int | None = Field(default=None, ge=400, le=599)
    applies_to: str | None = None


class ScenarioState(BaseModel):
    """Same shape as `mock_bank_state` in the organisers' scenario files."""

    bank_status: dict[str, dict[str, Any]] = Field(default_factory=dict)
    accounts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    balances: dict[str, dict[str, Any]] = Field(default_factory=dict)
    fault_injection: FaultInjection | None = None