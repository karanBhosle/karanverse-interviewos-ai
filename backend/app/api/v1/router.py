from fastapi import APIRouter

from app.api.v1 import auth, health, interviews, learning, resumes, tts, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
api_router.include_router(interviews.router)
api_router.include_router(tts.router)
api_router.include_router(learning.router)
api_router.include_router(users.router)
