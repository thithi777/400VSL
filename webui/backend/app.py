"""Ứng dụng FastAPI: API + phục vụ giao diện tĩnh và video mẫu."""
import logging
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request

from .api import api_router
from .config import FRONTEND_DIR, QUEUE_MAX_WAITING, QUEUE_WORKERS, REFERENCE_VIDEO_DIR, SESSION_COOKIE
from .db import init_db
from .inference import SignRecognizer
from .pipeline import extract_keypoints
from .services.analyzer import Analyzer
from .services.auth import user_for_token
from .services.catalog import Catalog
from .services.queue import AnalysisQueue

log = logging.getLogger("vsl400")


class MemberFiles(StaticFiles):
    """Video mẫu có mặt người biểu diễn: chỉ phục vụ cho người đã đăng nhập."""

    async def __call__(self, scope, receive, send):
        token = Request(scope).cookies.get(SESSION_COOKIE)
        if await run_in_threadpool(user_for_token, token) is None:
            await PlainTextResponse("Bạn cần đăng nhập.", status_code=401)(scope, receive, send)
            return
        await super().__call__(scope, receive, send)


class FrontendFiles(StaticFiles):
    """Bắt trình duyệt hỏi lại server (ETag -> 304) mỗi lần, để sửa JS/CSS là thấy ngay."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(app):
    init_db()
    app.state.queue = AnalysisQueue(QUEUE_WORKERS, QUEUE_MAX_WAITING)
    app.state.catalog = Catalog()
    app.state.analyzer = None
    app.state.model_error = None
    app.state.gpu = None
    try:
        recognizer = SignRecognizer()
        recognizer.warm_up()
        extract_keypoints([np.zeros((256, 256, 3), dtype=np.uint8)], 25.0)  # nạp MediaPipe trước
        app.state.analyzer = Analyzer(recognizer, app.state.catalog)
        app.state.gpu = recognizer.gpu_name
        log.info("Model sẵn sàng trên %s", recognizer.gpu_name)
    except Exception as exc:
        app.state.model_error = str(exc)
        log.exception("Không nạp được model")
    yield


def create_app():
    app = FastAPI(
        title="VSL400 - Học ngôn ngữ ký hiệu",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.include_router(api_router, prefix="/api")
    app.mount("/media/reference", MemberFiles(directory=REFERENCE_VIDEO_DIR, check_dir=False), name="reference")
    app.mount("/", FrontendFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
