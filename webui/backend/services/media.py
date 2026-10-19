"""Đọc đầu vào (file video, chuỗi ảnh webcam) thành frame RGB và tạo ảnh xem lại.

Đọc video bằng OpenCV rồi BGR -> RGB, giống extractkpt200.py.
"""
import base64
import os
import tempfile

import cv2
import numpy as np

from ..config import DEFAULT_FPS, MAX_FRAMES, PREVIEW_QUALITY, PREVIEW_SIZE


class MediaError(ValueError):
    """Đầu vào không đọc được hoặc vượt giới hạn; thông điệp hiển thị thẳng cho người dùng."""


def read_video_file(path, max_frames=MAX_FRAMES):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise MediaError("Không mở được file video. Hãy thử file .mp4, .mov hoặc .webm khác.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if len(frames) > max_frames:
                raise MediaError(
                    f"Video dài quá {max_frames} frame (khoảng {max_frames / DEFAULT_FPS:.0f} giây). "
                    "Mỗi video chỉ nên chứa một ký hiệu, hãy cắt ngắn lại."
                )
    finally:
        cap.release()

    if not frames:
        raise MediaError("Video không có frame nào đọc được.")
    if not fps or fps <= 0 or fps > 240:
        fps = DEFAULT_FPS
    return frames, float(fps)


def read_video_bytes(data, filename="upload.mp4", max_frames=MAX_FRAMES):
    """OpenCV chỉ đọc từ đường dẫn nên ghi tạm ra đĩa rồi xóa ngay sau khi đọc."""
    suffix = os.path.splitext(filename or "")[1].lower() or ".mp4"
    fd, tmp_path = tempfile.mkstemp(prefix="vsl400_", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return read_video_file(tmp_path, max_frames)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def decode_image_frames(blobs, max_frames=MAX_FRAMES):
    """Danh sách bytes JPEG/PNG (webcam) -> danh sách frame RGB."""
    if not blobs:
        raise MediaError("Không nhận được frame nào từ webcam.")
    if len(blobs) > max_frames:
        raise MediaError(f"Quá nhiều frame ({len(blobs)} > {max_frames}).")

    frames = []
    shape = None
    for i, blob in enumerate(blobs):
        img = cv2.imdecode(np.frombuffer(blob, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise MediaError(f"Frame {i + 1} bị hỏng, không giải mã được.")
        if shape is None:
            shape = img.shape
        elif img.shape != shape:
            raise MediaError("Các frame webcam có kích thước khác nhau.")
        frames.append(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return frames


def encode_preview(frames, size=PREVIEW_SIZE, quality=PREVIEW_QUALITY):
    """Frame RGB -> danh sách JPEG base64 thu nhỏ (cạnh dài = size) để trình duyệt phát lại."""
    out = []
    params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    for frame in frames:
        h, w = frame.shape[:2]
        scale = size / max(h, w)
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        if scale < 1:
            img = cv2.resize(img, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, params)
        if ok:
            out.append(base64.b64encode(buf.tobytes()).decode("ascii"))
    return out
