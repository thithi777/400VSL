"""Phân tích một đoạn ký hiệu: trích keypoint -> model -> (so với video mẫu) -> kết quả.

Chạy dạng generator để API gửi tiến độ thật về trình duyệt (NDJSON):
    {"type": "progress", "stage": "extract", "current": 12, "total": 64}
    ...
    {"type": "result", "data": {...}}
Số lượt chạy cùng lúc do hàng đợi (services/queue.py) quyết định. Mỗi lượt có MediaPipe riêng nên
chạy song song được; riêng bước model trên GPU dùng khóa để các lượt lần lượt đi qua.
"""
import threading
import time

import numpy as np

from ..coaching import PARTS, build_feedback, compare_sequences, headline, load_calibration, verdict_of
from ..coaching.compare import hand_usage
from ..coaching.feedback import lesson_score, part_name, physical_side
from ..coaching.features import prepare
from ..config import WINDOW
from ..pipeline import fuse, to_model_input
from ..pipeline.extract import iter_keypoints
from .catalog import CatalogError
from .media import encode_preview

TOP_K = 5
PROGRESS_EVERY = 4
ACTIVE_WEIGHT = 0.5


def progress(stage, current=0, total=1):
    return {"type": "progress", "stage": stage, "current": int(current), "total": int(total)}


def _ms(t0):
    return round((time.perf_counter() - t0) * 1000)


def assess_quality(raw):
    """Kiểm tra đầu vào có giống điều kiện quay dữ liệu train không."""
    T = int(raw.shape[0])
    pose = float(np.any(raw[:, 22, :2] != 0, axis=-1).mean())
    right = float(np.any(raw[:, 0, :2] != 0, axis=-1).mean())
    left = float(np.any(raw[:, 11, :2] != 0, axis=-1).mean())

    warnings = []
    if T < 20:
        warnings.append(f"Đoạn video quá ngắn ({T} frame). Một ký hiệu thường dài khoảng 2 đến 3 giây.")
    if pose < 0.7:
        warnings.append(f"Chỉ thấy vai và thân người trong {round(pose * 100)}% số frame. "
                        "Hãy lùi ra để camera thấy từ đầu tới hông.")
    if max(right, left) < 0.3:
        warnings.append("Gần như không thấy bàn tay nào. Kiểm tra ánh sáng và giữ tay trong khung hình.")
    elif T >= 10 and pose >= 0.7:
        # Cả hai tay không giơ lên và gần như không di chuyển: chỉ 0,3 % video VSL400 thật rơi vào ngưỡng này
        seq = prepare(raw)
        if max(hand_usage(seq, side)[0] for side in ("right", "left")) < 0.3:
            warnings.append("Gần như không thấy tay giơ lên hay di chuyển, kết quả dưới đây có thể không có nghĩa. "
                            "Hãy bắt đầu làm ký hiệu ngay khi đếm ngược kết thúc.")
    return {"frames": T, "pose": pose, "hands": {"right": right, "left": left}, "warnings": warnings}


class Analyzer:
    def __init__(self, recognizer, catalog):
        self.recognizer = recognizer
        self.catalog = catalog
        self.calibration = load_calibration()
        self._gpu_lock = threading.Lock()

    def top_k(self, probs, k=TOP_K):
        order = np.argsort(-probs)[:k]
        return [
            {"label": int(i) + 1, "gloss": self.catalog.gloss_of_index(int(i)), "prob": float(probs[i])}
            for i in order
        ]

    def run(self, frames, fps, target=None, preview=True):
        """preview=False: không gửi lại ảnh xem lại (webcam: trình duyệt đã có ảnh vừa ghi, đỡ ~1 MB tải về)."""
        if target is not None and target not in self.catalog.gloss:
            raise CatalogError(f"Không có bài học số {target}.")

        total = len(frames)
        timing = {}

        # 1. Keypoint
        t0 = time.perf_counter()
        yield progress("extract", 0, total)
        keypoints = []
        for i, kp in enumerate(iter_keypoints(frames, fps)):
            keypoints.append(kp)
            if (i + 1) % PROGRESS_EVERY == 0 or i + 1 == total:
                yield progress("extract", i + 1, total)
        raw = np.stack(keypoints).astype(np.float32)
        timing["extract_ms"] = _ms(t0)

        # 2. Fusion + feeder + model
        yield progress("model")
        t0 = time.perf_counter()
        model_input = to_model_input(fuse(raw, WINDOW), WINDOW)
        with self._gpu_lock:
            probs = self.recognizer.probabilities(model_input)[0]
        timing["model_ms"] = _ms(t0)

        # 3. So với video mẫu
        practice = None
        if target is not None:
            yield progress("compare")
            t0 = time.perf_counter()
            practice = self._practice(raw, probs, target)
            timing["compare_ms"] = _ms(t0)

        # 4. Ảnh xem lại
        preview_frames = []
        if preview:
            yield progress("preview")
            t0 = time.perf_counter()
            preview_frames = encode_preview(frames)
            timing["preview_ms"] = _ms(t0)

        height, width = frames[0].shape[:2]
        yield {
            "type": "result",
            "data": {
                "frames": total,
                "fps": float(fps),
                "size": [int(width), int(height)],
                "top5": self.top_k(probs),
                "quality": assess_quality(raw),
                "preview": preview_frames,
                "timing": timing,
                "practice": practice,
            },
        }

    def _practice(self, raw, probs, target):
        gloss = self.catalog.gloss[target]
        order = np.argsort(-probs)
        rank = int(np.where(order == target - 1)[0][0]) + 1
        verdict = verdict_of(rank)
        top1 = self.catalog.gloss_of_index(int(order[0]))

        # Model nhận đúng: khoan dung với khác biệt phong cách; nhận sai: chấm chặt để chỉ ra chỗ sai
        comp = compare_sequences(raw, self.catalog.reference_keypoints(target), self.calibration,
                                 strict=verdict != "pass")

        parts = []
        for part in PARTS:
            key = part["key"]
            weight = comp.weights[key]
            parts.append({
                "key": key,
                "name": part_name(comp, part),
                "side": physical_side(comp, part["side"]),
                "kind": part["kind"],
                "score": round(comp.part_scores[key]),
                "phases": [None if s is None else round(s) for s in comp.phase_scores[key]],
                "weight": round(weight, 2),
                "active": weight >= ACTIVE_WEIGHT,
            })

        return {
            "target": {"label": target, "gloss": gloss},
            "verdict": verdict,
            "rank": rank,
            "prob": float(probs[target - 1]),
            "headline": headline(verdict, gloss, rank, top1),
            "score": lesson_score(probs[target - 1], comp.similarity),
            "similarity": round(comp.similarity),
            "parts": parts,
            "feedback": build_feedback(comp, verdict),
            "mirrored": comp.mirrored_better,
        }
