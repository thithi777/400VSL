"""So sánh người học với video mẫu bằng DTW theo từng bộ phận.

1. Trọng số bộ phận: tay nào trong video mẫu được nâng lên hoặc di chuyển thì quan trọng;
   tay để yên chỉ giữ trọng số nhỏ.
2. Căn chỉnh thời gian: DTW (hai đầu nới lỏng) trên chi phí tổng hợp của 4 bộ phận,
   mỗi bộ phận chia cho thang đo riêng (hiệu chuẩn từ dữ liệu) để cộng được với nhau.
3. Dọc đường căn chỉnh: sai lệch từng bộ phận, từng giai đoạn (đầu / giữa / cuối),
   từng ngón tay, hướng lệch của cổ tay, biên độ chuyển động.
4. Đổi sai lệch sang điểm 0-100 theo ngưỡng hiệu chuẩn (scripts/calibrate_coaching.py):
   `bad` = mức lệch điển hình giữa hai ký hiệu KHÁC nhau -> 0 điểm. Mức được 100 điểm:
   - model nhận đúng: `good` (phân vị 75 giữa hai người làm CÙNG ký hiệu), khoan dung với khác biệt phong cách
   - model nhận sai (`strict`): `good_strict` (trung vị), nhạy hơn để chỉ ra chỗ sai
"""
import json
from dataclasses import dataclass

import numpy as np

from ..config import CALIBRATION_JSON
from .dtw import dtw
from .features import FINGERS, HANDS, PARTS, hand_activity, mirror, pairwise_distance, prepare

PHASES = ["đầu", "giữa", "cuối"]
DTW_MARGIN = 0.15
INACTIVE_WEIGHT = 0.15

# Giá trị mặc định khi chưa chạy hiệu chuẩn (đơn vị: kích thước bàn tay / chiều rộng vai)
DEFAULT_CALIBRATION = {
    "right_shape": {"scale": 0.43, "good": 0.59, "good_strict": 0.43, "bad": 0.76},
    "right_motion": {"scale": 0.18, "good": 0.24, "good_strict": 0.18, "bad": 0.31},
    "left_shape": {"scale": 0.49, "good": 0.73, "good_strict": 0.49, "bad": 1.00},
    "left_motion": {"scale": 0.18, "good": 0.24, "good_strict": 0.18, "bad": 0.38},
}


def load_calibration(path=CALIBRATION_JSON):
    calib = {k: dict(v) for k, v in DEFAULT_CALIBRATION.items()}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, values in data.get("parts", {}).items():
            if key in calib:
                calib[key].update({k: float(values[k]) for k in ("scale", "good", "good_strict", "bad") if k in values})
    except (OSError, ValueError):
        pass
    return calib


def to_score(distance, good, bad):
    """Sai lệch -> điểm 0-100 (<= good: 100, >= bad: 0, tuyến tính ở giữa)."""
    span = max(bad - good, 1e-6)
    return np.clip((bad - np.asarray(distance, dtype=np.float64)) / span, 0.0, 1.0) * 100.0


def hand_usage(seq, side):
    """0..1: tay được dùng bao nhiêu trong ký hiệu (nâng cao hơn khuỷu hoặc di chuyển nhiều)."""
    a = hand_activity(seq, side)
    by_lift = np.clip((a["lift"] + 0.6) / 0.4, 0.0, 1.0)      # cổ tay từ -0.6 đến -0.2 vai so với khuỷu
    by_travel = np.clip((a["travel"] - 0.05) / 0.20, 0.0, 1.0)
    return float(max(by_lift, by_travel)), a


def part_weights(ref):
    usage = {side: hand_usage(ref, side) for side in HANDS}
    weights = {}
    for part in PARTS:
        u = usage[part["side"]][0]
        weights[part["key"]] = INACTIVE_WEIGHT + (1.0 - INACTIVE_WEIGHT) * u
    return weights, {side: {"usage": u, **a} for side, (u, a) in usage.items()}


def align(user, ref, weights, calib, margin=DTW_MARGIN):
    """-> path (K, 2) [chỉ số user, chỉ số mẫu], dict sai lệch từng bộ phận dọc path, chi phí tổng hợp."""
    dist = {p["key"]: pairwise_distance(user.parts[p["key"]], ref.parts[p["key"]]) for p in PARTS}
    total_w = sum(weights.values())
    cost = sum(weights[k] * dist[k] / calib[k]["scale"] for k in dist) / total_w
    path, mean_cost = dtw(cost, margin)
    errors = {k: d[path[:, 0], path[:, 1]] for k, d in dist.items()}
    return path, errors, mean_cost


