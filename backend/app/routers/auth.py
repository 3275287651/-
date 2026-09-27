"""认证：运营后台登录 + 客户注册登录 + 图形验证码（不依赖短信/第三方）。"""
from __future__ import annotations

import random
import string
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_admin, current_user
from ..models import Admin, User
from ..schemas import LoginIn, UserLoginIn, UserRegisterIn
from ..security import create_token, hash_password, verify_password

router = APIRouter(tags=["auth"])

# 单进程内存验证码（生产多副本部署请换成 Redis）
_CAPTCHA_STORE: dict[str, tuple[str, float]] = {}
_CAPTCHA_TTL = 300
_CAPTCHA_CHARS = "".join(c for c in string.ascii_uppercase + string.digits if c not in "OI01")


def _purge_expired() -> None:
    now = time.time()
    for k in [k for k, (_, exp) in _CAPTCHA_STORE.items() if exp < now]:
        _CAPTCHA_STORE.pop(k, None)


def _make_captcha_svg(code: str) -> str:
    w, h = 120, 40
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<rect width="100%" height="100%" fill="#F1F5F9"/>',
    ]
    for _ in range(6):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#94A3B8" '
            f'stroke-width="{random.choice([0.6, 0.9, 1.2])}" opacity="0.7"/>'
        )
    for i, ch in enumerate(code):
        x = 14 + i * 18 + random.randint(-2, 2)
        y = 28 + random.randint(-3, 3)
        rot = random.randint(-22, 22)
        parts.append(
            f'<text x="{x}" y="{y}" font-family="Georgia,serif" font-size="22" font-weight="700" '
            f'fill="#0F172A" transform="rotate({rot} {x} {y})">{ch}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


@router.get("/api/auth/captcha")
def captcha():
    _purge_expired()
    code = "".join(random.choice(_CAPTCHA_CHARS) for _ in range(4))
    key = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(20))
    _CAPTCHA_STORE[key] = (code.upper(), time.time() + _CAPTCHA_TTL)
    return Response(
        content=_make_captcha_svg(code),
        media_type="image/svg+xml",
        headers={"X-Captcha-Key": key, "Cache-Control": "no-store"},
    )


def _check_captcha(key: str | None, value: str | None) -> None:
    if not key or not value:
        raise HTTPException(400, "请填写图形验证码")
    item = _CAPTCHA_STORE.pop(key, None)
    if not item:
        raise HTTPException(400, "验证码已失效，请点击刷新")
    code, exp = item
    if exp < time.time():
        raise HTTPException(400, "验证码已过期，请点击刷新")
    if code != value.strip().upper():
        raise HTTPException(400, "验证码不正确")


# --------------------------------------------------------------------------- #
# 运营后台
# --------------------------------------------------------------------------- #
@router.post("/api/admin/auth/login")
def admin_login(payload: LoginIn, db: Session = Depends(get_db)):
    admin = db.execute(select(Admin).where(Admin.username == payload.username.strip())).scalar_one_or_none()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(401, "用户名或密码不正确")
    if not admin.status:
        raise HTTPException(403, "该账户已停用")
    admin.last_login_at = datetime.now()
    db.commit()
    return {
        "token": create_token(admin.username, admin.role, admin.id),
        "admin": {"id": admin.id, "username": admin.username, "name": admin.name, "role": admin.role},
    }


@router.get("/api/admin/auth/me")
def admin_me(admin: Admin = Depends(current_admin)):
    return {"id": admin.id, "username": admin.username, "name": admin.name, "role": admin.role}


# --------------------------------------------------------------------------- #
# 客户
# --------------------------------------------------------------------------- #
@router.post("/api/auth/register")
def user_register(payload: UserRegisterIn, db: Session = Depends(get_db)):
    _check_captcha(payload.captcha_key, payload.captcha)
    phone = payload.phone.strip()
    if not (phone.isdigit() and len(phone) == 11):
        raise HTTPException(400, "请输入 11 位手机号")
    if db.execute(select(User).where(User.phone == phone)).scalar_one_or_none():
        raise HTTPException(400, "该手机号已注册，请直接登录")
    user = User(
        phone=phone,
        email=(payload.email or "").strip() or None,
        nickname=(payload.nickname or "").strip() or f"用户{phone[-4:]}",
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    return {"token": create_token(phone, "customer", user.id),
            "user": {"id": user.id, "phone": user.phone, "nickname": user.nickname}}


@router.post("/api/auth/login")
def user_login(payload: UserLoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.phone == payload.phone.strip())).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "手机号或密码不正确")
    if not user.status:
        raise HTTPException(403, "账户已被禁用，请联系客服")
    user.last_login_at = datetime.now()
    db.commit()
    return {"token": create_token(user.phone, "customer", user.id),
            "user": {"id": user.id, "phone": user.phone, "nickname": user.nickname}}


@router.get("/api/auth/me")
def user_me(user: User = Depends(current_user)):
    return {"id": user.id, "phone": user.phone, "email": user.email,
            "nickname": user.nickname, "created_at": user.created_at.strftime("%Y-%m-%d")}