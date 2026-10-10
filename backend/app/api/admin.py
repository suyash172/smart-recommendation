from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["Admin"])


class KillSwitchUpdate(BaseModel):
    active: bool
    updated_by: str = Field(default="unknown", min_length=1, max_length=100)


class KillSwitchState(BaseModel):
    active: bool
    updated_by: str | None = None
    updated_at: datetime | None = None


@router.get("/kill-switch", response_model=KillSwitchState)
def get_kill_switch(request: Request):
    return request.app.state.kill_switch.status()


@router.post("/kill-switch", response_model=KillSwitchState)
def set_kill_switch(body: KillSwitchUpdate, request: Request):
    """ON: every transaction gets NO_RECOMMENDATION and the LLM is never called."""
    return request.app.state.kill_switch.set_active(body.active, body.updated_by)