@dataclass
class Comparison:
    path: np.ndarray            # (K, 2)
    phase_of_step: np.ndarray   # (K,) 0/1/2
    errors: dict                # part -> (K,) sai lệch thô
    step_scores: dict           # part -> (K,) điểm 0-100 từng bước
    part_scores: dict           # part -> điểm 0-100
    phase_scores: dict          # part -> [3 điểm]
    weights: dict               # part -> trọng số
    usage_ref: dict             # side -> mức dùng tay trong video mẫu
    usage_user: dict            # side -> mức dùng tay của người học
    visible_user: dict          # side -> tỉ lệ frame thấy tay
    finger_errors: dict         # side -> {phase: [5 sai lệch]}
    wrist_offset: dict          # side -> {phase: (dx, dy)} người học - mẫu, đơn vị vai
    amplitude_ratio: dict       # side -> biên độ người học / mẫu
    similarity: float           # điểm tổng hợp 0-100
    mirrored_better: bool       # người học dùng tay ngược với mẫu -> user đã được đổi tay khi chấm
    user: object                # Sequence (đã đổi tay nếu mirrored_better)
    ref: object                 # Sequence


def _phases(path):
    j = path[:, 1].astype(np.float64)
    lo, hi = j.min(), j.max()
    rel = (j - lo) / max(hi - lo, 1.0)
    return np.minimum((rel * 3).astype(np.int64), 2)


def compare_sequences(user_raw, ref_raw, calib=None, strict=False):
    """strict=True khi model không nhận ra ký hiệu: dùng ngưỡng 100 điểm chặt hơn để chỉ ra chỗ sai."""
    calib = calib or load_calibration()
    good_key = "good_strict" if strict else "good"
    user = prepare(user_raw)
    ref = prepare(ref_raw)

    weights, usage_ref = part_weights(ref)
    path, errors, cost = align(user, ref, weights, calib)

    # Thử soi gương: nếu khớp tốt hơn hẳn thì người học đang dùng tay ngược (ví dụ người thuận tay trái).
    # Khi đó chấm trên chuỗi đã đổi tay để nhận xét về hình dạng/chuyển động vẫn có nghĩa.
    user_mirror = mirror(user)
    path_m, errors_m, cost_mirror = align(user_mirror, ref, weights, calib)
    mirrored_better = cost_mirror < 0.7 * cost
    if mirrored_better:
        user, path, errors = user_mirror, path_m, errors_m

    phase = _phases(path)
    step_scores, part_scores, phase_scores = {}, {}, {}
    for part in PARTS:
        k, c = part["key"], calib[part["key"]]
        good, bad = c[good_key], c["bad"]
        step_scores[k] = to_score(errors[k], good, bad)
        part_scores[k] = float(to_score(errors[k].mean(), good, bad))
        phase_scores[k] = [
            float(to_score(errors[k][phase == p].mean(), good, bad)) if np.any(phase == p) else None
            for p in range(3)
        ]

    finger_errors, wrist_offset, amplitude_ratio, usage_user, visible_user = {}, {}, {}, {}, {}
    ui, rj = path[:, 0], path[:, 1]
    for side, info in HANDS.items():
        b = info["base"]
        shape_u = user.parts[f"{side}_shape"][ui]
        shape_r = ref.parts[f"{side}_shape"][rj]
        per_point = np.linalg.norm(shape_u - shape_r, axis=-1)        # (K, 10)
        finger_errors[side] = {}
        wrist_offset[side] = {}
        for p in range(3):
            mask = phase == p
            if not mask.any():
                continue
            finger_errors[side][p] = [float(per_point[mask][:, [a - 1, t - 1]].mean()) for _, (a, t) in FINGERS]
            d = user.xy[ui[mask], b] - ref.xy[rj[mask], b]
            wrist_offset[side][p] = (float(d[:, 0].mean()), float(d[:, 1].mean()))

        travel_u = np.sqrt(np.sum(user.xy[ui, b].var(axis=0)))
        travel_r = np.sqrt(np.sum(ref.xy[rj, b].var(axis=0)))
        amplitude_ratio[side] = float(travel_u / max(travel_r, 1e-3))
        usage_user[side] = hand_usage(user, side)[0]
        visible_user[side] = float(user.visible[side].mean())

    total_w = sum(weights.values())
    similarity = sum(weights[k] * part_scores[k] for k in part_scores) / total_w

    return Comparison(
        path=path,
        phase_of_step=phase,
        errors=errors,
        step_scores=step_scores,
        part_scores=part_scores,
        phase_scores=phase_scores,
        weights=weights,
        usage_ref={side: v["usage"] for side, v in usage_ref.items()},
        usage_user=usage_user,
        visible_user=visible_user,
        finger_errors=finger_errors,
        wrist_offset=wrist_offset,
        amplitude_ratio=amplitude_ratio,
        similarity=float(similarity),
        mirrored_better=bool(mirrored_better),
        user=user,
        ref=ref,
    )
