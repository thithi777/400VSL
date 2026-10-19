"""Pipeline tiền xử lý, giống hệt lúc train (HANDOFF.md mục 3).

    extract  -> (T, 28, 3) keypoint thô từ MediaPipe Tasks
    fusion   -> interpolate_missing -> normalize_pose -> Kalman RTS -> fit_length -> (3, 64, 28)
    feeder   -> điểm 24 = cổ -> trừ cổ -> valid_crop_resize -> (1, 3, 64, 28, 1)
"""
from .extract import extract_keypoints
from .feeder import to_model_input
from .fusion import fuse, smooth_sequence

__all__ = ["extract_keypoints", "fuse", "smooth_sequence", "to_model_input"]
