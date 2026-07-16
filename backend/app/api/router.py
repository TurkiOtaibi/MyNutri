from fastapi import APIRouter

from app.api.routes import diary, foods, health, nutrition, profile

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(profile.router)
api_router.include_router(nutrition.router)
api_router.include_router(foods.router)
api_router.include_router(diary.router)
