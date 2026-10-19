"""Các route /api/*. Chỉ /api/status và /api/auth/* dùng được khi chưa đăng nhập."""
from fastapi import APIRouter, Depends

from . import analyze, auth, catalog, progress, system
from .auth import current_user

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router, dependencies=[Depends(current_user)])
api_router.include_router(progress.router)
api_router.include_router(analyze.router)

__all__ = ["api_router", "current_user"]
