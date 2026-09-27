"""密码哈希与令牌签发。仅依赖标准库 + PyJWT，避免生产环境额外依赖。"""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from .config import SECRET_KEY, TOKEN_EXPIRE_MINUTES

_ALGO = "HS256"
_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def create_token(subject: str, role: str, subject_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "uid": subject_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=_ALGO)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[_ALGO])
    except Exception:
        return None