"""
WealthBot API Entry Point
=========================
FastAPI application with health checks, metadata, and CORS middleware.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.db.database import DatabaseManager
from app.services.ml_service import MLService


# =============================================================================
# Response Models
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    version: str
    environment: str
    database: str


class RootResponse(BaseModel):
    """Root endpoint response schema."""
    message: str
    version: str
    docs_url: str


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown events.
    
    - Startup: Initialize database connection pool
    - Shutdown: Close database connections gracefully
    """
    # Startup
    db_manager = DatabaseManager()
    await db_manager.initialize()

    # Preload ML model (non-blocking — logs warning if file is missing)
    ml_service = MLService()
    await ml_service.load_model()

    yield

    # Shutdown
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
    
    response_data = HealthResponse(
        status=overall_status,
        version="0.1.0",
        environment=settings.app_env,
        database=db_status,
    )
    
    return JSONResponse(
        content=response_data.model_dump(),
        status_code=status_code,
    )


@app.get(
    "/ready",
    tags=["Health"],
    summary="Readiness Check",
    description="Kubernetes-style readiness probe.",
)
async def readiness_check() -> dict[str, str]:
    """Simple readiness check for container orchestration."""
    return {"status": "ready"}


@app.get(
    "/live",
    tags=["Health"],
    summary="Liveness Check",
    description="Kubernetes-style liveness probe.",
)
async def liveness_check() -> dict[str, str]:
    """Simple liveness check for container orchestration."""
    return {"status": "alive"}


# =============================================================================
# Include API Routers (to be added as the project grows)
# =============================================================================

# from app.api.v1 import users, transactions, predictions
# app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
# app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])
