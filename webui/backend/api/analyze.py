"""POST /api/analyze: nhận một đoạn ký hiệu, trả tiến độ + kết quả dạng NDJSON.

Đầu vào (multipart/form-data), chọn một trong hai:
    video   file video (tải lên)
    frames  nhiều ảnh JPEG theo thứ tự (webcam), kèm fps
Tuỳ chọn:
    target  label 1-400 của bài đang luyện -> thêm phần so sánh với video mẫu
    mode    "drill" khi luyện tập không xem mẫu (cần target) -> ghi vào tiến độ luyện tập thay cho bài học

Cần đăng nhập. Lượt được giữ chỗ trong hàng đợi TRƯỚC khi đọc dữ liệu tải lên (hàng đầy thì trả
503 ngay). Ảnh chỉ được giải mã khi tới lượt, nên mỗi người đang chờ chỉ chiếm vài MB.
Trong lúc chờ, trình duyệt nhận {"stage": "queue", "current": vị trí, "total": số người chờ, "eta": giây}.
Ảnh xem lại chỉ gửi về cho video tải lên; với webcam, trình duyệt dùng chính ảnh vừa ghi.
Kết quả được ghi vào lịch sử và tiến độ của người học.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool
from starlette.datastructures import UploadFile

from ..config import DEFAULT_FPS, MAX_FRAMES, MAX_UPLOAD_MB, UPLOAD_TIMEOUT_S
from ..services.analyzer import progress
from ..services.catalog import CatalogError
from ..services.media import MediaError, decode_image_frames, read_video_bytes
from ..services.queue import QueueRejected
from ..services.records import record_result
from .auth import current_user

router = APIRouter(tags=["analyze"])
log = logging.getLogger("vsl400.analyze")

MAX_BYTES = MAX_UPLOAD_MB * 1024 * 1024


class QueuedResponse(StreamingResponse):
    """Luôn gọi on_close khi kết thúc, kể cả khi người dùng đóng tab trước khi luồng kịp bắt đầu."""

    def __init__(self, content, on_close, **kwargs):
        super().__init__(content, **kwargs)
        self._on_close = on_close

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._on_close()


def _close_form(form):
    """Đóng file tạm của multipart. Gọi đồng bộ để vẫn chạy được khi request đã bị huỷ."""
    for _, value in form.multi_items():
        if isinstance(value, UploadFile):
            value.file.close()


async def _read_form(request):
    async def read():
        return await request.form(max_files=MAX_FRAMES + 1, max_fields=16)

    try:
        return await asyncio.wait_for(read(), UPLOAD_TIMEOUT_S)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=408, detail="Tải lên quá lâu, mạng có thể đang chậm. Hãy thử lại.") from exc


def _parse_fields(form, catalog):
    try:
        fps = float(form.get("fps") or DEFAULT_FPS)
        target = form.get("target")
        target = int(target) if target not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="fps hoặc target không hợp lệ.") from exc
    if target is not None and target not in catalog.gloss:
        raise HTTPException(status_code=404, detail=f"Không có bài học số {target}.")
    drill = form.get("mode") == "drill"
    if drill and target is None:
        raise HTTPException(status_code=400, detail="Luyện tập cần ký hiệu mục tiêu (target).")
    if not 1 <= fps <= 120:
        raise HTTPException(status_code=400, detail="fps phải trong khoảng 1 đến 120.")

    video = form.get("video")
    video = video if isinstance(video, UploadFile) else None
    frames = [f for f in form.getlist("frames") if isinstance(f, UploadFile)]
    if video is None and not frames:
        raise HTTPException(status_code=400, detail="Cần gửi file video hoặc chuỗi frame.")
    if video is not None and (video.size or 0) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File lớn hơn {MAX_UPLOAD_MB} MB.")
    return video, frames, fps, target, drill


def _save(user_id, result, drill):
    """Ghi kết quả vào CSDL; lỗi CSDL không được làm mất kết quả đã chấm."""
    try:
        entry = record_result(user_id, result, drill=drill)
        if result.get("practice") is not None:
            result["practice"]["progress"] = entry
    except Exception:
        log.exception("Không lưu được kết quả của người dùng %s", user_id)


@router.post("/analyze")
async def analyze(request: Request, user=Depends(current_user)):
    state = request.app.state
    analyzer = state.analyzer
    if analyzer is None:
        raise HTTPException(status_code=503, detail=state.model_error or "Model chưa sẵn sàng.")
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File lớn hơn {MAX_UPLOAD_MB} MB.")

    queue = state.queue
    try:
        ticket = queue.reserve(user["id"])
    except QueueRejected as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        raise HTTPException(status_code=exc.status, detail=str(exc), headers=headers) from exc

    form = None
    try:
        form = await _read_form(request)
        video, frames, fps, target, drill = _parse_fields(form, state.catalog)
        blobs = [await f.read() for f in frames] if video is None else None
    except BaseException:
        queue.release(ticket)
        if form is not None:
            _close_form(form)
        raise
    queue.enqueue(ticket)

    def work():
        """Chạy trong thread khi đã tới lượt: giải mã -> keypoint -> model -> so với mẫu -> lưu."""
        try:
            yield progress("decode")
            if video is not None:
                frames_rgb, src_fps = read_video_bytes(video.file.read(), video.filename or "upload.mp4")
            else:
                frames_rgb, src_fps = decode_image_frames(blobs), fps
            for event in analyzer.run(frames_rgb, src_fps, target, preview=video is not None):
                if event["type"] == "result":
                    _save(user["id"], event["data"], drill)
                yield event
        except (MediaError, CatalogError) as exc:
            yield {"type": "error", "message": str(exc)}
        except Exception as exc:  # lỗi không lường trước: ghi log, báo ngắn gọn cho người dùng
            log.exception("Phân tích thất bại")
            yield {"type": "error", "message": f"Lỗi khi phân tích: {exc}"}

    done = {"completed": False}

    async def events():
        async for position, eta in queue.turns(ticket):
            yield {"type": "progress", "stage": "queue", "current": position,
                   "total": queue.stats()["waiting"], "eta": eta}
        async for event in iterate_in_threadpool(work()):
            yield event
        done["completed"] = True

    async def ndjson():
        async for event in events():
            yield json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"

    def on_close():
        queue.release(ticket, completed=done["completed"])
        _close_form(form)

    return QueuedResponse(
        ndjson(),
        on_close=on_close,
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
