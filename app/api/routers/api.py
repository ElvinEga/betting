from fastapi import APIRouter
from app.api.routers.user import user_router, jackpot_router

router = APIRouter()

router.include_router(user_router)
router.include_router(jackpot_router)


