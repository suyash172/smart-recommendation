import asyncio
import os
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response

from .admin import router as admin_router
from .seed_loader import load_seed
from .state import MockBankState


async def _fault_response(fault: dict[str, Any]) -> Response:
    ftype = fault.get("type")

    if ftype == "timeout":
        # MOCK_DELAY_SCALE lets tests shrink the 15 s delay to ~0
        delay = float(fault.get("delay_seconds", 15)) * float(os.getenv("MOCK_DELAY_SCALE", "1"))
        await asyncio.sleep(delay)
        return JSONResponse(status_code=504, content={"error": "Gateway timeout"})

    if ftype == "http_error":
        return JSONResponse(
            status_code=int(fault.get("status_code", 500)),
            content={"error": "Simulated upstream error"},
        )

    if ftype == "malformed_json":
        return Response(content='{"exists": tru', media_type="application/json", status_code=200)

    if ftype == "invalid_data":
        return JSONResponse(status_code=200, content=fault.get("payload", {}))

    return JSONResponse(status_code=500, content={"error": f"Unknown fault type: {ftype}"})


async def _respond(
    request: Request,
    endpoint: str,
    key: str,
    entry: dict[str, Any],
    build: Callable[[dict[str, Any]], dict[str, Any]],
) -> Response:
    state: MockBankState = request.app.state.bank
    state.record_call(endpoint, key)

    if state.forced_status_code:  # global fault injection: applies to every /api/* endpoint
        return JSONResponse(
            status_code=state.forced_status_code, content={"error": "Forced fault injection"}
        )
    if "fault" in entry:
        return await _fault_response(entry["fault"])
    return JSONResponse(content=build(entry["data"]))


def create_app(seed: dict[str, Any] | None = None) -> FastAPI:
    app = FastAPI(
        title="Mock Bank Status API",
        version="2.0.0",
        description="Mock of the organisers' Bank Status API. Lookups are exact-match; unknown keys get defaults.",
    )
    app.state.bank = MockBankState(seed if seed is not None else load_seed())
    app.include_router(admin_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/accounts")
    async def get_account(request: Request, account_number: str = Query(..., alias="account-number")):
        entry = request.app.state.bank.lookup_account(account_number)
        return await _respond(
            request, "/api/accounts", account_number, entry,
            lambda d: {**d, "account_number": account_number},
        )

    @app.get("/api/accounts-balance")
    async def get_balance(request: Request, account_number: str = Query(..., alias="account-number")):
        entry = request.app.state.bank.lookup_balance(account_number)
        return await _respond(request, "/api/accounts-balance", account_number, entry, lambda d: d)

    @app.get("/api/bank-status")
    async def get_bank_status(request: Request, bic_code: str = Query(..., alias="bic-code")):
        entry = request.app.state.bank.lookup_bank(bic_code)
        return await _respond(
            request, "/api/bank-status", bic_code, entry,
            lambda d: {"estimated_recovery": None, **d, "bic_code": bic_code},
        )

    return app


app = create_app()