from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.routes import multi_timeframe
from app.core.config import settings
from app.db.mongo import (
    close_mongodb_connection,
    connect_to_mongodb,
)

from app.routes.auth import (
    limiter,
    router as auth_router,
)

from app.routes.health import router as health_router
from app.routes.market_data import router as market_data_router
from app.routes import analysis


# =========================================================
# Application Lifespan
# =========================================================

@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongodb()

    try:
        yield
    finally:
        await close_mongodb_connection()


# =========================================================
# FastAPI Application
# =========================================================

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=(
        "/docs"
        if settings.app_env != "production"
        else None
    ),
    redoc_url=(
        "/redoc"
        if settings.app_env != "production"
        else None
    ),
    openapi_url=(
        "/openapi.json"
        if settings.app_env != "production"
        else None
    ),
    debug=False,
    lifespan=lifespan,
)


# =========================================================
# Rate Limiting
# =========================================================

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.add_middleware(SlowAPIMiddleware)


# =========================================================
# Trusted Host Protection
# =========================================================

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)


# =========================================================
# CORS Configuration
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-MT5-API-Key",
    ],
    max_age=600,
)


# =========================================================
# Security Headers
# =========================================================

@app.middleware("http")
async def add_security_headers(request, call_next):
    request_id = str(uuid4())

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers["Cache-Control"] = "no-store"

    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# =========================================================
# API Routers
# =========================================================

app.include_router(
    health_router,
    prefix=f"{settings.api_v1_prefix}/health",
)

app.include_router(multi_timeframe.router)
app.include_router(analysis.router)
app.include_router(
    auth_router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    market_data_router,
    prefix=settings.api_v1_prefix,
)




# =========================================================
# Root Endpoint
# =========================================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "application": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": (
            "/docs"
            if settings.app_env != "production"
            else None
        ),
    }