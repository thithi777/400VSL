"""Tiến độ của người đang đăng nhập.

GET  /api/progress      tiến độ từng bài học (có xem video mẫu)
GET  /api/drill         tiến độ luyện tập (không xem mẫu)
POST /api/drill/reset   bỏ đánh dấu đã đạt của một nhóm ký hiệu để luyện lại từ đầu
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.records import load_drill, load_progress, reset_drill
from .auth import current_user

router = APIRouter(tags=["progress"])


class DrillReset(BaseModel):
    labels: list[int] = Field(min_length=1, max_length=400)


@router.get("/progress")
def progress(user=Depends(current_user)):
    return load_progress(user["id"])


@router.get("/drill")
def drill(user=Depends(current_user)):
    return load_drill(user["id"])


@router.post("/drill/reset")
def drill_reset(body: DrillReset, user=Depends(current_user)):
    return reset_drill(user["id"], body.labels)
