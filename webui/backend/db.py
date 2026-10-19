"""CSDL tài khoản và tiến độ học (SQLAlchemy).

Mặc định là một file SQLite trong webui/instance/. Muốn chuyển sang PostgreSQL chỉ cần đặt
VSL_DATABASE_URL (ví dụ postgresql+psycopg://user:pass@host/vsl400) và cài driver tương ứng.
Thời gian lưu dạng UTC không kèm múi giờ.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import ForeignKey, Index, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import DATABASE_URL


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)  # luôn viết thường
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_login_at: Mapped[datetime | None]


class AuthSession(Base):
    """Phiên đăng nhập. Chỉ lưu SHA-256 của token: lộ CSDL cũng không dùng được cookie."""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(index=True)


class Progress(Base):
    """Tiến độ từng bài của một người học (một dòng cho mỗi bài đã luyện)."""
    __tablename__ = "progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    label: Mapped[int] = mapped_column(primary_key=True)
    attempts: Mapped[int] = mapped_column(default=0)
    best: Mapped[int] = mapped_column(default=0)
    passed: Mapped[bool] = mapped_column(default=False)
    last_at: Mapped[datetime] = mapped_column(default=utcnow)


class DrillProgress(Base):
    """Tiến độ luyện tập không xem mẫu, tách khỏi tiến độ bài học.
    passed = đã làm đúng ít nhất một lần -> không bị bốc lại khi luyện tập (đặt lại được)."""
    __tablename__ = "drill_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    label: Mapped[int] = mapped_column(primary_key=True)
    attempts: Mapped[int] = mapped_column(default=0)
    best: Mapped[int] = mapped_column(default=0)
    passed: Mapped[bool] = mapped_column(default=False)
    last_at: Mapped[datetime] = mapped_column(default=utcnow)


class Attempt(Base):
    """Mỗi lần chấm (bài học hoặc nhận diện tự do). Không lưu video hay ảnh webcam."""
    __tablename__ = "attempts"
    __table_args__ = (Index("ix_attempts_user_time", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(8))           # practice | drill | free
    label: Mapped[int | None]                               # ký hiệu đang luyện (practice, drill)
    top1: Mapped[int]                                       # label model xếp hạng 1
    top1_prob: Mapped[float]
    verdict: Mapped[str | None] = mapped_column(String(8))  # pass | near | fail
    score: Mapped[int | None]
    similarity: Mapped[int | None]
    rank: Mapped[int | None]
    frames: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


def _make_engine(url):
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)

    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(conn, _record):
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")     # đọc không chặn ghi
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


engine = _make_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db():
    """Tạo thư mục chứa file SQLite và các bảng còn thiếu (không đụng dữ liệu cũ)."""
    if engine.url.get_backend_name() == "sqlite" and engine.url.database:
        Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """Một giao dịch: commit khi xong, rollback khi lỗi."""
    with SessionLocal() as session, session.begin():
        yield session
