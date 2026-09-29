"""CivicPulse — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
import signal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

import time
from contextlib import asynccontextmanager
from starlette.responses import PlainTextResponse

from app.core.metrics import format_prometheus_metrics, record_request
from app.middleware import RequestIDMiddleware, configure_logging
from app.providers.cache import close_redis
from app.routes import complaints, health, meta, stats

# ── Structured logging ───────────────────────────────────────────────
configure_logging()
logger = logging.getLogger(__name__)

# ── Graceful shutdown state ──────────────────────────────────────────
_draining = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager replacing deprecated startup/shutdown events."""
    global _draining

    def _handle_sigterm(signum, frame):
        global _draining
        _draining = True
        logger.info("SIGTERM received — draining in-flight requests")

    try:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, _handle_sigterm, signal.SIGTERM, None)
    except (NotImplementedError, ValueError):
        signal.signal(signal.SIGTERM, _handle_sigterm)

    logger.info("CivicPulse backend started")
    yield
    logger.info("Shutting down — closing connections")
    await close_redis()
    from app.core.database import engine
    await engine.dispose()
    logger.info("Shutdown complete")


# ── App instance ─────────────────────────────────────────────────────
app = FastAPI(
    title="CivicPulse",
    description="Municipal complaint intake, triage and operations platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache", "X-Request-ID", "Retry-After"],
)

# ── Request-ID middleware ────────────────────────────────────────────
app.add_middleware(RequestIDMiddleware)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(complaints.router)
app.include_router(stats.router)
app.include_router(meta.router)


# ── Metrics endpoint (Prometheus text format §2.2) ───────────────────
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus text format metrics (§2.2)."""
    return PlainTextResponse(
        content=format_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ── Custom validation error handler ─────────────────────────────────
@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """Return field-level errors in a stable, frontend-friendly shape."""
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        errors.append({"field": field, "message": err["msg"]})
    return JSONResponse(status_code=400, content={"errors": errors})


from fastapi.exceptions import RequestValidationError  # noqa: E402


@app.exception_handler(RequestValidationError)
async def fastapi_validation_handler(
    request: Request, exc: RequestValidationError
):
    """Override FastAPI's default verbose validation error response."""
    errors = []
    for err in exc.errors():
        loc = err.get("loc", ())
        # Skip the first element if it's 'body'
        field_parts = [str(p) for p in loc if p != "body"]
        field = ".".join(field_parts) if field_parts else "unknown"
        errors.append({"field": field, "message": err["msg"]})
    return JSONResponse(status_code=400, content={"errors": errors})


@app.middleware("http")
async def request_metrics_and_drain_middleware(request: Request, call_next):
    """Record request duration metrics and return 503 while draining."""
    if _draining and request.url.path == "/ready":
        return JSONResponse(
            status_code=503,
            content={"error": "not_ready", "failed": "draining"},
        )

    start_time = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start_time
    record_request(request.method, request.url.path, response.status_code, duration)
    return response

