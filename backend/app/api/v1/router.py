from fastapi import APIRouter

from app.api.v1.routes.applications import router as applications_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.jobs import router as jobs_router
from app.api.v1.routes.resumes import router as resumes_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(jobs_router)
api_router.include_router(applications_router)
api_router.include_router(resumes_router)

# Registered in subsequent steps:
# from app.api.v1.routes.candidates import router as candidates_router
# from app.api.v1.routes.matching import router as matching_router
# from app.api.v1.routes.analytics import router as analytics_router
