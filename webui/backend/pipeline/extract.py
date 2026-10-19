"""Bước 1: chuỗi frame RGB -> keypoint thô (T, 28, 3).

Giống extractkpt/extractkpt200.py: tạo landmarker MỚI cho mỗi video (chế độ VIDEO
cần timestamp tăng dần), timestamp = frame_idx * 1000 / fps.
"""
import numpy as np

from .landmarks import (
    TOTAL_JOINTS,
    create_hand_landmarker,
    create_pose_landmarker,
    ensure_models,
    extract_from_frame,
    frame_timestamp_ms,
)


def iter_keypoints(frames_rgb, fps):
    """Sinh (28, 3) cho từng frame, để nơi gọi báo tiến độ giữa chừng."""
    ensure_models()
    with create_hand_landmarker() as hands, create_pose_landmarker() as pose:
        for i, frame in enumerate(frames_rgb):
            yield extract_from_frame(frame, hands, pose, frame_timestamp_ms(i, fps))


def extract_keypoints(frames_rgb, fps):
    """frames_rgb: danh sách ảnh RGB (H, W, 3) uint8 -> (T, 28, 3) float32."""
    out = list(iter_keypoints(frames_rgb, fps))
    if not out:
        return np.zeros((0, TOTAL_JOINTS, 3), dtype=np.float32)
    return np.stack(out).astype(np.float32)
