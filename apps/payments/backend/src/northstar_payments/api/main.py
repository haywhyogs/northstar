"""Payments API (the 'teller'). Start: uvicorn northstar_payments.api.main:app"""

import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from northstar_payments.api import accounts, auth, payments
from northstar_payments.api.deps import get_session
from northstar_payments.common.config import get_settings
from northstar_payments.common.logging import configure_logging, correlation_id_var

configure_logging(get_settings().log_level)
logger = logging.getLogger("northstar_payments.api")

app = FastAPI(title="Northstar Payments API", version="0.1.0")
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(payments.router)


@app.middleware("http")
async def correlation_and_access_log(request: Request, call_next) -> Response:
    """Give every request a correlation ID (or reuse the caller's) and log one JSON line per request."""
    incoming = request.headers.get("X-Correlation-ID", "")
    correlation_id = incoming if 0 < len(incoming) <= 64 else str(uuid.uuid4())
    token = correlation_id_var.set(correlation_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "request",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
        return response
    finally:
        correlation_id_var.reset(token)


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    """Liveness: the process is running. (Kubernetes restarts the container if this fails.)"""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def ready(response: Response, session: Session = Depends(get_session)) -> dict[str, str]:
    """Readiness: can we reach the database? (Kubernetes stops sending traffic if this fails.)"""
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        logger.exception("readiness check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "database unavailable"}
