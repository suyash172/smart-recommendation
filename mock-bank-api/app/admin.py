from fastapi import APIRouter, Request

from .models import ScenarioState

router = APIRouter(prefix="/admin", tags=["Admin (test helpers, not in the organisers' contract)"])


@router.post("/reset")
def reset(request: Request):
    """Restore the organisers' seed data."""
    request.app.state.bank.reset()
    return {"status": "reset", "detail": "Restored organiser seed data"}


@router.post("/seed")
def seed(body: ScenarioState, request: Request, replace: bool = True):
    """Apply a scenario's mock_bank_state. By default the store is cleared first,
    so anything not listed falls back to defaults (bank ONLINE, account ACTIVE, balance 10000/9500)."""
    request.app.state.bank.apply_scenario(body.model_dump(), replace=replace)
    return {"status": "seeded", "replace": replace}


@router.get("/state")
def state(request: Request):
    return request.app.state.bank.snapshot()


@router.get("/calls")
def calls(request: Request):
    """Every /api/* call received since the last reset or seed."""
    return request.app.state.bank.calls