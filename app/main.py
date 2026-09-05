from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.api.recovery_cases import router as recovery_cases_router
from app.api.recovery_decisions import router as recovery_decisions_router
from app.api.recovery_actions import router as recovery_actions_router
from app.api.recovery_outcomes import router as recovery_outcomes_router
from app.api.audit_events import router as audit_events_router
from app.api.risk_assessments import router as risk_assessments_router
from app.api.recovery_orchestrator import router as recovery_orchestrator_router

app = FastAPI(
    title="RecoverAI",
    version="0.1.0",
)


class Settings(BaseSettings):
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:4174",
        "http://127.0.0.1:4175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(recovery_cases_router)
app.include_router(recovery_decisions_router)
app.include_router(recovery_actions_router)
app.include_router(recovery_outcomes_router)
app.include_router(audit_events_router)
app.include_router(risk_assessments_router)
app.include_router(recovery_orchestrator_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
