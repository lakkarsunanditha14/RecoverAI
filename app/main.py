from fastapi import FastAPI

from app.api.recovery_cases import router as recovery_cases_router
from app.api.recovery_decisions import router as recovery_decisions_router
from app.api.recovery_actions import router as recovery_actions_router
from app.api.recovery_outcomes import router as recovery_outcomes_router
from app.api.audit_events import router as audit_events_router


app = FastAPI(
    title="RecoverAI",
    version="0.1.0",
)


app.include_router(recovery_cases_router)
app.include_router(recovery_decisions_router)
app.include_router(recovery_actions_router)
app.include_router(recovery_outcomes_router)
app.include_router(audit_events_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
