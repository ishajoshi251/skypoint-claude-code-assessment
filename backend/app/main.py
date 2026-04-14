import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers

logger = structlog.get_logger(__name__)
settings = get_settings()

# Rate limiter — uses Redis via REDIS_URL
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)


def create_app() -> FastAPI:
    app = FastAPI(
        title="TalentBridge API",
        description="Intelligent job portal — HR & Candidate platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Rate limiter state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Global exception handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"], include_in_schema=False)
    async def health_check():
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "ok", "service": "talentbridge-api"})

    logger.info("TalentBridge API started", env=settings.APP_ENV)
    return app


app = create_app()
