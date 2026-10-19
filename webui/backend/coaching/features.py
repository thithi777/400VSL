"""Đặc trưng để so sánh người học với video mẫu, tách theo bộ phận cơ thể.

Toạ độ dùng chung với model: keypoint thô -> nội suy -> chuẩn hóa theo vai -> Kalman RTS
(smooth_sequence), rồi lấy cổ (trung điểm 2 vai) làm gốc như feeder. Chỉ dùng x, y
(z của camera đơn kém tin cậy). Đơn vị: chiều rộng vai.

4 bộ phận:
    right_shape / left_shape    hình dạng bàn tay = 10 điểm ngón tay so với cổ tay,
                                chia cho kích thước bàn tay (giữ hướng lòng bàn tay)
    right_motion / left_motion  vị trí cổ tay + khuỷu tay so với cổ
"""
from dataclasses import dataclass, field

import numpy as np

from ..pipeline.fusion import smooth_sequence

SHO_L, SHO_R, NECK = 22, 23, 24

# Mỗi tay: 0 cổ tay, rồi (gốc, đầu) của ngón cái, trỏ, giữa, áp út, út
HANDS = {
    "right": {"label": "phải", "base": 0, "elbow": 27},
    "left": {"label": "trái", "base": 11, "elbow": 26},
}
FINGERS = [
    ("ngón cái", (1, 2)),
    ("ngón trỏ", (3, 4)),
    ("ngón giữa", (5, 6)),
    ("ngón áp út", (7, 8)),
    ("ngón út", (9, 10)),
]
MIDDLE_BASE = 5          # gốc ngón giữa: đo kích thước bàn tay
DEFAULT_HAND_SIZE = 0.3  # khi không thấy tay (đơn vị vai)

PARTS = [
    {"key": "right_shape", "side": "right", "kind": "shape", "name": "Hình dạng bàn tay phải"},
    {"key": "right_motion", "side": "right", "kind": "motion", "name": "Vị trí, chuyển động tay phải"},
    {"key": "left_shape", "side": "left", "kind": "shape", "name": "Hình dạng bàn tay trái"},
    {"key": "left_motion", "side": "left", "kind": "motion", "name": "Vị trí, chuyển động tay trái"},
]
PART_KEYS = [p["key"] for p in PARTS]

# Hoán đổi trái <-> phải khi soi gương
MIRROR_INDEX = np.array(
    list(range(11, 22)) + list(range(0, 11)) + [23, 22, 24, 25, 27, 26]
)


@dataclass
class Sequence:
    xy: np.ndarray                      # (T, 28, 2) gốc tại cổ, đơn vị vai
    visible: dict                       # side -> (T,) bool, tay được MediaPipe phát hiện ở frame đó
    parts: dict = field(default_factory=dict)   # part key -> (T, P, 2)
    hand_size: dict = field(default_factory=dict)

    @property
    def length(self):
        return self.xy.shape[0]


def _hand_visible(raw, side):
    wrist = HANDS[side]["base"]
    return np.any(raw[:, wrist, :2] != 0, axis=-1)


def _build_parts(xy, visible):
    parts, sizes = {}, {}
    for side, info in HANDS.items():
        b = info["base"]
        wrist = xy[:, b]
        fingers = xy[:, b + 1:b + 11]

        span = np.linalg.norm(xy[:, b + MIDDLE_BASE] - wrist, axis=-1)
        seen = visible[side] & (span > 1e-4)
        size = float(np.median(span[seen])) if seen.any() else DEFAULT_HAND_SIZE
        size = max(size, 0.05)
        sizes[side] = size

        parts[f"{side}_shape"] = (fingers - wrist[:, None]) / size
        parts[f"{side}_motion"] = np.stack([wrist, xy[:, info["elbow"]]], axis=1)
    return parts, sizes


def prepare(raw):
    """Keypoint thô (T, 28, 3) -> Sequence."""
    raw = np.asarray(raw, dtype=np.float32)
    xy = smooth_sequence(raw)[:, :, :2].astype(np.float64)
    neck = (xy[:, SHO_L] + xy[:, SHO_R]) / 2
    xy[:, NECK] = neck  # điểm 24: mũi -> cổ, giống feeder
    xy = xy - neck[:, None]

    visible = {side: _hand_visible(raw, side) for side in HANDS}
    parts, sizes = _build_parts(xy, visible)
    return Sequence(xy=xy, visible=visible, parts=parts, hand_size=sizes)


def mirror(seq):
    """Soi gương: đổi tay trái <-> phải và lật trục x. Dùng để phát hiện người học dùng nhầm tay."""
    xy = seq.xy[:, MIRROR_INDEX].copy()
    xy[..., 0] *= -1
    visible = {"right": seq.visible["left"], "left": seq.visible["right"]}
    parts, sizes = _build_parts(xy, visible)
    return Sequence(xy=xy, visible=visible, parts=parts, hand_size=sizes)


def hand_activity(seq, side):
    """Mức độ tay được dùng trong ký hiệu, dựa trên độ cao và độ di chuyển của cổ tay.

    Trả về dict: lift (cổ tay cao nhất so với khuỷu, dương = cao hơn khuỷu),
    travel (độ lệch chuẩn vị trí cổ tay), visible (tỉ lệ frame thấy tay).
    """
    info = HANDS[side]
    wrist = seq.xy[:, info["base"]]
    elbow = seq.xy[:, info["elbow"]]
    lift = float(np.max(elbow[:, 1] - wrist[:, 1]))      # y hướng xuống
    travel = float(np.sqrt(np.sum(wrist.var(axis=0))))
    return {"lift": lift, "travel": travel, "visible": float(seq.visible[side].mean())}


def pairwise_distance(a, b):
    """a: (Ta, P, 2), b: (Tb, P, 2) -> (Ta, Tb) khoảng cách Euclid trung bình trên P điểm."""
    diff = a[:, None, :, :] - b[None, :, :, :]
    return np.sqrt(np.sum(diff ** 2, axis=-1)).mean(axis=-1)
