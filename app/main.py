"""
WealthBot API Entry Point
=========================
FastAPI application with health checks, metadata, and CORS middleware.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.db.database import DatabaseManager
from app.services.artifact_loader import ensure_artifacts
from app.services.ml_service import MLService

logger = structlog.get_logger("wealthbot.api")

# =============================================================================
# Response Models
# =============================================================================


class MLStatus(BaseModel):
    """ML subsystem readiness."""

    predictor_loaded: bool
    categorizer_loaded: bool


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    environment: str
    database: str
    ml: MLStatus


class RootResponse(BaseModel):
    """Root endpoint response schema."""

    message: str
    version: str
    docs_url: str


# =============================================================================
# Application Lifespan
# =============================================================================


_INSECURE_SECRETS = {
    "",
    "dev-secret-key-change-in-production",
    "dev-secret-key-change-in-prod",
    "your-super-secret-key-change-in-production",
    "changeme",
    "secret",
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown events.

    - Startup: Initialize database connection pool
    - Shutdown: Close database connections gracefully
    """
    _ = app

    # Security: warn if running with insecure secret key
    import logging

    configure_logging()
    logger = logging.getLogger("wealthbot.security")

    # Initialize Sentry (if enabled)
    if settings.sentry_enabled and settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                traces_sample_rate=settings.sentry_traces_sample_rate,
                environment=settings.app_env,
                release="wealthbot@0.1.0",
            )
            logger.info("Sentry initialized (env=%s)", settings.app_env)
        except Exception:
            logger.warning("Failed to initialize Sentry — continuing without error tracking.")

    if settings.secret_key in _INSECURE_SECRETS:
        if settings.app_env in ("production", "staging"):
            raise RuntimeError(
                "FATAL: SECRET_KEY is insecure. "
                "Set a strong SECRET_KEY in your environment before running in production. "
                "Generate one with: openssl rand -hex 32"
            )
        logger.warning(
            "SECRET_KEY is using an insecure default. "
            "This is acceptable for local development only. "
            "Generate a secure key with: openssl rand -hex 32"
        )

    # Startup
    db_manager = DatabaseManager()
    await db_manager.initialize()

    # Fetch ML artifacts from object storage (no-op when env vars unset)
    from pathlib import Path as _Path

    ensure_artifacts(_Path("./ml/models"))

    # Preload ML models (non-blocking — logs warning if artifacts are missing)
    ml_service = MLService()
    await ml_service.load_models()

    # Warmup inference so the first user request doesn't pay cold-start latency
    try:
        if ml_service._model_loaded:
            import numpy as _np

            await ml_service.predict_spending(
                _np.zeros(21, dtype=_np.float32), user_id="__warmup__"
            )
        if ml_service._categorizer_loaded:
            await ml_service.categorize_transaction("warmup", user_id="__warmup__")
    except Exception:
        logger.exception("ML warmup inference failed — continuing anyway")

    # Connect to Redis (if enabled)
    if settings.redis_enabled:
        from app.core.cache import redis_pool

        await redis_pool.connect()

    yield

    # Shutdown
    if settings.redis_enabled:
        from app.core.cache import redis_pool

        await redis_pool.close()
    await db_manager.close()


# =============================================================================
# FastAPI Application Instance
# =============================================================================

app = FastAPI(
    title="WealthBot API",
    description="""
    🏦 **WealthBot** - Predictive Personal Finance Application

    ## Features
    * 💰 Smart transaction categorization using DistilBERT
    * 📊 Predictive spending analysis with XGBoost
    * 🛡️ Safe-to-Spend calculations
    * 🔐 GDPR/SOC 2 compliant data handling

    ## API Modules
    * **Users** - User management and authentication
    * **Transactions** - Financial transaction tracking
    * **Predictions** - ML-powered spending insights
    """,
    version="0.1.0",
    terms_of_service="https://wealthbot.app/terms",
    contact={
        "name": "WealthBot Support",
        "url": "https://wealthbot.app/support",
        "email": "support@wealthbot.app",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://wealthbot.app/license",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# =============================================================================
# Rate Limiting
# =============================================================================

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]


async def internal_server_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return a safe 500 payload with CORS headers preserved.

    CORSMiddleware does not reliably wrap responses generated by exception
    handlers — error responses can ship without Access-Control-Allow-Origin,
    making the browser report a CORS failure and hiding the real bug. This
    handler injects CORS headers explicitly so client-side DevTools surface
    the real status code and body.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        error=str(exc),
    )
    payload: dict[str, str] = {"detail": "Internal Server Error"}
    if request_id is not None:
        payload["request_id"] = request_id

    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    if origin and origin in settings.allowed_origins_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload,
        headers=headers,
    )


