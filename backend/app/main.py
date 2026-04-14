import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TalentBridge API",
        description="Intelligent job portal — HR & Candidate platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ---------------------------------------------------------------------------
    # Middleware
    # ---------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers — applied via a simple middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # ---------------------------------------------------------------------------
    # Routes
    # ---------------------------------------------------------------------------
    @app.get("/health", tags=["health"], include_in_schema=False)
    async def health_check() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "talentbridge-api"})

    # API v1 router will be registered here in subsequent steps
    # from app.api.v1.router import api_router
    # app.include_router(api_router, prefix="/api/v1")

    logger.info("TalentBridge API started", env=settings.APP_ENV)
    return app


app = create_app()
