from fastapi import APIRouter

from app.api.endpoints.jackpot.jackpot import jackpot_module
from app.api.endpoints.user.user import user_module
from app.api.endpoints.user.auth import auth_module

user_router = APIRouter()
jackpot_router = APIRouter()

user_router.include_router(
    user_module,
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

user_router.include_router(
    auth_module,
    prefix="",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


jackpot_router.include_router(
    jackpot_module,
    prefix="/jackpot",
    tags=["jackpot"],
    responses={404: {"description": "Not found"}},
)
