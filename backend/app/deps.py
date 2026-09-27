"""通用依赖：管理员 / 客户身份校验。"""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Admin, User
from .security import decode_token


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization.strip()


def current_admin(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Admin:
    token = _bearer(authorization)
    payload = decode_token(token) if token else None
    if not payload or payload.get("role") not in ("admin", "operator"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已失效，请重新登录")
    admin = db.get(Admin, payload.get("uid"))
    if not admin or not admin.status:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账户不存在或已停用")
    return admin


def require_super_admin(admin: Admin = Depends(current_admin)) -> Admin:
    if admin.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "该操作仅超级管理员可用")
    return admin


def current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    token = _bearer(authorization)
    payload = decode_token(token) if token else None
    if not payload or payload.get("role") != "customer":
        return None
    user = db.get(User, payload.get("uid"))
    if not user or not user.status:
        return None
    return user


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "请先登录")
    return user