app.add_exception_handler(Exception, internal_server_error_handler)


# =============================================================================
# CORS Middleware Configuration
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts_list,
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=settings.gzip_minimum_size,
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    """Attach request IDs and consistent security headers to every response."""
    request_id = str(uuid4())
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = perf_counter()
    try:
        response = await call_next(request)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - verified via handler unit test
        response = await internal_server_error_handler(request, exc)

    duration_ms = round((perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(duration_ms)
    response.headers["Strict-Transport-Security"] = (
        f"max-age={settings.hsts_max_age}; includeSubDomains"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    # Structured request log
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=duration_ms,
        request_id=request_id,
    )

    structlog.contextvars.clear_contextvars()
    return response


# =============================================================================
# API Routers
# =============================================================================

app.include_router(api_v1_router)


# =============================================================================
# Core Endpoints
# =============================================================================


@app.get(
    "/",
    response_model=RootResponse,
    tags=["Root"],
    summary="API Root",
    description="Welcome endpoint with API information.",
)
async def root() -> RootResponse:
    """Return API welcome message and documentation link."""
    return RootResponse(
        message="Welcome to WealthBot API 🏦",
        version="0.1.0",
        docs_url="/docs",
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health Check",
    description="Comprehensive health check including database connectivity.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def health_check() -> JSONResponse:
    """
    Perform comprehensive health check.

    Verifies:
    - Application is running
    - Database connectivity
    """
    db_status = "healthy"
    overall_status = "healthy"
    status_code = status.HTTP_200_OK

    try:
        db_manager = DatabaseManager()
        is_db_healthy = await db_manager.health_check()
        if not is_db_healthy:
            db_status = "unhealthy"
            overall_status = "degraded"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception:
        db_status = "unreachable"
        overall_status = "unhealthy"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    ml_service = MLService()
    response_data = HealthResponse(
        status=overall_status,
        version="0.1.0",
        environment=settings.app_env,
        database=db_status,
        ml=MLStatus(
            predictor_loaded=bool(ml_service._model_loaded),
            categorizer_loaded=bool(ml_service._categorizer_loaded),
        ),
    )

    return JSONResponse(
        content=response_data.model_dump(),
        status_code=status_code,
    )


@app.get(
    "/ready",
    tags=["Health"],
    summary="Readiness Check",
    description="Returns 503 until the DB (and Redis, if enabled) are reachable.",
)
async def readiness_check() -> JSONResponse:
    """Readiness probe: DB reachable + Redis reachable (when enabled)."""
    reasons: list[str] = []
    try:
        db_manager = DatabaseManager()
        if not await db_manager.health_check():
            reasons.append("database unreachable")
    except Exception as exc:
        reasons.append(f"database error: {exc}")

    if settings.redis_enabled:
        try:
            from app.core.cache import redis_pool

            client = redis_pool.client
            if client is None or not await client.ping():
                reasons.append("redis unreachable")
        except Exception as exc:
            reasons.append(f"redis error: {exc}")

    if reasons:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reasons": reasons},
        )
    return JSONResponse(content={"status": "ready"})


@app.get(
    "/live",
    tags=["Health"],
    summary="Liveness Check",
    description="Kubernetes-style liveness probe.",
)
async def liveness_check() -> dict[str, str]:
    """Simple liveness check for container orchestration."""
    return {"status": "alive"}
