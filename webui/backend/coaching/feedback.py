"""Chuyển kết quả so sánh + dự đoán của model thành nhận xét tiếng Việt.

Quy ước hướng: video không lật gương, nên tay phải của người hiện ở nửa TRÁI ảnh.
Mọi chỉ dẫn nói theo cơ thể người học ("phía bên phải của bạn"), không theo màn hình.
"""
import numpy as np

from .compare import PHASES
from .features import FINGERS, HANDS, PARTS

GOOD_SCORE = 75     # >= : bộ phận đạt
WEAK_SCORE = 50     # <  : lỗi rõ
ACTIVE_WEIGHT = 0.5
OFFSET_THRESHOLD = 0.2   # lệch cổ tay đáng kể (đơn vị chiều rộng vai)


MODEL_WEIGHT = 0.7  # điểm bài = 70 % độ tin cậy HD-GCN + 30 % độ giống mẫu (DTW)


def verdict_of(rank):
    if rank == 1:
        return "pass"
    if rank <= 5:
        return "close"
    return "fail"


def lesson_score(prob, similarity):
    """Điểm bài 0-100. HD-GCN (đúng 97,9 % trên test) quyết định phần lớn; DTW chỉ phân biệt
    đúng/sai ở mức AUC ~0,85 và đo độ giống MỘT người mẫu, nên chỉ chiếm phần nhỏ."""
    return round(100 * (MODEL_WEIGHT * float(prob) + (1 - MODEL_WEIGHT) * float(similarity) / 100))


def headline(verdict, target_gloss, rank, top1_gloss):
    if verdict == "pass":
        return f"Đúng ký hiệu. Mô hình nhận ra “{target_gloss}”."
    if verdict == "close":
        return f"Gần đúng. “{target_gloss}” đứng thứ {rank}, mô hình đang nghiêng về “{top1_gloss}”."
    return f"Chưa đúng. Mô hình nhận thành “{top1_gloss}”."


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " và " + items[-1]


def physical_side(comp, side):
    """Tay thật của người học ứng với `side` trong phép so sánh (đã đổi tay nếu dùng ngược tay)."""
    if comp.mirrored_better:
        return "left" if side == "right" else "right"
    return side


def _hand(comp, side):
    return HANDS[physical_side(comp, side)]["label"]


def part_name(comp, part):
    """Tên bộ phận theo tay thật của người học."""
    key = f"{physical_side(comp, part['side'])}_{part['kind']}"
    return next(p["name"] for p in PARTS if p["key"] == key)


def _worst_phase(phase_scores):
    valid = [(s, p) for p, s in enumerate(phase_scores) if s is not None]
    return min(valid)[1] if valid else 1


def _shape_message(comp, side, phase):
    label = _hand(comp, side)
    errs = comp.finger_errors[side].get(phase)
    text = f"Hình dạng bàn tay {label} chưa giống mẫu ở đoạn {PHASES[phase]} động tác"
    if errs:
        order = np.argsort(errs)[::-1]
        top = [FINGERS[order[0]][0]]
        if errs[order[1]] >= 0.75 * errs[order[0]]:
            top.append(FINGERS[order[1]][0])
        text += f", lệch nhiều nhất ở {_join(top)}"
    return text + ". Xem chậm video mẫu và để ý cách co, duỗi các ngón này."


def _motion_message(comp, side, phase):
    label = _hand(comp, side)
    dx, dy = comp.wrist_offset[side].get(phase, (0.0, 0.0))
    if comp.mirrored_better:
        dx = -dx  # chuỗi so sánh đã lật trục x
    hints = []
    if dy > OFFSET_THRESHOLD:
        hints.append("đưa tay lên cao hơn")
    elif dy < -OFFSET_THRESHOLD:
        hints.append("hạ tay thấp xuống")
    # Ảnh không lật: x lớn hơn = lệch về phía bên TRÁI của người học
    if dx > OFFSET_THRESHOLD:
        hints.append("đưa tay về phía bên phải của bạn")
    elif dx < -OFFSET_THRESHOLD:
        hints.append("đưa tay về phía bên trái của bạn")

    if hints:
        return f"Vị trí tay {label} lệch ở đoạn {PHASES[phase]} động tác: {_join(hints)}."

    ratio = comp.amplitude_ratio[side]
    if ratio < 0.65:
        return f"Chuyển động tay {label} còn nhỏ so với mẫu. Hãy làm rộng và dứt khoát hơn."
    if ratio > 1.6:
        return f"Chuyển động tay {label} rộng hơn mẫu. Hãy thu gọn lại."
    return (f"Đường đi của tay {label} chưa giống mẫu ở đoạn {PHASES[phase]} động tác. "
            "Xem lại hướng di chuyển trong video mẫu.")


