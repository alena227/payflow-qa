"""Регистрация, вход, 2FA.

Вход:
- неверный пароль или неверный код 2FA увеличивают счетчик неудачных попыток;
- после LOGIN_MAX_ATTEMPTS (5) неудач подряд вход блокируется на LOGIN_LOCK_MINUTES (5) -> 429;
- если у пользователя включена 2FA, без поля otp вход вернет 401 "otp required".

2FA (TOTP, как в Google Authenticator): сервер и приложение знают общий секрет и
из него + текущего времени считают 6-значный код, который меняется каждые 30 секунд.
"""
import logging
import os

import psycopg
import pyotp
from fastapi import APIRouter, Depends, HTTPException

from ..db import pool
from ..flags import BUGS
from ..schemas import LoginIn, OtpIn, RegisterIn, TokenOut, TotpSetupOut, UserOut
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("api.auth")

MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "5"))


def verify_otp(secret: str | None, code: str) -> bool:
    # valid_window=1: принимаем также код из соседнего 30-секундного окна (рассинхрон часов)
    return bool(secret) and pyotp.TOTP(secret).verify(code, valid_window=1)


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


def _otp_error(user: dict, otp: str | None) -> str | None:
    """None — код верный; иначе текст ошибки."""
    if BUGS:
        if otp is None:
            return "otp required"
        if otp and not verify_otp(user["totp_secret"], otp):
            return "invalid otp"
        return None
    if otp is None:
        return "otp required"
    if not verify_otp(user["totp_secret"], otp):
        return "invalid otp"
    return None


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn):
    # Ошибку запоминаем и выбрасываем ПОСЛЕ выхода из блока with:
    # иначе исключение откатит транзакцию и счетчик неудачных попыток не сохранится.
    error: tuple[int, str] | None = None
    with pool.connection() as conn:
        user = conn.execute(
            """SELECT id, password_hash, is_system, totp_secret, totp_enabled, locked_until,
                      locked_until > now() AS is_locked
               FROM users WHERE email = %s FOR UPDATE""",
            (body.email.lower(),),
        ).fetchone()

        def register_failure():
            conn.execute(
                """UPDATE users SET
                     locked_until  = CASE WHEN failed_logins + 1 >= %(max)s
                                          THEN now() + make_interval(mins => %(lock)s) ELSE locked_until END,
                     failed_logins = CASE WHEN failed_logins + 1 >= %(max)s THEN 0 ELSE failed_logins + 1 END
                   WHERE id = %(id)s""",
                {"max": MAX_ATTEMPTS, "lock": LOCK_MINUTES, "id": user["id"]},
            )

        if not user or user["is_system"]:
            # одинаковый ответ для «нет такого email» и «неверный пароль»
            error = (401, "invalid credentials")
        elif user["is_locked"]:
            error = (429, "too many failed attempts, try again later")
        elif not verify_password(body.password, user["password_hash"]):
            register_failure()
            error = (401, "invalid credentials")
        elif user["totp_enabled"]:
            otp_err = _otp_error(user, body.otp)
            if otp_err == "invalid otp":
                register_failure()
            if otp_err:
                error = (401, otp_err)

        if error is None:
            conn.execute("UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = %s", (user["id"],))

    if error:
        log.warning("login failed", extra={"extra_fields": {"reason": error[1]}})
        raise HTTPException(error[0], error[1])
    return {"access_token": create_token(user["id"])}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    return user


@router.post("/2fa/setup", response_model=TotpSetupOut, tags=["2fa"])
def totp_setup(user: dict = Depends(current_user)):
    """Шаг 1: сгенерировать секрет. Его (или otpauth_uri как QR-код) добавляют в приложение-аутентификатор."""
    if user["totp_enabled"]:
        raise HTTPException(409, "2fa already enabled")
    secret = pyotp.random_base32()
    with pool.connection() as conn:
        conn.execute("UPDATE users SET totp_secret = %s WHERE id = %s", (secret, user["id"]))
    uri = pyotp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name="PayFlow")
    return {"secret": secret, "otpauth_uri": uri}


@router.post("/2fa/enable", status_code=204, tags=["2fa"])
def totp_enable(body: OtpIn, user: dict = Depends(current_user)):
    """Шаг 2: подтвердить кодом из приложения — только после этого 2FA включается."""
    with pool.connection() as conn:
        row = conn.execute("SELECT totp_secret, totp_enabled FROM users WHERE id = %s", (user["id"],)).fetchone()
        if row["totp_enabled"]:
            raise HTTPException(409, "2fa already enabled")
        if not verify_otp(row["totp_secret"], body.code):
            raise HTTPException(400, "invalid otp")
        conn.execute("UPDATE users SET totp_enabled = TRUE WHERE id = %s", (user["id"],))


@router.post("/2fa/disable", status_code=204, tags=["2fa"])
def totp_disable(body: OtpIn, user: dict = Depends(current_user)):
    with pool.connection() as conn:
        row = conn.execute("SELECT totp_secret, totp_enabled FROM users WHERE id = %s", (user["id"],)).fetchone()
        if not row["totp_enabled"]:
            raise HTTPException(409, "2fa not enabled")
        if not verify_otp(row["totp_secret"], body.code):
            raise HTTPException(400, "invalid otp")
        conn.execute("UPDATE users SET totp_enabled = FALSE, totp_secret = NULL WHERE id = %s", (user["id"],))
