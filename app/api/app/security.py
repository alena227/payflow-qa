"""Пароли (bcrypt) и JWT.

JWT = три части base64 через точку: header.payload.signature.
Подпись HMAC-SHA256 с секретом сервера: если кто-то поменяет payload
(например, sub — id пользователя), подпись не сойдется и токен отклонится.
"""
import datetime as dt
import os

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import pool

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "30"))

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # некорректный хэш (например, у системного пользователя)
        return False


def create_token(user_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + dt.timedelta(minutes=JWT_TTL_MINUTES)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _unauthorized(detail: str = "not authenticated") -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """Зависимость FastAPI: достает пользователя из заголовка Authorization: Bearer <token>."""
    if creds is None:
        raise _unauthorized()
    try:
        # algorithms=[...] — принимаем ТОЛЬКО HS256 (защита от alg=none и подмены алгоритма)
        payload = jwt.decode(
            creds.credentials, JWT_SECRET, algorithms=[JWT_ALG], options={"require": ["exp", "sub"]}
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise _unauthorized("invalid token")
    with pool.connection() as conn:
        user = conn.execute(
            "SELECT id, email, is_system FROM users WHERE id = %s", (user_id,)
        ).fetchone()
    if not user or user["is_system"]:
        raise _unauthorized("invalid token")
    return user
