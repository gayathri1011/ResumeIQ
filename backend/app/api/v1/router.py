from fastapi import APIRouter

from app.api.v1 import auth, bullets, health, jobs, resumes

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(auth.router)
api_v1_router.include_router(resumes.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(bullets.router)
