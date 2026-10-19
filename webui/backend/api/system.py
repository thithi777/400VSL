"""GET /api/status: model đã sẵn sàng chưa, thông số ghi webcam và tình trạng hàng đợi."""
from fastapi import APIRouter, Request

from ..config import CAPTURE_COUNTDOWN_S, CAPTURE_FRAMES, CAPTURE_JPEG_QUALITY, CAPTURE_MAX_SIDE, DEFAULT_FPS

router = APIRouter(tags=["system"])


@router.get("/status")
def status(request: Request):
    state = request.app.state
    catalog = state.catalog
    return {
        "ready": state.analyzer is not None,
        "error": state.model_error,
        "classes": len(catalog.gloss),
        "reference": {"signer": catalog.reference_signer, "count": len(catalog.references)},
        "capture": {
            "countdown": CAPTURE_COUNTDOWN_S,
            "frames": CAPTURE_FRAMES,
            "fps": DEFAULT_FPS,
            "max_side": CAPTURE_MAX_SIDE,
            "jpeg_quality": CAPTURE_JPEG_QUALITY,
        },
        "queue": state.queue.stats(),
    }
