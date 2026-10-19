"""MediaPipe Tasks: Pose Landmarker FULL + Hand Landmarker, chế độ VIDEO.

Chép từ extractkpt/mp_landmarkers.py (bản dùng để trích keypoint train).
Ngưỡng, thứ tự gọi Pose -> Hand và cách gán 28 điểm phải giữ nguyên.
Khác biệt duy nhất: bytes của file .task được đọc một lần rồi giữ trong bộ nhớ.
"""
import os
import urllib.request
from functools import lru_cache

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from ..config import MP_MODEL_DIR

POSE_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
                  "pose_landmarker_full/float16/latest/pose_landmarker_full.task")
HAND_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                  "hand_landmarker/float16/latest/hand_landmarker.task")

POSE_MODEL_PATH = MP_MODEL_DIR / "pose_landmarker_full.task"
HAND_MODEL_PATH = MP_MODEL_DIR / "hand_landmarker.task"

MIN_DETECTION_CONFIDENCE = 0.5
MIN_PRESENCE_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

NUM_HAND_JOINTS = 11
TOTAL_JOINTS = 28  # 11 (R) + 11 (L) + 6 (Body)

# Cổ tay (0) + gốc và đầu của 5 ngón trong 21 điểm Hand Landmark
TARGET_HAND_INDICES = [0, 1, 4, 5, 8, 9, 12, 13, 16, 17, 20]


def ensure_models():
    """Tải file .task về mp_models/ nếu chưa có (dùng chung thư mục với code train)."""
    os.makedirs(MP_MODEL_DIR, exist_ok=True)
    for url, path in ((POSE_MODEL_URL, POSE_MODEL_PATH), (HAND_MODEL_URL, HAND_MODEL_PATH)):
        if not path.exists():
            tmp_path = str(path) + ".part"
            urllib.request.urlretrieve(url, tmp_path)
            os.replace(tmp_path, path)


@lru_cache(maxsize=2)
def _model_bytes(model_path):
    # Nạp model bằng bytes thay vì đường dẫn: tránh lỗi MediaPipe nối sai đường dẫn Windows
    with open(model_path, "rb") as f:
        return f.read()


def _base_options(model_path):
    return mp_python.BaseOptions(model_asset_buffer=_model_bytes(str(model_path)))


def create_pose_landmarker():
    options = vision.PoseLandmarkerOptions(
        base_options=_base_options(POSE_MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=MIN_DETECTION_CONFIDENCE,
        min_pose_presence_confidence=MIN_PRESENCE_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
    )
    return vision.PoseLandmarker.create_from_options(options)


def create_hand_landmarker():
    options = vision.HandLandmarkerOptions(
        base_options=_base_options(HAND_MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
        min_hand_presence_confidence=MIN_PRESENCE_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
    )
    return vision.HandLandmarker.create_from_options(options)


def frame_timestamp_ms(frame_idx, fps):
    """Timestamp (ms) tăng dần cho chế độ VIDEO. FPS lỗi thì mặc định 25."""
    if not fps or fps <= 0:
        fps = 25.0
    return int(round(frame_idx * 1000.0 / fps))


def extract_from_frame(rgb_frame, hands_landmarker, pose_landmarker, timestamp_ms):
    """Một frame RGB -> (28, 3). Điểm không phát hiện = 0."""
    keypoints = np.zeros((TOTAL_JOINTS, 3), dtype=np.float32)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb_frame))

    # 1) Pose: 6 điểm thân
    pose = pose_landmarker.detect_for_video(mp_image, timestamp_ms)
    if pose.pose_landmarks:
        lm = pose.pose_landmarks[0]
        keypoints[22] = [lm[11].x, lm[11].y, lm[11].z]   # vai trái
        keypoints[23] = [lm[12].x, lm[12].y, lm[12].z]   # vai phải
        keypoints[24] = [lm[0].x, lm[0].y, lm[0].z]      # mũi (feeder đổi thành cổ)
        lx, ly, lz = lm[23].x, lm[23].y, lm[23].z
        rx, ry, rz = lm[24].x, lm[24].y, lm[24].z
        keypoints[25] = [(lx + rx) / 2, (ly + ry) / 2, (lz + rz) / 2]  # tâm hông
        keypoints[26] = [lm[13].x, lm[13].y, lm[13].z]   # khuỷu trái
        keypoints[27] = [lm[14].x, lm[14].y, lm[14].z]   # khuỷu phải

    # 2) Hand: 2 x 11 điểm
    hands = hands_landmarker.detect_for_video(mp_image, timestamp_ms)
    for hand_landmarks, handedness in zip(hands.hand_landmarks, hands.handedness):
        base = 0 if handedness[0].category_name == "Right" else 11
        for i, idx in enumerate(TARGET_HAND_INDICES):
            if idx < len(hand_landmarks):
                lm_h = hand_landmarks[idx]
                keypoints[base + i] = [lm_h.x, lm_h.y, lm_h.z]

    return keypoints