def build_feedback(comp, verdict=None):
    """-> danh sách {level: good|tip|warn, part, text}, sắp theo mức độ cần sửa.

    Khi mô hình đã nhận đúng (verdict 'pass'), lệch so với người mẫu chủ yếu là khác biệt phong cách:
    nhận xét về bộ phận chỉ ở mức gợi ý, không phải lỗi.
    """
    items = []
    lenient = verdict == "pass"

    # 1. Camera không thấy tay đang cần dùng
    for side in HANDS:
        if comp.usage_ref[side] >= ACTIVE_WEIGHT and comp.visible_user[side] < 0.6:
            pct = round(comp.visible_user[side] * 100)
            items.append({
                "level": "warn", "part": f"{side}_shape",
                "text": (f"Camera chỉ thấy tay {_hand(comp, side)} trong {pct}% thời gian. "
                         "Giữ tay trong khung hình, đủ sáng và đừng di chuyển quá nhanh."),
            })

    # 2. Dùng ngược tay (khớp tốt hơn hẳn khi soi gương); phần chấm bên dưới đã đổi tay
    if comp.mirrored_better:
        main = max(HANDS, key=lambda s: comp.usage_ref[s])
        other = "left" if main == "right" else "right"
        items.append({
            "level": "tip", "part": None,
            "text": (f"Bạn đang dùng tay {HANDS[other]['label']} làm tay chính, còn người mẫu dùng tay "
                     f"{HANDS[main]['label']}. Người thuận tay {HANDS[other]['label']} có thể làm như vậy; "
                     "điểm bên dưới đã đổi tay để so sánh. Lưu ý video mẫu không lật gương: "
                     "tay phải của người mẫu nằm ở bên trái màn hình."),
        })

    # 3. Từng bộ phận đang được dùng, bộ phận kém nhất trước
    active = [p for p in PARTS if comp.weights[p["key"]] >= ACTIVE_WEIGHT]
    for part in sorted(active, key=lambda p: comp.part_scores[p["key"]]):
        key = part["key"]
        score = comp.part_scores[key]
        if score >= GOOD_SCORE:
            continue
        phase = _worst_phase(comp.phase_scores[key])
        if part["kind"] == "shape":
            text = _shape_message(comp, part["side"], phase)
        else:
            text = _motion_message(comp, part["side"], phase)
        if lenient:
            items.append({"level": "tip", "part": key, "text": f"Để giống mẫu hơn: {text[0].lower()}{text[1:]}"})
        else:
            items.append({"level": "warn" if score < WEAK_SCORE else "tip", "part": key, "text": text})

    # 4. Tay không cần dùng nhưng người học lại cử động nhiều (và lệch hẳn khỏi tư thế của mẫu)
    for side in HANDS:
        other = "left" if side == "right" else "right"
        if (comp.usage_ref[side] < 0.3 and comp.usage_user[side] > 0.7
                and comp.part_scores[f"{side}_motion"] < 60):
            items.append({
                "level": "tip", "part": f"{side}_motion",
                "text": f"Ký hiệu này chỉ dùng tay {_hand(comp, other)}. Tay {_hand(comp, side)} nên để yên, buông tự nhiên.",
            })

    # 5. Ghi nhận phần làm tốt
    good = [part_name(comp, p).lower() for p in active if comp.part_scores[p["key"]] >= GOOD_SCORE]
    if lenient and not items:
        items.append({"level": "good", "part": None, "text": "Ký hiệu rõ ràng và gần giống mẫu. Giữ nhịp như vậy."})
    elif lenient:
        items.insert(0, {"level": "good", "part": None,
                         "text": "Mô hình đã nhận đúng ký hiệu. Các gợi ý dưới đây chỉ giúp động tác giống người mẫu hơn."})
    elif good and not items:
        items.append({"level": "good", "part": None, "text": "Các bộ phận chính đều gần giống mẫu. Giữ nhịp như vậy."})
    elif good:
        items.append({"level": "good", "part": None, "text": f"Làm tốt: {_join(good)}."})

    return items
