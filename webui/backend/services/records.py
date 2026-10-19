"""Lưu kết quả chấm của người học: lịch sử từng lần, tiến độ bài học và tiến độ luyện tập.

Máy chủ tự ghi sau khi chấm (không nhận điểm do trình duyệt gửi lên).
Bài học (xem video mẫu) và luyện tập (không xem mẫu) có tiến độ riêng.
"""
from datetime import timezone

from sqlalchemy import select, update

from ..db import Attempt, DrillProgress, Progress, session_scope, utcnow


def _progress_entry(row):
    """Cùng dạng trình duyệt đã dùng: {attempts, best, passed, last (ms epoch)}."""
    return {
        "attempts": row.attempts,
        "best": row.best,
        "passed": row.passed,
        "last": int(row.last_at.replace(tzinfo=timezone.utc).timestamp() * 1000),
    }


def _load(table, user_id):
    with session_scope() as db:
        rows = db.scalars(select(table).where(table.user_id == user_id))
        return {row.label: _progress_entry(row) for row in rows}


def load_progress(user_id):
    return _load(Progress, user_id)


def load_drill(user_id):
    return _load(DrillProgress, user_id)


def reset_drill(user_id, labels):
    """Bỏ đánh dấu đã đạt của các ký hiệu (luyện tập lại từ đầu); số lần thử và điểm cao nhất giữ nguyên."""
    with session_scope() as db:
        db.execute(update(DrillProgress)
                   .where(DrillProgress.user_id == user_id, DrillProgress.label.in_(labels))
                   .values(passed=False))
    return load_drill(user_id)


def record_result(user_id, result, drill=False):
    """Ghi một lần chấm; có ký hiệu mục tiêu thì cập nhật tiến độ (bài học, hoặc luyện tập nếu drill)
    và trả về tiến độ mới của ký hiệu đó."""
    practice = result.get("practice")
    top1 = result["top5"][0]
    now = utcnow()
    table = DrillProgress if drill else Progress
    with session_scope() as db:
        db.add(Attempt(
            user_id=user_id,
            mode=("drill" if drill else "practice") if practice else "free",
            label=practice["target"]["label"] if practice else None,
            top1=top1["label"],
            top1_prob=top1["prob"],
            verdict=practice["verdict"] if practice else None,
            score=practice["score"] if practice else None,
            similarity=practice["similarity"] if practice else None,
            rank=practice["rank"] if practice else None,
            frames=result["frames"],
            created_at=now,
        ))
        if not practice:
            return None

        label = practice["target"]["label"]
        row = db.get(table, (user_id, label), with_for_update=True)
        if row is None:
            row = table(user_id=user_id, label=label, attempts=0, best=0, passed=False)
            db.add(row)
        row.attempts += 1
        row.best = max(row.best, int(practice["score"]))
        row.passed = row.passed or practice["verdict"] == "pass"
        row.last_at = now
        return _progress_entry(row)
