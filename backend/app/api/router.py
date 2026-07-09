from fastapi import APIRouter

from app.api.routes import diary, foods, health, profile, sync

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(profile.router)
api_router.include_router(foods.router)
api_router.include_router(diary.router)
api_router.include_router(sync.router)
