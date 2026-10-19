"""/api/auth/*: đăng ký, đăng nhập, đăng xuất, người đang đăng nhập.

current_user dùng làm dependency cho mọi API cần đăng nhập (trả 401 nếu chưa đăng nhập).
"""
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..config import SESSION_COOKIE, SESSION_DAYS
from ..services.auth import AuthError, authenticate, create_session, end_session, register, user_for_token

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


def client_ip(request):
    # uvicorn đã thay bằng IP thật từ X-Forwarded-For khi đứng sau cloudflared (proxy tin cậy 127.0.0.1)
    return request.client.host if request.client else "unknown"


def current_user(request: Request):
    user = user_for_token(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập để tiếp tục.")
    return user


def _auth_error(exc):
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    return HTTPException(status_code=exc.status, detail=str(exc), headers=headers)


def _start_session(request, response, user):
    response.set_cookie(
        SESSION_COOKIE,
        create_session(user["id"]),
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",  # trang khác không gửi được POST kèm cookie (chống CSRF)
        secure=request.url.scheme == "https",
        path="/",
    )
    return {"user": user}


@router.post("/register")
def register_account(body: Credentials, request: Request, response: Response):
    try:
        user = register(body.username, body.password, client_ip(request))
    except AuthError as exc:
        raise _auth_error(exc) from exc
    return _start_session(request, response, user)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response):
    try:
        user = authenticate(body.username, body.password, client_ip(request))
    except AuthError as exc:
        raise _auth_error(exc) from exc
    return _start_session(request, response, user)


@router.post("/logout")
def logout(request: Request, response: Response):
    end_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"user": None}


@router.get("/me")
def me(request: Request):
    """Không trả 401 để trang mở lần đầu không báo lỗi; chưa đăng nhập thì user = null."""
    return {"user": user_for_token(request.cookies.get(SESSION_COOKIE))}
