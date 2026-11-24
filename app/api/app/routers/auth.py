import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from ..db import pool
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("api.auth")


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn):
    """Создает пользователя и сразу два пустых счета: RUB и USD."""
    email = body.email.lower()
    try:
        with pool.connection() as conn:
            user = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email",
                (email, hash_password(body.password)),
            ).fetchone()
            conn.execute(
                "INSERT INTO accounts (user_id, currency) VALUES (%s, 'RUB'), (%s, 'USD')",
                (user["id"], user["id"]),
            )
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "email already registered")
    log.info("user registered", extra={"extra_fields": {"user_id": user["id"]}})
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    with pool.connection() as conn:
        user = conn.execute(
            "SELECT id, password_hash, is_system FROM users WHERE email = %s", (body.email.lower(),)
        ).fetchone()
    # одинаковый ответ для «нет такого email» и «неверный пароль» — не подсказываем, какие email есть
    if not user or user["is_system"] or not verify_password(body.password, user["password_hash"]):
        log.warning("login failed")
        raise HTTPException(401, "invalid credentials")
    return {"access_token": create_token(user["id"])}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    return user
