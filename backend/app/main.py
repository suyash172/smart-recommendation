from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.orchestrator import DecisionAgent, NotConfiguredAgent
from app.api import admin, retry_decision
from app.config import Settings, load_settings
from app.core.logging import setup_logging
from app.db.database import init_db, make_engine, make_session_factory
from app.db.repository import DecisionRepository
from app.services.decision_service import DecisionService
from app.services.kill_switch import KillSwitch


def create_app(settings: Settings | None = None, agent: DecisionAgent | None = None) -> FastAPI:
    settings = settings or load_settings()
    setup_logging()

    engine = make_engine(settings.database_url)
    init_db(engine)
    repo = DecisionRepository(make_session_factory(engine))
    kill_switch = KillSwitch(repo)

    app = FastAPI(
        title="Smart-Recommendation API",
        version="2.0.0",
        description="Middleware that recommends what to do with failed (NSTP) payments.",
    )
    app.state.settings = settings
    app.state.repo = repo
    app.state.kill_switch = kill_switch
    app.state.decision_service = DecisionService(settings, repo, kill_switch, agent or NotConfiguredAgent())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = [
            {"loc": [str(p) for p in e["loc"]], "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=400, content={"detail": "Invalid input payload", "errors": errors})

    app.include_router(retry_decision.router)
    app.include_router(admin.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app