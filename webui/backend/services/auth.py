"""Tài khoản: đăng ký, đăng nhập, phiên đăng nhập (cookie) và chặn dò mật khẩu.

- Mật khẩu băm bằng Argon2id. Tham số theo khuyến nghị OWASP (19 MiB, 2 vòng): nhẹ RAM hơn
  mặc định 64 MiB khi nhiều người đăng nhập cùng lúc.
- Cookie chứa token ngẫu nhiên; CSDL chỉ lưu SHA-256 của token.
- Đếm lần đăng nhập sai / đăng ký theo IP và theo tên trong bộ nhớ (đủ cho một máy chủ).
"""
import hashlib
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from ..config import PASSWORD_MAX, PASSWORD_MIN, SESSION_DAYS, USERNAME_MAX, USERNAME_MIN
from ..db import AuthSession, User, session_scope, utcnow

USERNAME_RE = re.compile(rf"^[a-z0-9_.]{{{USERNAME_MIN},{USERNAME_MAX}}}$")
USERNAME_RULE = (f"Tên đăng nhập gồm {USERNAME_MIN} đến {USERNAME_MAX} ký tự: chữ không dấu, số, "
                 "dấu chấm hoặc gạch dưới.")

_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
# Sai tên đăng nhập vẫn băm một lần để thời gian trả lời giống sai mật khẩu (không lộ tên nào tồn tại)
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))


class AuthError(ValueError):
    """Thông điệp hiển thị thẳng cho người dùng; status là mã HTTP."""

    def __init__(self, message, status=400, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class Throttle:
    """Đếm sự kiện trong cửa sổ trượt theo từng khoá (IP, tên đăng nhập)."""

    def __init__(self, limit, window_s):
        self.limit = limit
        self.window_s = window_s
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def _trim(self, key, now):
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_s:
            hits.popleft()
        if not hits:
            del self._hits[key]
        return hits

    def retry_after(self, key):
        """0 nếu còn được phép, ngược lại số giây phải chờ."""
        now = time.monotonic()
        with self._lock:
            hits = self._trim(key, now)
            if len(hits) < self.limit:
                return 0
            return int(self.window_s - (now - hits[0])) + 1

    def hit(self, key):
        with self._lock:
            self._hits[key].append(time.monotonic())

    def reset(self, key):
        with self._lock:
            self._hits.pop(key, None)


# Một lớp học dùng chung một IP (NAT) nên giới hạn theo IP để rộng, theo tên thì chặt
_login_fail_by_name = Throttle(limit=10, window_s=15 * 60)
_login_fail_by_ip = Throttle(limit=100, window_s=15 * 60)
_register_by_ip = Throttle(limit=60, window_s=60 * 60)


def _check(throttle, key, message):
    wait = throttle.retry_after(key)
    if wait:
        raise AuthError(f"{message} Thử lại sau {max(1, round(wait / 60))} phút.", 429, retry_after=wait)


def normalize_username(username):
    return (username or "").strip().lower()


def public_user(user):
    return {"id": user.id, "username": user.username, "created_at": user.created_at.isoformat() + "Z"}


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register(username, password, ip):
    name = normalize_username(username)
    if not USERNAME_RE.match(name):
        raise AuthError(USERNAME_RULE)
    if not PASSWORD_MIN <= len(password or "") <= PASSWORD_MAX:
        raise AuthError(f"Mật khẩu cần từ {PASSWORD_MIN} đến {PASSWORD_MAX} ký tự.")
    _check(_register_by_ip, ip, "Có quá nhiều tài khoản được tạo từ mạng này.")

    taken = AuthError("Tên đăng nhập này đã có người dùng. Hãy chọn tên khác.", 409)
    password_hash = _hasher.hash(password)
    try:
        with session_scope() as db:
            if db.scalar(select(User.id).where(User.username == name)) is not None:
                raise taken
            user = User(username=name, password_hash=password_hash, last_login_at=utcnow())
            db.add(user)
            db.flush()
            result = public_user(user)
    except IntegrityError as exc:  # hai người đăng ký cùng tên đúng một lúc
        raise taken from exc
    _register_by_ip.hit(ip)
    return result


def authenticate(username, password, ip):
    name = normalize_username(username)
    _check(_login_fail_by_ip, ip, "Có quá nhiều lần đăng nhập sai từ mạng này.")
    _check(_login_fail_by_name, name, "Tài khoản này bị tạm khoá do nhập sai mật khẩu nhiều lần.")

    with session_scope() as db:
        user = db.scalar(select(User).where(User.username == name))
        try:
            _hasher.verify(user.password_hash if user else _DUMMY_HASH, password or "")
            ok = user is not None
        except (VerificationError, InvalidHashError):
            ok = False

        if not ok:
            _login_fail_by_ip.hit(ip)
            _login_fail_by_name.hit(name)
            raise AuthError("Sai tên đăng nhập hoặc mật khẩu.", 401)

        if _hasher.check_needs_rehash(user.password_hash):
            user.password_hash = _hasher.hash(password)
        user.last_login_at = utcnow()
        result = public_user(user)

    _login_fail_by_name.reset(name)
    return result


def create_session(user_id):
    """Tạo phiên mới, trả token để đặt vào cookie. Dọn luôn các phiên đã hết hạn."""
    token = secrets.token_urlsafe(32)
    now = utcnow()
    with session_scope() as db:
        db.execute(delete(AuthSession).where(AuthSession.expires_at < now))
        db.add(AuthSession(token_hash=_token_hash(token), user_id=user_id,
                           expires_at=now + timedelta(days=SESSION_DAYS)))
    return token


def user_for_token(token):
    """Token trong cookie -> thông tin người dùng, hoặc None nếu không có / hết hạn."""
    if not token or len(token) > 128:
        return None
    with session_scope() as db:
        user = db.scalar(
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(AuthSession.token_hash == _token_hash(token), AuthSession.expires_at > utcnow())
        )
        return public_user(user) if user else None


def end_session(token):
    if not token:
        return
    with session_scope() as db:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
